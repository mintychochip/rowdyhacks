"""RAG-powered Devpost alignment check — hybrid TF-IDF + Jina embeddings retrieval."""

import json
import re
from pathlib import Path

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.checks.interface import CheckContext, CheckResult
from app.config import settings

CHUNK_SIZE = 500
TOP_K_TFIDF = 3  # chunks per claim from TF-IDF
TOP_K_EMBED = 3  # chunks per claim from embeddings


RETRIEVAL_PROMPT = """You are a hackathon submission auditor. Verify whether a Devpost submission's claims match the actual code.

The GitHub repository URL is: {github_url}

Claims to verify:
{claims_text}

Relevant code chunks:
{chunks_text}

For EVERY claim, determine:
- VERIFIED: Found in the code — provide clickable GitHub links
- MISSING: Not found anywhere in the provided code
- UNCLEAR: May be present but evidence is inconclusive

CRITICAL: For evidence, use FULL GitHub URLs in this EXACT format:
  https://github.com/{{owner}}/{{repo}}/blob/{{branch}}/{{file_path}}#L{{start}}-L{{end}}

Example: "https://github.com/alice/study-buddy/blob/main/src/app.py#L14-L28"

Use 'main' as the default branch. Derive the owner/repo from the GitHub URL above.
If the repo URL is "https://github.com/Michaelhamaty/WakeMate", then links should start with "https://github.com/Michaelhamaty/WakeMate/blob/main/".

Return a JSON object:
{{
  "overall_assessment": "brief summary",
  "claims": [
    {{
      "claim": "the claim text",
      "verdict": "VERIFIED" | "MISSING" | "UNCLEAR",
      "evidence": ["https://github.com/owner/repo/blob/main/path/file.ext#L1-L10 — what was found"],
      "explanation": "one sentence"
    }}
  ],
  "suspicious_patterns": [],
  "alignment_score": 0-100
}}

alignment_score: 0 = all claims verified, 100 = nothing matches.
Every evidence entry MUST be a full GitHub URL. No bare file paths allowed."""


async def check_alignment_ai(context: CheckContext) -> CheckResult:
    """RAG pipeline: chunk repo -> TF-IDF retrieve -> LLM verify with citations."""
    repos = [context.repo_path] if context.repo_path else []
    if not repos:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=30,
            status="warn",
            details={"reason": "No repo available"},
        )

    if not settings.get_poolside_key():
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=0,
            status="pass",
            details={"reason": "LLM not configured"},
        )

    repo = context.repo_path
    claims = list(context.scraped.claimed_tech) if context.scraped.claimed_tech else []

    # Also extract claims from description using simple NLP
    if context.scraped.description:
        desc_claims = _extract_feature_claims(context.scraped.description)
        claims.extend(desc_claims)

    if not claims:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=0,
            status="pass",
            details={"reason": "No claims to verify"},
        )

    # Phase 1: Chunk ALL repos
    chunks = []
    for repo in repos:
        chunks.extend(_chunk_repo(repo))

    if not chunks:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=30,
            status="warn",
            details={"reason": "No source files to analyze"},
        )

    # Phase 2: Hybrid retrieval — TF-IDF (exact) + Jina embeddings (semantic)
    retrieved = await _retrieve_chunks_async(claims, chunks)

    # Phase 3: LLM verification with retrieved chunks only
    claims_text = "\n".join(f"- {c}" for c in claims)
    chunks_text = "\n\n".join(f"[{c['file']}:{c['start_line']}-{c['end_line']}]\n{c['content']}" for c in retrieved)

    prompt = RETRIEVAL_PROMPT.format(
        claims_text=claims_text,
        chunks_text=chunks_text,
        github_url=context.scraped.github_url or "https://github.com/unknown/repo",
    )

    api_url = f"{settings.poolside_api_url}/chat/completions"
    api_key = settings.get_poolside_key()
    model = settings.poolside_model

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Poolside API (OpenAI-compatible)
            resp = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 16384,
                    "messages": [
                        {"role": "system", "content": RETRIEVAL_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
    except Exception as e:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=30,
            status="warn",
            details={"reason": f"LLM API error: {e}"},
        )

    analysis = _parse_json(content)
    if analysis is None:
        return CheckResult(
            check_name="claimed-vs-actual-tech",
            check_category="devpost_alignment",
            score=50,
            status="warn",
            details={"reason": "Failed to parse LLM response", "raw": content[:500]},
        )

    # Build result
    score = analysis.get("alignment_score", 50)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    # Post-process claims: convert bare file paths to clickable GitHub URLs
    gh_url = context.scraped.github_url or ""
    if gh_url and gh_url.endswith("/"):
        gh_url = gh_url.rstrip("/")
    blob_base = f"{gh_url}/blob/main" if gh_url else ""

    def _make_links(claims_list: list) -> list:
        for c in claims_list:
            linked = []
            for e in c.get("evidence") or []:
                linked.append(_linkify_evidence(e, blob_base))
            c["evidence"] = linked
        return claims_list

    verified = _make_links([c for c in analysis.get("claims", []) if c.get("verdict") == "VERIFIED"])
    missing = _make_links([c for c in analysis.get("claims", []) if c.get("verdict") == "MISSING"])
    unclear = _make_links([c for c in analysis.get("claims", []) if c.get("verdict") == "UNCLEAR"])

    evidence = []
    for c in verified:
        for e in (c.get("evidence") or [])[:3]:
            evidence.append(e)

    return CheckResult(
        check_name="claimed-vs-actual-tech",
        check_category="devpost_alignment",
        score=score,
        status=status,
        details={
            "overall_assessment": analysis.get("overall_assessment", ""),
            "verified_count": len(verified),
            "missing_count": len(missing),
            "unclear_count": len(unclear),
            "verified": verified,
            "missing": missing,
            "unclear": unclear,
            "suspicious_patterns": analysis.get("suspicious_patterns", []),
            "chunks_retrieved": len(retrieved),
            "total_chunks": len(chunks),
        },
        evidence=evidence,
    )


_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    "models",
    "weights",
    "checkpoints",
    "data",
    "datasets",
    "__MACOSX",
    ".DS_Store",
    "egg-info",
    ".eggs",
}
_SKIP_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".mp4",
    ".mp3",
    ".wav",
    ".ogg",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".pth",
    ".pt",
    ".onnx",
    ".h5",
    ".pb",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".lock",
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".a",
}
_SOURCE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".ipynb",
    ".html",
    ".css",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".cfg",
    ".json",
    ".xml",
    ".r",
    ".R",
    ".sh",
    ".bash",
    ".ps1",
}

MAX_CHUNKS = 10000
MAX_FILE_BYTES = 100_000  # skip files larger than 100KB


def _chunk_repo(repo: Path) -> list[dict]:
    """Split source files into overlapping chunks with file:line metadata."""
    chunks = []

    for path in repo.rglob("*"):
        if not path.is_file():
            continue

        parts = path.relative_to(repo).parts

        # Skip by directory
        if any(p in _SKIP_DIRS for p in parts):
            continue

        # Skip by extension
        if path.suffix.lower() in _SKIP_EXTS:
            continue

        # Skip large files
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue

        ext = path.suffix.lower()
        if ext not in _SOURCE_EXTS and ext != "":
            continue

        try:
            content = path.read_text(errors="ignore")
        except Exception:
            continue

        if len(content.strip()) < 20:
            continue

        if len(chunks) >= MAX_CHUNKS:
            break

        rel = str(path.relative_to(repo)).replace("\\", "/")
        lines = content.split("\n")
        line_offset = 0
        while line_offset < len(lines) and len(chunks) < MAX_CHUNKS:
            chunk_lines = lines[line_offset : line_offset + 30]
            chunk_text = "\n".join(chunk_lines)
            if len(chunk_text.strip()) >= 20:
                chunks.append(
                    {
                        "file": rel,
                        "start_line": line_offset + 1,
                        "end_line": min(line_offset + 30, len(lines)),
                        "content": chunk_text,
                    }
                )
            line_offset += 15  # 50% overlap

    return chunks


_embed_model = None


def _get_embed_model():
    """Lazy-load E5-small model — 130MB, 14x faster than large models, strong retrieval."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        _embed_model = SentenceTransformer("intfloat/e5-small-v2")
    return _embed_model


def _embed_chunks_bge(chunks: list[dict]) -> np.ndarray | None:
    """Embed chunks using local E5-small model. Returns (n_chunks, dim) array or None."""
    try:
        model = _get_embed_model()
        # E5 models need "passage: " prefix for documents
        texts = [f"passage: {c['file']}\n{c['content']}" for c in chunks]
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    except Exception:
        return None


def _embed_chunks_bge_static(texts: list[str], _existing_matrix: np.ndarray | None = None) -> np.ndarray | None:
    """Embed text claims using already-loaded E5-small model."""
    try:
        model = _get_embed_model()
        # E5 models need "query: " prefix for queries
        texts = [f"query: {t}" for t in texts]
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    except Exception:
        return None


def _retrieve_chunks(claims: list[str], chunks: list[dict]) -> list[dict]:
    """Hybrid retrieval: TF-IDF (exact terms) + Jina embeddings (semantic)."""
    if not chunks:
        return []

    chunk_texts = [f"{c['file']}\n{c['content']}" for c in chunks]
    seen: set[int] = set()
    result: list[dict] = []

    # --- TF-IDF retrieval (exact term matching) ---
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
        lowercase=True,
        token_pattern=r"(?u)\b\w+\b",
    )
    tfidf_matrix = vectorizer.fit_transform(chunk_texts + claims)
    chunk_vecs = tfidf_matrix[: len(chunks)]
    claim_vecs = tfidf_matrix[len(chunks) :]
    sim = cosine_similarity(claim_vecs, chunk_vecs)
    for ci in range(len(claims)):
        top = np.argsort(sim[ci])[-TOP_K_TFIDF:][::-1]
        for idx in top:
            if idx not in seen:
                seen.add(int(idx))
                result.append(chunks[int(idx)])

    return result


async def _retrieve_chunks_async(claims: list[str], chunks: list[dict]) -> list[dict]:
    """Async wrapper that adds BGE-M3 embedding retrieval on top of TF-IDF."""
    import asyncio

    tfidf_results = _retrieve_chunks(claims, chunks)
    tfidf_indices = {chunks.index(c) for c in tfidf_results if c in chunks}

    # Run embedding in thread pool (sentence-transformers is sync)
    loop = asyncio.get_running_loop()
    embed_matrix = await loop.run_in_executor(None, _embed_chunks_bge, chunks)
    if embed_matrix is None:
        return tfidf_results  # model failed to load, TF-IDF only

    # Embed claims
    claim_embeddings = await loop.run_in_executor(None, _embed_chunks_bge_static, claims, embed_matrix)
    if claim_embeddings is None:
        return tfidf_results

    # Cosine similarity for embeddings
    # Normalize
    embed_norm = embed_matrix / (np.linalg.norm(embed_matrix, axis=1, keepdims=True) + 1e-10)
    claim_norm = claim_embeddings / (np.linalg.norm(claim_embeddings, axis=1, keepdims=True) + 1e-10)
    emb_sim = claim_norm @ embed_norm.T

    for ci in range(len(claims)):
        top = np.argsort(emb_sim[ci])[-TOP_K_EMBED:][::-1]
        for idx in top:
            if int(idx) not in tfidf_indices:
                tfidf_indices.add(int(idx))
                result = tfidf_results + [chunks[int(idx)]]
                tfidf_results = result

    return tfidf_results


def _extract_feature_claims(description: str) -> list[str]:
    """Extract feature-like claims from a project description using simple heuristics."""
    claims = []
    # Split on common separators
    sentences = re.split(r"[.;•\n]", description)
    for s in sentences:
        s = s.strip()
        # Look for sentences describing features (action verbs, tech mentions)
        if any(
            kw in s.lower()
            for kw in [
                "using",
                "powered by",
                "built with",
                "implemented",
                "features",
                "detects",
                "tracks",
                "uses",
                "enables",
                "real-time",
                "ai ",
                "ml ",
                "machine learning",
            ]
        ):
            if len(s) > 15 and len(s) < 200:
                claims.append(s)
    return claims[:5]  # cap to avoid noise


def _linkify_evidence(text: str, blob_base: str) -> str:
    """Convert bare file paths with line numbers to full GitHub URLs."""
    import re

    # If already a full URL, return as-is
    if text.startswith("https://github.com/"):
        return text
    if not blob_base:
        return text

    # Match patterns like "app/app.py:1-30" or "README.md:16-45"
    m = re.match(r"([\w./-]+\.[\w]+):(\d+)(?:-(\d+))?", text.strip())
    if m:
        path = m.group(1)
        start = m.group(2)
        end = m.group(3)
        line_ref = f"#L{start}" if not end else f"#L{start}-L{end}"
        suffix = text[text.index(m.group(0)) + len(m.group(0)) :] if m.group(0) in text else ""
        return f"{blob_base}/{path}{line_ref} —{suffix}"
    # Match patterns with file path and context like "app/app.py:1-30 — description"
    m = re.match(r"([\w./-]+\.[\w]+):(\d+)(?:-(\d+))?\s*[—–-]\s*(.+)", text.strip())
    if m:
        path = m.group(1)
        start = m.group(2)
        end = m.group(3)
        desc = m.group(4)
        line_ref = f"#L{start}" if not end else f"#L{start}-L{end}"
        return f"{blob_base}/{path}{line_ref} — {desc}"
    return text


def _parse_json(content: str) -> dict | None:
    """Extract and parse JSON from LLM response, repairing truncation."""
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Repair truncated JSON
    repaired = content.strip().rstrip(",\n\r\t ")
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    # Count unclosed strings (odd number of quotes on the last line)
    in_string = False
    clean = []
    for ch in repaired:
        if ch == '"' and (not clean or clean[-1] != "\\"):
            in_string = not in_string
        clean.append(ch)
    # If we're inside a string, close it
    if in_string:
        repaired += '"'
    # Close unterminated objects/arrays
    repaired += "}" * open_braces + "]" * open_brackets
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        # Last resort: strip the last incomplete line and try again
        lines = repaired.split("\n")
        for trim in range(1, min(5, len(lines))):
            try:
                truncated = "\n".join(lines[:-trim])
                ob = truncated.count("{") - truncated.count("}")
                obr = truncated.count("[") - truncated.count("]")
                return json.loads(truncated + "}" * ob + "]" * obr)
            except json.JSONDecodeError:
                continue
        return None

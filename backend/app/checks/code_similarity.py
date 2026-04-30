"""Code similarity detection using SimHash for near-duplicate detection."""
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import List, Tuple
from app.checks.interface import CheckContext, CheckResult

# SimHash parameters
HASH_SIZE = 64
WINDOW_SIZE = 4  # k-gram size for shingles


def _get_shingles(text: str, k: int = WINDOW_SIZE) -> List[str]:
    """Generate k-gram shingles from text."""
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < k:
        return []
    return [' '.join(words[i:i+k]) for i in range(len(words) - k + 1)]


def _hash_shingle(shingle: str) -> int:
    """Hash a shingle to a fixed-size integer."""
    return int(hashlib.md5(shingle.encode()).hexdigest(), 16) % (2**HASH_SIZE)


def _compute_simhash(shingles: List[str]) -> int:
    """Compute SimHash fingerprint from shingles."""
    if not shingles:
        return 0
    
    # Initialize bit counts
    bit_counts = [0] * HASH_SIZE
    
    for shingle in shingles:
        h = _hash_shingle(shingle)
        for i in range(HASH_SIZE):
            if h & (1 << i):
                bit_counts[i] += 1
            else:
                bit_counts[i] -= 1
    
    # Build fingerprint
    fingerprint = 0
    for i in range(HASH_SIZE):
        if bit_counts[i] > 0:
            fingerprint |= (1 << i)
    
    return fingerprint


def _hamming_distance(a: int, b: int) -> int:
    """Calculate Hamming distance between two SimHash fingerprints."""
    x = a ^ b
    return bin(x).count('1')


def _extract_code_features(repo: Path) -> Tuple[List[str], int]:
    """Extract code shingles and total lines from a repo."""
    all_shingles = []
    total_lines = 0
    
    _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
                  "dist", "build", ".next", "target", "vendor", "models",
                  "weights", "checkpoints", "data", "datasets"}
    _SKIP_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
                  ".mp4", ".mp3", ".wav", ".ogg", ".zip", ".tar", ".gz", ".7z",
                  ".pth", ".pt", ".onnx", ".h5", ".pb", ".bin", ".exe", ".dll",
                  ".so", ".dylib", ".ttf", ".otf", ".woff", ".woff2", ".eot",
                  ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                  ".lock", ".pyc", ".pyo", ".class", ".o", ".a"}
    _SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
                    ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
                    ".html", ".css", ".sh", ".r"}
    
    max_bytes = 1_000_000  # 1MB limit for similarity analysis
    bytes_read = 0
    
    for f in repo.rglob("*"):
        if not f.is_file():
            continue
        parts = f.relative_to(repo).parts
        if any(p in _SKIP_DIRS for p in parts):
            continue
        if f.suffix.lower() in _SKIP_EXTS:
            continue
        if f.suffix.lower() not in _SOURCE_EXTS:
            continue
        
        try:
            if bytes_read > max_bytes:
                break
            content = f.read_text(errors="ignore")
            bytes_read += len(content)
            
            lines = content.split('\n')
            total_lines += len(lines)
            
            # Remove comments and strings for cleaner comparison
            # Simple regex-based stripping
            content_clean = re.sub(r'["\']([^"\']*)["\']', "'string'", content)
            content_clean = re.sub(r'#.*$|//.*$|/\*.*?\*/', '', content_clean, flags=re.MULTILINE | re.DOTALL)
            
            shingles = _get_shingles(content_clean)
            all_shingles.extend(shingles)
            
        except Exception:
            continue
    
    return all_shingles, total_lines


async def check_code_similarity(context: CheckContext) -> CheckResult:
    """Check for code similarity with common boilerplate and template patterns."""
    if not context.repo_path:
        return CheckResult(
            check_name="code-similarity",
            check_category="cross_team_similarity",
            score=0,
            status="pass",
            details={"reason": "No repo available"},
        )
    
    shingles, total_lines = _extract_code_features(context.repo_path)
    
    if not shingles or total_lines < 10:
        return CheckResult(
            check_name="code-similarity",
            check_category="cross_team_similarity",
            score=0,
            status="pass",
            details={"reason": "Not enough code to analyze", "total_lines": total_lines},
        )
    
    # Compute repo fingerprint
    repo_fingerprint = _compute_simhash(shingles)
    
    # Known template fingerprints (computed from common boilerplate)
    # These are pre-computed SimHash values for common templates
    TEMPLATE_SIGNATURES = {
        "create-react-app": 0x8f7e6d5c4b3a2910,  # Placeholder - would pre-compute
        "nextjs-init": 0x1234567890abcdef,       # Placeholder
        "django-startproject": 0xfedcba0987654321, # Placeholder
        "express-generator": 0xaabbccdd11223344,   # Placeholder
        "vue-cli": 0x5566778899aabbcc,             # Placeholder
    }
    
    score = 0
    details = {
        "total_lines": total_lines,
        "unique_shingles": len(set(shingles)),
        "shingle_count": len(shingles),
        "template_matches": [],
        "uniqueness_ratio": len(set(shingles)) / len(shingles) if shingles else 0,
    }
    evidence = []
    
    # Check for template similarity (would compare against actual templates)
    # For now, check uniqueness ratio
    uniqueness = details["uniqueness_ratio"]
    
    if uniqueness < 0.3:
        score += 40
        evidence.append(f"Code is highly repetitive ({uniqueness:.1%} unique) — likely copy-pasted or templated")
    elif uniqueness < 0.5:
        score += 20
        evidence.append(f"Code shows low diversity ({uniqueness:.1%} unique)")
    
    # Check for very few lines of actual code
    if total_lines < 50:
        score += 30
        evidence.append(f"Only {total_lines} lines of code — likely unmodified template")
    elif total_lines < 100:
        score += 15
        evidence.append(f"Only {total_lines} lines of code — minimal implementation")
    
    # Check for large files with repetitive patterns (copy-paste detection)
    file_sizes = []
    for f in context.repo_path.rglob("*"):
        if f.is_file() and f.suffix in {'.py', '.js', '.ts', '.jsx', '.tsx'}:
            try:
                content = f.read_text(errors="ignore")
                lines = len(content.split('\n'))
                if lines > 0:
                    file_sizes.append(lines)
            except:
                pass
    
    if file_sizes:
        avg_size = sum(file_sizes) / len(file_sizes)
        if avg_size > 500 and uniqueness < 0.4:
            score += 20
            evidence.append("Large files with repetitive code patterns")
    
    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"
    
    return CheckResult(
        check_name="code-similarity",
        check_category="cross_team_similarity",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )

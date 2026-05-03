"""Detect AI-generated code using perplexity and entropy analysis."""

import math
import re
from collections import Counter
from pathlib import Path

from app.checks.interface import CheckContext, CheckResult


def _calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of text (higher = more random/predictable)."""
    if not text:
        return 0

    # Remove whitespace for cleaner analysis
    text = text.replace(" ", "").replace("\n", "").replace("\t", "")
    if not text:
        return 0

    # Count character frequencies
    char_counts = Counter(text)
    total_chars = len(text)

    # Calculate entropy
    entropy = 0
    for count in char_counts.values():
        probability = count / total_chars
        if probability > 0:
            entropy -= probability * math.log2(probability)

    return entropy


def _calculate_perplexity(text: str) -> float:
    """Calculate a simplified perplexity metric."""
    # Perplexity is related to how "surprised" a model would be
    # Lower perplexity = more predictable = more likely AI-generated

    if not text:
        return 0

    # Tokenize (simple word-based)
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < 3:
        return 0

    # Calculate n-gram probabilities
    bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
    bigram_counts = Counter(bigrams)

    # Calculate probability distribution
    total_bigrams = len(bigrams)
    if total_bigrams == 0:
        return 0

    # Calculate cross-entropy (simplified)
    cross_entropy = 0
    for bigram, count in bigram_counts.items():
        probability = count / total_bigrams
        cross_entropy -= probability * math.log2(probability)

    # Perplexity = 2^cross_entropy
    perplexity = math.pow(2, cross_entropy)

    return perplexity


def _analyze_code_patterns(code: str) -> dict:
    """Analyze code for AI-specific patterns."""
    patterns = {
        "uniform_naming": False,
        "excessive_comments": False,
        "perfect_indentation": False,
        "repetitive_structure": False,
        "docstring_pattern": False,
    }

    lines = code.split("\n")
    if not lines:
        return patterns

    # Check for excessive comments (AI often over-comments)
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    comment_lines = [l for l in lines if l.strip().startswith("#")]

    if code_lines and len(comment_lines) / len(code_lines) > 0.4:
        patterns["excessive_comments"] = True

    # Check for perfect indentation consistency (AI is very consistent)
    indentations = []
    for line in lines:
        if line.strip():
            leading = len(line) - len(line.lstrip())
            if leading > 0:
                indentations.append(leading)

    if indentations:
        # Check if all indentations are perfect multiples
        common_indent = Counter(indentations).most_common(1)[0][0]
        perfect_ratio = sum(1 for i in indentations if i % common_indent == 0) / len(indentations)
        if perfect_ratio > 0.98:
            patterns["perfect_indentation"] = True

    # Check for repetitive docstring patterns (AI often uses same format)
    docstring_count = len(re.findall(r'["\']{3}.*?["\']{3}', code, re.DOTALL))
    if docstring_count > 3:
        # Check if docstrings have similar structure
        docstrings = re.findall(r'["\']{3}(.*?)["\']{3}', code, re.DOTALL)
        if docstrings:
            # Calculate similarity between docstrings
            avg_length = sum(len(d) for d in docstrings) / len(docstrings)
            length_variance = sum((len(d) - avg_length) ** 2 for d in docstrings) / len(docstrings)
            if length_variance < 100:  # Very similar lengths
                patterns["docstring_pattern"] = True

    # Check for uniform naming conventions (AI is very consistent)
    # Look for snake_case vs camelCase consistency
    snake_case = len(re.findall(r"\b[a-z]+_[a-z_]+\b", code))
    camel_case = len(re.findall(r"\b[a-z]+[A-Z][a-zA-Z]*\b", code))

    if snake_case > 0 and camel_case > 0:
        ratio = max(snake_case, camel_case) / (snake_case + camel_case)
        if ratio > 0.95:  # Almost perfect consistency
            patterns["uniform_naming"] = True

    # Check for repetitive structure (AI often follows same patterns)
    function_patterns = re.findall(r"def\s+(\w+)\s*\([^)]*\):", code)
    if len(function_patterns) > 3:
        # Check for similar function structures
        similar_count = 0
        for i in range(len(function_patterns)):
            for j in range(i + 1, len(function_patterns)):
                # Simple similarity: same length or similar naming
                if abs(len(function_patterns[i]) - len(function_patterns[j])) <= 2:
                    similar_count += 1
        if similar_count > len(function_patterns):
            patterns["repetitive_structure"] = True

    return patterns


def _analyze_file_entropy(repo: Path) -> dict:
    """Analyze entropy across all code files."""
    entropies = []
    perplexities = []
    total_chars = 0

    _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    _CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb", ".java", ".c", ".cpp"}

    max_bytes = 500_000
    bytes_read = 0

    for f in repo.rglob("*"):
        if not f.is_file():
            continue
        if any(p in _SKIP_DIRS for p in f.relative_to(repo).parts):
            continue
        if f.suffix not in _CODE_EXTS:
            continue

        try:
            if bytes_read > max_bytes:
                break
            content = f.read_text(errors="ignore")
            bytes_read += len(content)

            # Calculate entropy for this file
            ent = _calculate_entropy(content)
            perp = _calculate_perplexity(content)

            entropies.append((f.name, ent))
            perplexities.append((f.name, perp))
            total_chars += len(content)

        except:
            pass

    if not entropies:
        return {"avg_entropy": 0, "avg_perplexity": 0, "files_analyzed": 0}

    avg_entropy = sum(e for _, e in entropies) / len(entropies)
    avg_perplexity = sum(p for _, p in perplexities) / len(perplexities)

    return {
        "avg_entropy": avg_entropy,
        "avg_perplexity": avg_perplexity,
        "files_analyzed": len(entropies),
        "entropy_variance": max(e for _, e in entropies) - min(e for _, e in entropies),
        "low_entropy_files": sum(1 for _, e in entropies if e < 4.0),  # Low entropy = more predictable
    }


async def check_ai_perplexity(context: CheckContext) -> CheckResult:
    """Detect AI-generated code using perplexity and entropy analysis."""
    if not context.repo_path:
        return CheckResult(
            check_name="ai-perplexity",
            check_category="ai_detection",
            score=20,
            status="pass",
            details={"reason": "No repo available"},
        )

    # Analyze all code files
    analysis = _analyze_file_entropy(context.repo_path)

    if analysis["files_analyzed"] == 0:
        return CheckResult(
            check_name="ai-perplexity",
            check_category="ai_detection",
            score=0,
            status="pass",
            details={"reason": "No code files found"},
        )

    # Analyze patterns in specific files
    patterns_found = {
        "uniform_naming": 0,
        "excessive_comments": 0,
        "perfect_indentation": 0,
        "repetitive_structure": 0,
        "docstring_pattern": 0,
    }

    _CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs"}

    for f in context.repo_path.rglob("*"):
        if not f.is_file() or f.suffix not in _CODE_EXTS:
            continue
        try:
            content = f.read_text(errors="ignore")
            patterns = _analyze_code_patterns(content)
            for key, value in patterns.items():
                if value:
                    patterns_found[key] += 1
        except:
            pass

    score = 0
    details = {
        "avg_entropy": round(analysis["avg_entropy"], 2),
        "avg_perplexity": round(analysis["avg_perplexity"], 2),
        "files_analyzed": analysis["files_analyzed"],
        "low_entropy_files": analysis["low_entropy_files"],
        "patterns_found": patterns_found,
    }
    evidence = []

    # Low entropy = high predictability = likely AI
    if analysis["avg_entropy"] < 4.5:
        score += 25
        evidence.append(f"Low entropy ({analysis['avg_entropy']:.2f}) — code is highly predictable")
    elif analysis["avg_entropy"] < 5.0:
        score += 15
        evidence.append(f"Below-average entropy ({analysis['avg_entropy']:.2f})")

    # Low perplexity = low surprise = likely AI
    if analysis["avg_perplexity"] < 50:
        score += 25
        evidence.append(f"Low perplexity ({analysis['avg_perplexity']:.0f}) — very predictable patterns")
    elif analysis["avg_perplexity"] < 100:
        score += 15
        evidence.append(f"Below-average perplexity ({analysis['avg_perplexity']:.0f})")

    # Many files with low entropy
    if analysis["low_entropy_files"] > analysis["files_analyzed"] * 0.5:
        score += 20
        evidence.append(
            f"{analysis['low_entropy_files']}/{analysis['files_analyzed']} files have unusually low entropy"
        )

    # AI-specific patterns
    if patterns_found["uniform_naming"] > 2:
        score += 15
        evidence.append("Extremely consistent naming conventions across files")

    if patterns_found["excessive_comments"] > 2:
        score += 15
        evidence.append("Excessive commenting pattern detected")

    if patterns_found["perfect_indentation"] > 3:
        score += 10
        evidence.append("Perfectly consistent indentation (human code varies more)")

    if patterns_found["docstring_pattern"] > 2:
        score += 10
        evidence.append("Repetitive docstring format across files")

    if patterns_found["repetitive_structure"] > 2:
        score += 15
        evidence.append("Repetitive function/class structures")

    # Check for AI-specific code smells
    ai_smells = 0
    for f in context.repo_path.rglob("*.py"):
        try:
            content = f.read_text(errors="ignore")
            # AI often generates these patterns
            if "# This function" in content or "# This method" in content:
                ai_smells += 1
            if re.search(r"#\s*\w+\s+\w+\s+function", content):
                ai_smells += 1
        except:
            pass

    if ai_smells > 3:
        score += 20
        evidence.append(f"{ai_smells} AI-style comment patterns found")

    score = min(100, score)
    status = "pass" if score <= 30 else "warn" if score <= 60 else "fail"

    return CheckResult(
        check_name="ai-perplexity",
        check_category="ai_detection",
        score=score,
        status=status,
        details=details,
        evidence=evidence,
    )

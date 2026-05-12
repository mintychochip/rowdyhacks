import re
import sys
from pathlib import Path

def post_process(content: str) -> str:
    """Replace Clerk auth patterns with self-hosted auth patterns."""
    # Import fixes
    content = content.replace('from app.clerk_auth import ', 'from app.auth import ')

    # Parameter / signature fixes
    content = content.replace('user_payload: dict = Depends(require_clerk_user)', 'current_user: User = Depends(get_current_user)')
    content = content.replace('auth: dict = Depends(require_organizer)', 'current_user: User = Depends(require_organizer)')
    content = content.replace('_user = Depends(require_organizer)', 'current_user: User = Depends(require_organizer)')

    # Variable usage fixes
    content = content.replace('user_payload["sub"]', 'current_user.id')
    content = content.replace('auth["user"]', 'current_user')
    content = content.replace('user = user_payload', 'user = current_user')

    # Depends fixes
    content = content.replace('Depends(require_clerk_user)', 'Depends(get_current_user)')

    # Docstring / comment references
    content = content.replace('app.clerk_auth.require_clerk_user', 'app.auth.get_current_user')
    content = content.replace('app.clerk_auth.require_organizer', 'app.auth.require_organizer')
    content = content.replace('Validates Clerk JWT', 'Validates JWT token')

    return content


def resolve_import_block(head: str, theirs: str) -> str:
    """Keep theirs, add any non-clerk imports from head that are missing."""
    head_lines = [l for l in head.splitlines() if l.strip() and 'clerk_auth' not in l]
    theirs_lines = [l for l in theirs.splitlines() if l.strip()]
    combined = theirs_lines[:]
    for line in head_lines:
        if line not in combined:
            combined.append(line)
    return '\n'.join(combined) + '\n'


def resolve_block(head: str, theirs: str, filepath: str, line_no: int) -> str:
    """Resolve a single conflict block."""
    head_stripped = head.strip()
    theirs_stripped = theirs.strip()

    # Empty sides
    if not head_stripped:
        return theirs
    if not theirs_stripped:
        return post_process(head)

    # Import block heuristic
    head_lines = [l for l in head.splitlines() if l.strip()]
    theirs_lines = [l for l in theirs.splitlines() if l.strip()]
    if head_lines and theirs_lines:
        if all(l.startswith(('from ', 'import ')) for l in head_lines + theirs_lines):
            return resolve_import_block(head, theirs)

    # Docstring-only block (both start and end with triple quotes)
    if (head_stripped.startswith('"""') and head_stripped.endswith('"""') and
            theirs_stripped.startswith('"""') and theirs_stripped.endswith('"""')):
        # Keep the longer docstring (usually head)
        doc = head if len(head) >= len(theirs) else theirs
        doc = post_process(doc)
        return doc

    # If theirs looks like a short auth-only replacement and head has the full logic,
    # prefer head but post-process auth references.
    # Heuristic: if theirs is significantly shorter, it's likely just an auth refactor.
    if len(head_stripped) > len(theirs_stripped) * 1.2:
        return post_process(head)

    # Default: prefer head (master logic) with auth rewrites, but if theirs is longer
    # and contains new feature strings we know about, prefer theirs.
    # Known feature additions we want to keep from self-hosted-auth:
    feature_markers = [
        "invite_only",
        "invite_code",
        "HackathonInvite",
        "review_notes_count",
        "average_rating",
        "RegistrationNoteService",
    ]
    if any(m in theirs_stripped for m in feature_markers) and not any(m in head_stripped for m in feature_markers):
        # theirs contains a feature addition; merge carefully by taking theirs
        # but if head had a long docstring, keep it.
        if head_stripped.startswith('"""') and len(head_stripped) > 100:
            # Extract head docstring
            doc_end = head.find('"""', 3)
            if doc_end != -1:
                docstring = head[:doc_end+3]
                return post_process(docstring) + '\n' + theirs
        return post_process(theirs)

    return post_process(head)


def resolve_file(filepath: str):
    path = Path(filepath)
    content = path.read_text(encoding='utf-8')

    if '<<<<<<< HEAD' not in content:
        # No conflict markers, but still fix lingering clerk references
        fixed = post_process(content)
        if fixed != content:
            path.write_text(fixed, encoding='utf-8')
            print(f"  Post-processed (no conflicts): {filepath}")
        return

    lines = content.splitlines(keepends=True)
    resolved_parts = []
    i = 0
    line_no = 1
    while i < len(lines):
        if lines[i].startswith('<<<<<<< HEAD'):
            start = i
            sep = None
            end = None
            for j in range(i + 1, len(lines)):
                if lines[j].startswith('======='):
                    sep = j
                elif lines[j].startswith('>>>>>>> feature/self-hosted-auth'):
                    end = j
                    break
            if sep is None or end is None:
                raise ValueError(f"Malformed conflict in {filepath} around line {line_no}")

            head_block = ''.join(lines[start + 1:sep])
            theirs_block = ''.join(lines[sep + 1:end])
            resolved = resolve_block(head_block, theirs_block, filepath, line_no)
            resolved_parts.append(resolved)
            i = end + 1
            line_no = end + 1
        else:
            resolved_parts.append(lines[i])
            i += 1
            line_no += 1

    resolved_content = ''.join(resolved_parts)
    resolved_content = post_process(resolved_content)

    # Ensure no conflict markers remain
    if '<<<<<<< HEAD' in resolved_content:
        print(f"  WARNING: remaining conflicts in {filepath}")
    else:
        path.write_text(resolved_content, encoding='utf-8')
        print(f"  Resolved: {filepath}")


files = [
    "backend/app/routes/assistant.py",
    "backend/app/routes/checks.py",
    "backend/app/routes/content.py",
    "backend/app/routes/crawler.py",
    "backend/app/routes/hackathons.py",
    "backend/app/routes/judging.py",
    "backend/app/routes/registrations.py",
    "backend/app/routes/registrations_organizer.py",
    "backend/app/routes/tracks.py",
    "backend/app/routes/webhooks.py",
    "backend/app/routes/dashboard.py",
    "backend/app/routes/hacker_dashboard.py",
    "backend/app/assistant/context_builder.py",
    "backend/app/assistant/indexer.py",
    "backend/app/assistant/tools/__init__.py",
    "backend/app/assistant/permissions.py",
    "backend/app/assistant/embedder.py",
    "backend/app/assistant/llm.py",
    "backend/app/assistant/vector_store.py",
]

for f in files:
    resolve_file(f)

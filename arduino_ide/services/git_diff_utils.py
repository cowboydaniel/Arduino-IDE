"""Utilities for computing git diff markers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

try:
    from git import Repo, GitCommandError
    from git.exc import InvalidGitRepositoryError, NoSuchPathError
except ImportError:  # pragma: no cover - GitPython is required for full functionality
    Repo = None  # type: ignore
    GitCommandError = InvalidGitRepositoryError = NoSuchPathError = None  # type: ignore


def _line_count_from_text(document_text: str) -> int:
    """Return the number of lines represented by the given document text."""
    if not document_text:
        return 0

    newline_count = document_text.count("\n")
    if document_text.endswith("\n"):
        return newline_count
    return newline_count + 1


def calculate_git_changes(file_path: Path | str, document_text: str) -> Dict[int, str]:
    """Return a mapping of line numbers to git change types.

    Args:
        file_path: Absolute or relative path to the file being edited.
        document_text: Current contents of the editor for line counting.

    Returns:
        Dictionary mapping 1-indexed line numbers to "added", "modified", or "deleted".
    """
    if not Repo or not file_path:
        return {}

    try:
        resolved_path = Path(file_path).resolve()
    except Exception:
        return {}

    try:
        repo = Repo(resolved_path.parent, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError, GitCommandError, ValueError, TypeError):
        return {}

    if repo.bare or not repo.working_tree_dir:
        return {}

    working_tree = Path(repo.working_tree_dir).resolve()
    try:
        relative_path = resolved_path.relative_to(working_tree)
    except ValueError:
        return {}

    line_count = _line_count_from_text(document_text)

    def clamp_line(number: int) -> int:
        if line_count <= 0:
            return 1
        return max(1, min(number, line_count))

    tracked = False
    try:
        tracked = bool(repo.git.ls_files(str(relative_path)).strip())
    except GitCommandError:
        tracked = False

    has_head = True
    try:
        _ = repo.head.commit
    except (ValueError, GitCommandError, TypeError):
        has_head = False

    if (not tracked) or (not has_head):
        if line_count > 0:
            return {line_number: "added" for line_number in range(1, line_count + 1)}
        return {}

    try:
        diff_text = repo.git.diff("HEAD", "--", str(relative_path))
    except GitCommandError:
        diff_text = ""

    if not diff_text.strip():
        return {}

    changes: Dict[int, str] = {}
    pending_deletions: list[int] = []
    current_new = 0

    for line in diff_text.splitlines():
        if line.startswith("@@"):
            pending_deletions.clear()
            header_parts = re.findall(r"-([0-9]+)(?:,([0-9]+))? \+([0-9]+)(?:,([0-9]+))?", line)
            if not header_parts:
                current_new = 0
                continue
            _, _, new_start, _ = header_parts[0]
            current_new = int(new_start)
            continue

        if line.startswith("diff --") or line.startswith("index") or line.startswith("---") or line.startswith("+++"):
            continue

        if line.startswith(" "):
            pending_deletions.clear()
            current_new += 1
            continue

        if line.startswith("-"):
            line_to_mark = clamp_line(current_new + len(pending_deletions))
            pending_deletions.append(line_to_mark)
            if line_to_mark >= 1:
                changes.setdefault(line_to_mark, "deleted")
            continue

        if line.startswith("+"):
            if pending_deletions:
                line_to_mark = pending_deletions.pop(0)
                changes[line_to_mark] = "modified"
            else:
                line_to_mark = clamp_line(current_new)
                changes[line_to_mark] = "added"
            current_new += 1
            continue

        if line.startswith("\\"):
            # "\ No newline at end of file"
            continue

    return changes


__all__ = ["calculate_git_changes"]

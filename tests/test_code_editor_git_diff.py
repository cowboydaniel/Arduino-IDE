from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from git import Repo

from arduino_ide.services.git_diff_utils import calculate_git_changes


@pytest.fixture
def git_repo(tmp_path):
    repo = Repo.init(tmp_path)
    repo.git.config("user.name", "Test User")
    repo.git.config("user.email", "test@example.com")
    return repo


def test_calculate_git_changes_marks_added_modified_deleted(git_repo, tmp_path):
    repo = git_repo
    file_path = Path(tmp_path) / "sketch.ino"
    file_path.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")
    repo.index.add([str(file_path.relative_to(repo.working_tree_dir))])
    repo.index.commit("Initial content")

    file_path.write_text("line1\nline2 modified\nline4\nline5 added\n", encoding="utf-8")

    changes = calculate_git_changes(file_path, file_path.read_text(encoding="utf-8"))

    assert changes == {2: "modified", 3: "deleted", 4: "added"}



def test_calculate_git_changes_handles_untracked_file(git_repo, tmp_path):
    file_path = Path(tmp_path) / "new_file.ino"
    file_path.write_text("alpha\nbeta\n", encoding="utf-8")

    changes = calculate_git_changes(file_path, file_path.read_text(encoding="utf-8"))

    assert changes == {1: "added", 2: "added"}

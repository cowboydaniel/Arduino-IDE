"""
Git Integration Service
Provides version control functionality using Git
"""

import subprocess
import logging
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """Represents a Git commit"""
    hash: str
    author: str
    email: str
    date: datetime
    message: str
    short_hash: str = ""

    def __post_init__(self):
        self.short_hash = self.hash[:7] if self.hash else ""


@dataclass
class GitFileStatus:
    """Status of a file in Git"""
    path: str
    status: str  # 'M' (modified), 'A' (added), 'D' (deleted), '?' (untracked), etc.
    staged: bool = False


@dataclass
class GitBranch:
    """Represents a Git branch"""
    name: str
    is_current: bool
    is_remote: bool = False
    tracking_branch: Optional[str] = None


@dataclass
class GitRemote:
    """Represents a Git remote"""
    name: str
    url: str
    fetch_url: str = ""
    push_url: str = ""


class GitService(QObject):
    """
    Service for Git version control operations
    Wraps Git CLI commands with Qt signals
    """

    # Signals
    repository_changed = Signal()
    commit_created = Signal(str)  # commit hash
    branch_changed = Signal(str)  # branch name
    remote_operation_completed = Signal(str)  # operation name
    error_occurred = Signal(str)  # error message

    def __init__(self, repo_path: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.repo_path = repo_path
        self._git_available = self._check_git_available()

        logger.info(f"Git service initialized (Git available: {self._git_available})")


    def _check_git_available(self) -> bool:
        """Check if Git is available in the system"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Git not available: {e}")
            return False


    def is_git_available(self) -> bool:
        """Check if Git is available"""
        return self._git_available


    def set_repository_path(self, path: str):
        """Set the repository path"""
        self.repo_path = path
        self.repository_changed.emit()


    def _run_git_command(self, args: List[str], cwd: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Run a Git command
        Returns (success, stdout, stderr)
        """
        if not self._git_available:
            return False, "", "Git is not available"

        if not cwd:
            cwd = self.repo_path

        if not cwd:
            return False, "", "No repository path set"

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Git command timed out"
        except Exception as e:
            return False, "", str(e)


    # ===== Repository Operations =====

    def init_repository(self, path: str) -> bool:
        """Initialize a new Git repository"""
        success, stdout, stderr = self._run_git_command(["init"], cwd=path)

        if success:
            self.repo_path = path
            self.repository_changed.emit()
            logger.info(f"Initialized Git repository at {path}")
        else:
            logger.error(f"Failed to init repository: {stderr}")
            self.error_occurred.emit(f"Init failed: {stderr}")

        return success


    def is_repository(self, path: Optional[str] = None) -> bool:
        """Check if path is a Git repository"""
        if not path:
            path = self.repo_path

        if not path:
            return False

        success, _, _ = self._run_git_command(["rev-parse", "--git-dir"], cwd=path)
        return success


    def get_repository_root(self) -> Optional[str]:
        """Get the root directory of the repository"""
        success, stdout, _ = self._run_git_command(["rev-parse", "--show-toplevel"])

        if success:
            return stdout.strip()

        return None


    # ===== Status and File Operations =====

    def get_status(self) -> List[GitFileStatus]:
        """Get status of files in repository"""
        success, stdout, stderr = self._run_git_command(["status", "--porcelain=v1"])

        if not success:
            logger.error(f"Failed to get status: {stderr}")
            return []

        file_statuses = []

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            # Parse porcelain format: "XY path"
            status_code = line[:2]
            file_path = line[3:]

            # Determine if staged
            staged = status_code[0] != ' ' and status_code[0] != '?'
            status_char = status_code[0] if staged else status_code[1]

            file_statuses.append(GitFileStatus(
                path=file_path,
                status=status_char,
                staged=staged
            ))

        return file_statuses


    def add_files(self, file_paths: List[str]) -> bool:
        """Stage files for commit"""
        if not file_paths:
            return False

        success, stdout, stderr = self._run_git_command(["add"] + file_paths)

        if success:
            self.repository_changed.emit()
            logger.info(f"Staged {len(file_paths)} file(s)")
        else:
            logger.error(f"Failed to stage files: {stderr}")
            self.error_occurred.emit(f"Add failed: {stderr}")

        return success


    def add_all(self) -> bool:
        """Stage all changes"""
        success, stdout, stderr = self._run_git_command(["add", "-A"])

        if success:
            self.repository_changed.emit()
            logger.info("Staged all changes")
        else:
            logger.error(f"Failed to stage all: {stderr}")
            self.error_occurred.emit(f"Add all failed: {stderr}")

        return success


    def reset_file(self, file_path: str) -> bool:
        """Unstage a file"""
        success, stdout, stderr = self._run_git_command(["reset", "HEAD", file_path])

        if success:
            self.repository_changed.emit()
            logger.info(f"Unstaged {file_path}")
        else:
            logger.error(f"Failed to unstage: {stderr}")
            self.error_occurred.emit(f"Reset failed: {stderr}")

        return success


    def discard_changes(self, file_path: str) -> bool:
        """Discard changes to a file"""
        success, stdout, stderr = self._run_git_command(["checkout", "--", file_path])

        if success:
            self.repository_changed.emit()
            logger.info(f"Discarded changes to {file_path}")
        else:
            logger.error(f"Failed to discard changes: {stderr}")
            self.error_occurred.emit(f"Checkout failed: {stderr}")

        return success


    # ===== Commit Operations =====

    def commit(self, message: str, author: Optional[str] = None, email: Optional[str] = None) -> Optional[str]:
        """Create a commit"""
        if not message:
            self.error_occurred.emit("Commit message cannot be empty")
            return None

        args = ["commit", "-m", message]

        if author and email:
            args.extend(["--author", f"{author} <{email}>"])

        success, stdout, stderr = self._run_git_command(args)

        if success:
            # Extract commit hash
            commit_hash = self._get_last_commit_hash()
            if commit_hash:
                self.commit_created.emit(commit_hash)
                self.repository_changed.emit()
                logger.info(f"Created commit: {commit_hash}")
                return commit_hash
        else:
            logger.error(f"Failed to commit: {stderr}")
            self.error_occurred.emit(f"Commit failed: {stderr}")

        return None


    def _get_last_commit_hash(self) -> Optional[str]:
        """Get hash of the last commit"""
        success, stdout, _ = self._run_git_command(["rev-parse", "HEAD"])

        if success:
            return stdout.strip()

        return None


    def get_commit_history(self, max_count: int = 100) -> List[GitCommit]:
        """Get commit history"""
        args = [
            "log",
            f"--max-count={max_count}",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso"
        ]

        success, stdout, stderr = self._run_git_command(args)

        if not success:
            logger.error(f"Failed to get history: {stderr}")
            return []

        commits = []

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|', 4)
            if len(parts) != 5:
                continue

            commit_hash, author, email, date_str, message = parts

            try:
                date = datetime.fromisoformat(date_str.replace(' ', 'T'))
            except:
                date = datetime.now()

            commits.append(GitCommit(
                hash=commit_hash,
                author=author,
                email=email,
                date=date,
                message=message
            ))

        return commits


    def get_commit_diff(self, commit_hash: str) -> str:
        """Get diff for a commit"""
        success, stdout, stderr = self._run_git_command(["show", commit_hash])

        if success:
            return stdout

        logger.error(f"Failed to get diff: {stderr}")
        return ""


    # ===== Branch Operations =====

    def get_current_branch(self) -> Optional[str]:
        """Get name of current branch"""
        success, stdout, _ = self._run_git_command(["branch", "--show-current"])

        if success:
            return stdout.strip()

        return None


    def get_branches(self, include_remote: bool = False) -> List[GitBranch]:
        """Get list of branches"""
        args = ["branch", "-vv"]
        if include_remote:
            args.append("-a")

        success, stdout, stderr = self._run_git_command(args)

        if not success:
            logger.error(f"Failed to get branches: {stderr}")
            return []

        branches = []
        current_branch = None

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            is_current = line.startswith('*')
            line = line[2:].strip()  # Remove "* " or "  "

            parts = line.split()
            if not parts:
                continue

            branch_name = parts[0]
            is_remote = branch_name.startswith('remotes/')

            # Extract tracking info if available
            tracking_branch = None
            if '[' in line and ']' in line:
                tracking_info = line[line.index('[') + 1:line.index(']')]
                if ':' in tracking_info:
                    tracking_branch = tracking_info.split(':')[0]

            branch = GitBranch(
                name=branch_name,
                is_current=is_current,
                is_remote=is_remote,
                tracking_branch=tracking_branch
            )

            branches.append(branch)

            if is_current:
                current_branch = branch_name

        return branches


    def create_branch(self, branch_name: str, checkout: bool = True) -> bool:
        """Create a new branch"""
        args = ["branch", branch_name]

        success, stdout, stderr = self._run_git_command(args)

        if success:
            logger.info(f"Created branch: {branch_name}")

            if checkout:
                return self.checkout_branch(branch_name)

            return True
        else:
            logger.error(f"Failed to create branch: {stderr}")
            self.error_occurred.emit(f"Create branch failed: {stderr}")

        return False


    def checkout_branch(self, branch_name: str) -> bool:
        """Switch to a branch"""
        success, stdout, stderr = self._run_git_command(["checkout", branch_name])

        if success:
            self.branch_changed.emit(branch_name)
            self.repository_changed.emit()
            logger.info(f"Checked out branch: {branch_name}")
        else:
            logger.error(f"Failed to checkout branch: {stderr}")
            self.error_occurred.emit(f"Checkout failed: {stderr}")

        return success


    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete a branch"""
        flag = "-D" if force else "-d"
        success, stdout, stderr = self._run_git_command(["branch", flag, branch_name])

        if success:
            self.repository_changed.emit()
            logger.info(f"Deleted branch: {branch_name}")
        else:
            logger.error(f"Failed to delete branch: {stderr}")
            self.error_occurred.emit(f"Delete branch failed: {stderr}")

        return success


    def merge_branch(self, branch_name: str) -> bool:
        """Merge a branch into current branch"""
        success, stdout, stderr = self._run_git_command(["merge", branch_name])

        if success:
            self.repository_changed.emit()
            logger.info(f"Merged branch: {branch_name}")
        else:
            logger.error(f"Failed to merge branch: {stderr}")
            self.error_occurred.emit(f"Merge failed: {stderr}")

        return success


    # ===== Remote Operations =====

    def get_remotes(self) -> List[GitRemote]:
        """Get list of remotes"""
        success, stdout, stderr = self._run_git_command(["remote", "-v"])

        if not success:
            logger.error(f"Failed to get remotes: {stderr}")
            return []

        remotes_dict = {}

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            name, url, direction = parts[0], parts[1], parts[2].strip('()')

            if name not in remotes_dict:
                remotes_dict[name] = GitRemote(name=name, url=url)

            if direction == "fetch":
                remotes_dict[name].fetch_url = url
            elif direction == "push":
                remotes_dict[name].push_url = url

        return list(remotes_dict.values())


    def add_remote(self, name: str, url: str) -> bool:
        """Add a remote"""
        success, stdout, stderr = self._run_git_command(["remote", "add", name, url])

        if success:
            self.repository_changed.emit()
            logger.info(f"Added remote: {name} ({url})")
        else:
            logger.error(f"Failed to add remote: {stderr}")
            self.error_occurred.emit(f"Add remote failed: {stderr}")

        return success


    def remove_remote(self, name: str) -> bool:
        """Remove a remote"""
        success, stdout, stderr = self._run_git_command(["remote", "remove", name])

        if success:
            self.repository_changed.emit()
            logger.info(f"Removed remote: {name}")
        else:
            logger.error(f"Failed to remove remote: {stderr}")
            self.error_occurred.emit(f"Remove remote failed: {stderr}")

        return success


    def fetch(self, remote: str = "origin") -> bool:
        """Fetch from remote"""
        success, stdout, stderr = self._run_git_command(["fetch", remote])

        if success:
            self.remote_operation_completed.emit("fetch")
            logger.info(f"Fetched from {remote}")
        else:
            logger.error(f"Failed to fetch: {stderr}")
            self.error_occurred.emit(f"Fetch failed: {stderr}")

        return success


    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """Pull from remote"""
        args = ["pull", remote]
        if branch:
            args.append(branch)

        success, stdout, stderr = self._run_git_command(args)

        if success:
            self.remote_operation_completed.emit("pull")
            self.repository_changed.emit()
            logger.info(f"Pulled from {remote}")
        else:
            logger.error(f"Failed to pull: {stderr}")
            self.error_occurred.emit(f"Pull failed: {stderr}")

        return success


    def push(self, remote: str = "origin", branch: Optional[str] = None, set_upstream: bool = False) -> bool:
        """Push to remote"""
        args = ["push"]

        if set_upstream:
            args.append("-u")

        args.append(remote)

        if branch:
            args.append(branch)

        success, stdout, stderr = self._run_git_command(args)

        if success:
            self.remote_operation_completed.emit("push")
            logger.info(f"Pushed to {remote}")
        else:
            logger.error(f"Failed to push: {stderr}")
            self.error_occurred.emit(f"Push failed: {stderr}")

        return success


    def clone(self, url: str, destination: str) -> bool:
        """Clone a repository"""
        success, stdout, stderr = self._run_git_command(["clone", url, destination], cwd=os.path.dirname(destination))

        if success:
            self.repo_path = destination
            self.repository_changed.emit()
            logger.info(f"Cloned repository from {url}")
        else:
            logger.error(f"Failed to clone: {stderr}")
            self.error_occurred.emit(f"Clone failed: {stderr}")

        return success


    # ===== Configuration =====

    def get_config(self, key: str) -> Optional[str]:
        """Get a config value"""
        success, stdout, _ = self._run_git_command(["config", "--get", key])

        if success:
            return stdout.strip()

        return None


    def set_config(self, key: str, value: str, global_config: bool = False) -> bool:
        """Set a config value"""
        args = ["config"]

        if global_config:
            args.append("--global")

        args.extend([key, value])

        success, stdout, stderr = self._run_git_command(args)

        if success:
            logger.info(f"Set config: {key} = {value}")
        else:
            logger.error(f"Failed to set config: {stderr}")

        return success


    def get_user_name(self) -> Optional[str]:
        """Get configured user name"""
        return self.get_config("user.name")


    def get_user_email(self) -> Optional[str]:
        """Get configured user email"""
        return self.get_config("user.email")


    def set_user_info(self, name: str, email: str, global_config: bool = True) -> bool:
        """Set user name and email"""
        name_success = self.set_config("user.name", name, global_config)
        email_success = self.set_config("user.email", email, global_config)

        return name_success and email_success

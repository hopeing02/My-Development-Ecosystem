from __future__ import annotations

import subprocess
from dataclasses import dataclass


class GitError(RuntimeError):
    """Raised when a git command fails."""


@dataclass(frozen=True)
class GitState:
    local_head: str
    remote_head: str


def run_git(*args: str) -> str:
    """
    Run a git command.

    Example:
        run_git("status")
        run_git("pull")
        run_git("rev-parse", "HEAD")
    """

    completed = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise GitError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"git {' '.join(args)} failed."
        )

    return completed.stdout.strip()


def get_local_head() -> str:
    """
    Return the current local commit hash.
    """

    return run_git(
        "rev-parse",
        "HEAD",
    )


def get_remote_head(
    branch: str = "main",
) -> str:
    """
    Return the latest commit hash on origin/<branch>.
    """

    output = run_git(
        "ls-remote",
        "origin",
        branch,
    )

    if not output:
        raise GitError(f"Remote branch not found: {branch}")

    return output.split()[0]


def get_git_state(
    branch: str = "main",
) -> GitState:
    """
    Return both local and remote commit hashes.
    """

    return GitState(
        local_head=get_local_head(),
        remote_head=get_remote_head(branch),
    )


def has_remote_changes(
    branch: str = "main",
) -> bool:
    """
    Return True when origin has new commits.
    """

    state = get_git_state(branch)

    return state.local_head != state.remote_head


def pull() -> None:
    """
    Execute git pull.
    """

    run_git("pull")


def current_branch() -> str:
    """
    Return current git branch.
    """

    return run_git(
        "branch",
        "--show-current",
    )

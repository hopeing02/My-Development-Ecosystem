from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str = ""


class SaveError(RuntimeError):
    pass


def run_command(command: list[str]) -> CommandResult:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
    )


def run_required(command: list[str]) -> CommandResult:
    result = run_command(command)

    if result.returncode != 0:
        raise SaveError(f"Command failed: {' '.join(command)}")

    return result


def get_current_branch() -> str:
    result = run_required(["git", "branch", "--show-current"])

    if not result.stdout:
        raise SaveError("Current Git branch could not be detected.")

    return result.stdout


def get_changed_files() -> list[str]:
    result = run_required(["git", "status", "--short"])

    if not result.stdout:
        return []

    return result.stdout.splitlines()


def ensure_has_changes() -> list[str]:
    changed_files = get_changed_files()

    if not changed_files:
        raise SaveError("No changes to save.")

    return changed_files


def save(commit_message: str, push: bool) -> None:
    branch = get_current_branch()
    changed_files = ensure_has_changes()

    print(f"Current branch: {branch}")
    print(f"Changed files: {len(changed_files)}")

    run_required(["uv", "run", "black", "."])
    run_required(["uv", "run", "ruff", "check", "."])
    run_required(["uv", "run", "pytest"])

    run_required(["git", "add", "."])
    run_required(["git", "commit", "-m", commit_message])

    if push:
        print("Push: enabled")
        run_required(["git", "push"])
    else:
        print("Push: disabled")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MDE save workflow.")
    parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Git commit message.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Create commit without pushing to GitHub.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        save(commit_message=args.message, push=not args.no_push)
    except SaveError as error:
        print(error)
        return 1

    print("MDE save completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

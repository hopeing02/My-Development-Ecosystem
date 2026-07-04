from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int


class SaveError(RuntimeError):
    pass


def run_command(command: list[str]) -> CommandResult:
    completed = subprocess.run(command, check=False)
    return CommandResult(command=command, returncode=completed.returncode)


def run_required(command: list[str]) -> None:
    result = run_command(command)

    if result.returncode != 0:
        raise SaveError(f"Command failed: {' '.join(command)}")


def save(commit_message: str, push: bool) -> None:
    run_required(["uv", "run", "black", "."])
    run_required(["uv", "run", "ruff", "check", "."])
    run_required(["uv", "run", "pytest"])

    run_required(["git", "add", "."])
    run_required(["git", "commit", "-m", commit_message])

    if push:
        run_required(["git", "push"])


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

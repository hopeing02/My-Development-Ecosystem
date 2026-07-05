from __future__ import annotations

import argparse
import sys

from tools.mde_save import save


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mde",
        description="My Development Ecosystem command line interface.",
    )

    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser(
        "save",
        help="Format, test, commit, and optionally push changes.",
    )
    save_parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Git commit message.",
    )
    save_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Commit locally without pushing to GitHub.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "save":
        save(commit_message=args.message, push=not args.no_push)
        print("MDE save completed.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

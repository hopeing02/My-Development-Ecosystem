from __future__ import annotations

import argparse
import sys
from pathlib import Path

# from tools import create_project
from tools.mde_agent import run_once, run_watch
from tools.mde_apply import apply_patch, apply_task

# from tools.mde_doctor import print_report, run_doctor
# from tools.mde_generate import generate_command
# from tools.mde_inbox import list_patches
# from tools.mde_new import AVAILABLE_TEMPLATES, create_project
from tools.mde_save import save

AVAILABLE_COMMANDS = [
    "new",
    "generate",
    "apply",
    "save",
    "agent",
    "inbox",
    #    "doctor",
    "docs",
    "build",
    "release",
    "obsidian",
    "deploy",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mde",
        description="My Development Ecosystem command line interface.",
    )

    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser(
        "new",
        help="Create a new MDE project.",
    )
    new_parser.add_argument(
        "project_name",
        help="Project name.",
    )
    new_parser.add_argument(
        "--template",
        default="shared",
        #        choices=sorted(AVAILABLE_TEMPLATES),
        help="Project template type.",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate MDE code artifacts.",
    )
    generate_subparsers = generate_parser.add_subparsers(dest="generate_target")

    generate_command_parser = generate_subparsers.add_parser(
        "command",
        help="Generate a command module and its test file.",
    )
    generate_command_parser.add_argument(
        "command_name",
        help="Command name.",
    )

    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply a patch file or task manifest.",
    )
    apply_parser.add_argument(
        "source",
        help="Patch file or manifest.yaml path.",
    )
    apply_parser.add_argument(
        "--target",
        help="Target file for a single patch.",
    )
    apply_parser.add_argument(
        "--no-test",
        action="store_true",
        help="Apply without running pytest.",
    )
    apply_parser.add_argument(
        "--remove-backup",
        action="store_true",
        help="Remove backup files after successful application.",
    )

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

    agent_parser = subparsers.add_parser(
        "agent",
        help="Run the MDE mobile automation agent.",
    )

    agent_mode_group = agent_parser.add_mutually_exclusive_group()

    agent_mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run one Agent cycle and exit.",
    )
    agent_mode_group.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor GitHub and process tasks.",
    )

    agent_parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Watch interval in seconds. Minimum: 5.",
    )
    agent_parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Commit and push successfully completed tasks.",
    )

    inbox_parser = subparsers.add_parser(
        "inbox",
        help="Manage legacy inbox patch files.",
    )
    inbox_subparsers = inbox_parser.add_subparsers(dest="inbox_action")
    inbox_subparsers.add_parser(
        "list",
        help="List legacy inbox patches.",
    )

    #    subparsers.add_parser(
    #        "doctor",
    #        help="Check the MDE development environment.",
    #    )

    implemented_commands = {
        "new",
        "generate",
        "apply",
        "save",
        "agent",
        "inbox",
        # "doctor",
    }

    for command in AVAILABLE_COMMANDS:
        if command in implemented_commands:
            continue

        subparsers.add_parser(
            command,
            help=f"Reserved command: {command}",
        )

    return parser


def run_reserved_command(command: str) -> int:
    print(f"'{command}' command is reserved but not implemented yet.")
    return 2


def run_apply_command(args: argparse.Namespace) -> int:
    source_path = Path(args.source)
    run_tests = not args.no_test
    keep_backups = not args.remove_backup

    if source_path.name == "manifest.yaml":
        result = apply_task(
            manifest_path=source_path,
            project_root=Path.cwd(),
            run_tests=run_tests,
            keep_backups=keep_backups,
        )

        print("Task applied.")
        print(f"Files applied: {len(result.results)}")

        for item in result.results:
            print(f"{item.patch_path} -> {item.target_path}")

        return 0

    if not args.target:
        print("--target is required for a single patch.")
        return 1

    result = apply_patch(
        patch_path=source_path,
        target_path=Path(args.target),
        run_tests=run_tests,
        keep_backup=keep_backups,
    )

    print("Patch applied.")
    print(f"Patch: {result.patch_path}")
    print(f"Target: {result.target_path}")
    print(f"Backup: {result.backup_path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        #        if args.command == "new":
        #            created_paths = create_project(
        #                args.project_name,
        #                template_name=args.template,
        #            )

        #            print("Project created.")

        #            for path in created_paths:
        #                print(path)

        #            return 0

        #        if args.command == "generate":
        #            if args.generate_target != "command":
        #                parser.print_help()
        #                return 1

        #            plan = generate_command(args.command_name)

        #            print("Command generated.")
        #            print(f"Tool path: {plan.tool_path}")
        #            print(f"Test path: {plan.test_path}")

        #            return 0

        if args.command == "apply":
            return run_apply_command(args)

        if args.command == "save":
            save(
                commit_message=args.message,
                push=not args.no_push,
            )
            print("MDE save completed.")
            return 0

        if args.command == "agent":
            if args.once:
                run_once(auto_save=args.auto_save)
                return 0

            if args.watch:
                run_watch(
                    interval_seconds=args.interval,
                    auto_save=args.auto_save,
                )
                return 0

            print("Use --once or --watch.")
            return 2

        #        if args.command == "inbox":
        #            if args.inbox_action != "list":
        #                parser.print_help()
        #                return 1

        #            patches = list_patches()

        #            if not patches:
        #                print("No legacy inbox patches.")
        #                return 0

        #            for patch in patches:
        #                print(f"{patch.patch_path} -> {patch.target_path}")

        #            return 0

        #        if args.command == "doctor":
        #            results = run_doctor()
        #           print_report(results)

        #            if any(not result.passed for result in results):
        #                return 1

        #            return 0

        if args.command in AVAILABLE_COMMANDS:
            return run_reserved_command(args.command)

        parser.print_help()
        return 1

    except RuntimeError as error:
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

from tools.mde_apply import ApplyError, apply_task
from tools.mde_git import GitError, has_remote_changes, pull
from tools.mde_lock import AgentLock, LockError
from tools.mde_log import build_log_path, close_logger, create_logger
from tools.mde_queue import (
    QueueError,
    move_to_completed,
    move_to_failed,
    move_to_processing,
    recover_processing_tasks,
)
from tools.mde_save import SaveError, save
from tools.mde_task import TaskError, TaskManifest, load_pending_tasks


class AgentError(RuntimeError):
    """Raised when an MDE agent cycle fails."""


@dataclass(frozen=True)
class AgentResult:
    remote_changed: bool
    recovered_count: int
    completed_tasks: list[str]
    failed_tasks: list[str]
    elapsed_seconds: float


def run_task(task: TaskManifest) -> None:
    """Move and execute one task as a transaction."""
    task_dir = task.manifest_path.parent
    processing_dir = move_to_processing(task_dir)
    processing_manifest = processing_dir / "manifest.yaml"

    try:
        apply_task(
            manifest_path=processing_manifest,
            project_root=Path.cwd(),
            run_tests=True,
            keep_backups=True,
        )
    except (ApplyError, TaskError, OSError) as error:
        try:
            move_to_failed(processing_dir)
        except QueueError as queue_error:
            raise AgentError(
                f"Task failed and could not be moved to failed: "
                f"{task.task_id}: {queue_error}"
            ) from error

        raise AgentError(f"Task failed: {task.task_id}: {error}") from error

    try:
        move_to_completed(processing_dir)
    except QueueError as error:
        raise AgentError(
            f"Task succeeded but could not be moved to completed: "
            f"{task.task_id}: {error}"
        ) from error


def run_pending_tasks() -> tuple[list[str], list[str]]:
    """Find and execute every task under inbox/tasks."""
    tasks = load_pending_tasks()

    if not tasks:
        print("No pending tasks.")
        return [], []

    completed_tasks: list[str] = []
    failed_tasks: list[str] = []

    for task in tasks:
        print(f"Running task: {task.task_id}")

        try:
            run_task(task)
        except AgentError as error:
            failed_tasks.append(task.task_id)
            print(error)
            continue

        completed_tasks.append(task.task_id)
        print(f"Task completed: {task.task_id}")

    return completed_tasks, failed_tasks


def sync_remote() -> bool:
    """Pull the remote repository only when its HEAD differs."""
    print("Checking GitHub changes...")

    if not has_remote_changes():
        print("No remote changes.")
        return False

    print("Remote changes detected.")
    print("Running git pull...")
    pull()

    return True


def run_once(auto_save: bool = False) -> AgentResult:
    """Run one complete Agent cycle."""
    started_at = time.perf_counter()
    log_path = build_log_path("agent")
    logger = create_logger("mde.agent", log_path)

    try:
        with AgentLock():
            logger.info("MDE agent cycle started.")

            print("================================")
            print("MDE Agent")
            print("================================")
            print(f"Log: {log_path}")

            recovered_tasks = recover_processing_tasks()

            for recovered_path in recovered_tasks:
                logger.warning(
                    "Recovered interrupted task to failed: %s",
                    recovered_path,
                )
                print(f"Recovered interrupted task: {recovered_path}")

            remote_changed = sync_remote()
            logger.info("Remote changed: %s", remote_changed)

            completed_tasks, failed_tasks = run_pending_tasks()

            for task_id in completed_tasks:
                logger.info("Task completed: %s", task_id)

            for task_id in failed_tasks:
                logger.error("Task failed: %s", task_id)

            if failed_tasks:
                raise AgentError("One or more tasks failed: " + ", ".join(failed_tasks))

            if auto_save and completed_tasks:
                print("Running mde save...")
                logger.info("Running automatic save and push.")

                save(
                    commit_message="chore(agent): apply mobile tasks",
                    push=True,
                )
            elif auto_save:
                print("Auto-save skipped: no completed tasks.")
                logger.info("Auto-save skipped because no tasks were completed.")

            elapsed_seconds = time.perf_counter() - started_at

            result = AgentResult(
                remote_changed=remote_changed,
                recovered_count=len(recovered_tasks),
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                elapsed_seconds=elapsed_seconds,
            )

            logger.info(
                "Agent completed: recovered=%d completed=%d failed=%d elapsed=%.2f",
                result.recovered_count,
                len(result.completed_tasks),
                len(result.failed_tasks),
                result.elapsed_seconds,
            )

            print()
            print("Agent result")
            print("--------------------------------")
            print(f"GitHub changed : {result.remote_changed}")
            print(f"Recovered      : {result.recovered_count}")
            print(f"Completed      : {len(result.completed_tasks)}")
            print(f"Failed         : {len(result.failed_tasks)}")
            print(f"Elapsed        : {result.elapsed_seconds:.2f} seconds")
            print("================================")

            return result

    except (
        AgentError,
        ApplyError,
        GitError,
        LockError,
        QueueError,
        SaveError,
        TaskError,
    ):
        logger.exception("MDE agent cycle failed.")
        raise

    finally:
        close_logger(logger)


def run_watch(
    interval_seconds: int = 30,
    auto_save: bool = False,
    max_cycles: int | None = None,
) -> None:
    """Continuously execute Agent cycles until Ctrl+C."""
    if interval_seconds < 5:
        raise AgentError("Watch interval must be at least 5 seconds.")

    cycle = 0

    try:
        while True:
            cycle += 1

            print()
            print(f"Agent watch cycle: {cycle}")

            try:
                run_once(auto_save=auto_save)
            except (
                AgentError,
                ApplyError,
                GitError,
                LockError,
                QueueError,
                SaveError,
                TaskError,
            ) as error:
                print(f"Agent cycle failed: {error}")

            if max_cycles is not None and cycle >= max_cycles:
                return

            print(f"Next check in {interval_seconds} seconds...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print()
        print("MDE agent watch stopped.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MDE mobile automation agent.")

    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run one Agent cycle and exit.",
    )
    mode_group.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor GitHub and process tasks.",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Watch interval in seconds. Minimum: 5.",
    )
    parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Commit and push successfully completed tasks.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
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

    except (
        AgentError,
        ApplyError,
        GitError,
        LockError,
        QueueError,
        SaveError,
        TaskError,
    ) as error:
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

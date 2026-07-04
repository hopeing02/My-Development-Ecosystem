from __future__ import annotations

import pytest

from tools.mde_save import SaveError, build_parser, save


def test_parser_requires_commit_message() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_accepts_commit_message() -> None:
    parser = build_parser()

    args = parser.parse_args(["-m", "feat: test save"])

    assert args.message == "feat: test save"
    assert args.no_push is False


def test_parser_accepts_no_push() -> None:
    parser = build_parser()

    args = parser.parse_args(["-m", "feat: test save", "--no-push"])

    assert args.message == "feat: test save"
    assert args.no_push is True


def test_save_runs_expected_commands_without_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run_required(command: list[str]) -> None:
        commands.append(command)

    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    save(commit_message="feat: test save", push=False)

    assert commands == [
        ["uv", "run", "black", "."],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "pytest"],
        ["git", "add", "."],
        ["git", "commit", "-m", "feat: test save"],
    ]


def test_save_runs_expected_commands_with_push(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run_required(command: list[str]) -> None:
        commands.append(command)

    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    save(commit_message="feat: test save", push=True)

    assert commands[-1] == ["git", "push"]


def test_save_stops_when_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_required(command: list[str]) -> None:
        if command == ["uv", "run", "black", "."]:
            raise SaveError("Command failed: uv run black .")

    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    with pytest.raises(SaveError):
        save(commit_message="feat: test save", push=True)

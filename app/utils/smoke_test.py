"""Minimal smoke test to ensure the CLI exposes expected commands."""

from __future__ import annotations

import main


def test_cli_registers_commands():
    parser = main.build_parser()
    subparsers = {
        name for action in parser._subparsers._group_actions for name in action.choices
    }
    assert {"extract", "templates"}.issubset(subparsers)


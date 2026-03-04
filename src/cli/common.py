<<<<<<< HEAD
"""Shared CLI helpers: prompts and input parsing."""
=======
"""
File    : common.py
Author  : Shane del Villar
Desc    : Shared CLI helpers: prompts and input parsing."""
>>>>>>> origin/develop

from __future__ import annotations


def prompt(msg: str, default: str = "") -> str:
    """Prompt for a string. If default is non-empty, show it and accept blank for default."""
    if default:
        raw = input(f"{msg} [{default}]: ").strip()
        return raw if raw else default
    return input(f"{msg}: ").strip()


def prompt_int(msg: str, default: int) -> int:
    """Prompt for an integer; use default if user enters blank."""
    while True:
        raw = input(f"{msg} [{default}]: ").strip()
        if raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")


def prompt_list(msg: str, default: list[str]) -> list[str]:
    """Prompt for a comma-separated list; return default if blank."""
    raw = input(f"{msg}: ").strip()
    if not raw:
        return list(default)
    return [s.strip() for s in raw.split(",") if s.strip()]

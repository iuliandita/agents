#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from render_prompts import harness_display_names, harness_target_rows


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    install = (repo_root / "INSTALL.md").read_text(encoding="utf-8")
    failures: list[str] = []

    for display in harness_display_names():
        if display not in readme:
            failures.append(f"README.md missing harness display name: {display}")
        if f"| {display} |" not in install:
            failures.append(f"INSTALL.md missing harness table row: {display}")

    for display, support, target, notes in harness_target_rows():
        expected = f"| {display} | {support} | `{target}` |"
        if expected not in install:
            failures.append(f"INSTALL.md target row drifted for {display}: {support} {target}")
        if notes and notes not in install:
            failures.append(f"INSTALL.md missing harness notes for {display}: {notes}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    print("Harness docs check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

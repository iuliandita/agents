#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from render_prompts import harness_display_names, harness_target_rows


START = "<!-- harness-targets:start -->"
END = "<!-- harness-targets:end -->"


def render_table() -> str:
    lines = ["| Harness | Support | Target | Notes |", "|---|---|---|---|"]
    for display, support, target, notes in harness_target_rows():
        lines.append(f"| {display} | {support} | `{target}` | {notes} |")
    return "\n".join(lines)


def replace_region(text: str, body: str) -> str:
    start = text.index(START)
    end = text.index(END)
    return text[:start] + START + "\n" + body + "\n" + text[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check INSTALL/README harness docs against the registry.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true", help="Regenerate the INSTALL harness table in place.")
    args = parser.parse_args(argv)

    install_path = args.repo_root / "INSTALL.md"
    install = install_path.read_text(encoding="utf-8")
    readme = (args.repo_root / "README.md").read_text(encoding="utf-8")

    if args.write:
        if START not in install or END not in install:
            print(f"ERROR: INSTALL.md is missing the {START} / {END} markers")
            return 1
        install_path.write_text(replace_region(install, render_table()), encoding="utf-8", newline="\n")
        print("Regenerated INSTALL.md harness table")
        return 0

    failures: list[str] = []
    for display in harness_display_names():
        if display not in readme:
            failures.append(f"README.md missing harness display name: {display}")
        if f"| {display} |" not in install:
            failures.append(f"INSTALL.md missing harness table row: {display}")

    for display, support, target, notes in harness_target_rows():
        expected = f"| {display} | {support} | `{target}` | {notes} |"
        if expected not in install:
            failures.append(f"INSTALL.md target row drifted for {display}: {support} {target} {notes}")

    if START in install and END in install:
        region = install[install.index(START) + len(START) : install.index(END)].strip("\n")
        if region != render_table():
            failures.append(
                "INSTALL.md harness table region drifted from the registry; "
                "run python scripts/check_harness_docs.py --write"
            )

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    print("Harness docs check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

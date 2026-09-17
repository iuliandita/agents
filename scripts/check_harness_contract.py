#!/usr/bin/env python3
"""Assert every supported harness carries verification receipts and is documented."""
from __future__ import annotations

from pathlib import Path

from render_prompts import HARNESSES


REQUIRED_DOCS = ("docs/harness-contract.md", "docs/surfaces.md", "docs/legacy-harnesses.md")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    failures: list[str] = []

    for harness in HARNESSES:
        if harness.name != "generic" and not harness.source_url:
            failures.append(f"{harness.name}: missing source_url receipt")
        if not harness.verified_on:
            failures.append(f"{harness.name}: missing verified_on date")

    for doc in REQUIRED_DOCS:
        if not (repo_root / doc).exists():
            failures.append(f"missing {doc}")
            continue
        if doc != "docs/harness-contract.md":
            continue
        text = (repo_root / doc).read_text(encoding="utf-8")
        for harness in HARNESSES:
            token = harness.display.split()[0]
            if token not in text:
                failures.append(f"{harness.name}: '{token}' not documented in {doc}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print("Harness contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

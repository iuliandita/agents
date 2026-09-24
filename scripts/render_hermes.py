#!/usr/bin/env python3
"""Merge the shared core into Hermes global rules.

Hermes has no global Markdown rules file: global operational rules live in
``agent.coding_instructions`` in ``$HERMES_HOME/config.yaml``. This merges the
rendered document into that key with a comment-preserving, line-based edit and
backs the file up first. Project-level rules still deploy to ``HERMES.md`` or
``AGENTS.override.md`` through ``sync-ai-prompts`` with ``HERMES_AGENTS_PATH``.

``hermes config set`` rewrites the YAML and drops comments, so this does a
targeted key edit instead of a full round-trip.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import render_prompts
from render_prompts import backup_existing


KEY = "coding_instructions"
AGENT = "agent"
INDENT = "  "
CONTENT_INDENT = "    "


def hermes_config_path(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    if values.get("HERMES_CONFIG_PATH"):
        return Path(values["HERMES_CONFIG_PATH"]).expanduser()
    if values.get("HERMES_HOME"):
        return Path(values["HERMES_HOME"]).expanduser() / "config.yaml"
    if os.name == "nt" and values.get("LOCALAPPDATA"):
        return Path(values["LOCALAPPDATA"]) / "hermes" / "config.yaml"
    return Path.home() / ".hermes" / "config.yaml"


def render_rules(repo_root: Path) -> str:
    harness = render_prompts.harness_by_name("hermes")
    overlays = render_prompts.load_overlays(repo_root)
    notice = render_prompts.withheld_notice(overlays, [harness.name])
    if notice:
        print(notice)
    core = (repo_root / "prompts" / "core.md").read_text(encoding="utf-8")
    # agent.coding_instructions is a global rules slot, unlike Hermes' project-file target.
    return render_prompts.render_for(repo_root, harness, core, overlays, with_overlays=True)


def _block_end(lines: list[str], start: int, min_indent: int) -> int:
    """First index at or after start whose indent is <= min_indent (blanks peek ahead)."""
    index = start
    while index < len(lines):
        line = lines[index]
        if line.strip() == "":
            peek = index
            while peek < len(lines) and lines[peek].strip() == "":
                peek += 1
            if peek < len(lines) and len(lines[peek]) - len(lines[peek].lstrip()) > min_indent:
                index = peek
                continue
            return index
        if len(line) - len(line.lstrip()) > min_indent:
            index += 1
            continue
        return index
    return index


def _value_block(rules: str) -> list[str]:
    body = rules.rstrip("\n").split("\n")
    return [f"{INDENT}{KEY}: |"] + [f"{CONTENT_INDENT}{line}" if line else "" for line in body]


def merge_coding_instructions(text: str, rules: str) -> str:
    """Set agent.coding_instructions while preserving every other line verbatim."""
    block = _value_block(rules)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    agent_index = next(
        (index for index, line in enumerate(lines) if re.match(rf"^{AGENT}:\s*(#.*)?$", line)),
        None,
    )
    if agent_index is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{AGENT}:")
        lines.extend(block)
    else:
        end = _block_end(lines, agent_index + 1, 0)
        key_index = next(
            (
                index
                for index in range(agent_index + 1, end)
                if lines[index].startswith(f"{INDENT}{KEY}:")
            ),
            None,
        )
        if key_index is None:
            lines[agent_index + 1 : agent_index + 1] = block
        else:
            value_end = key_index + 1
            after_colon = lines[key_index].split(":", 1)[1].strip()
            if after_colon[:1] in ("|", ">"):
                value_end = _block_end(lines, key_index + 1, len(INDENT))
            lines[key_index:value_end] = block

    result = "\n".join(lines) + "\n"
    return result


def render_preview(repo_root: Path, out_dir: Path) -> Path:
    destination = out_dir / "hermes" / "coding_instructions.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_rules(repo_root), encoding="utf-8", newline="\n")
    return destination


def deploy(repo_root: Path, config_path: Path, backup_dir: Path, dry_run: bool) -> int:
    rules = render_rules(repo_root)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else f"{AGENT}:\n"
    merged = merge_coding_instructions(original, rules)
    if merged == original:
        print(f"unchanged hermes: {config_path}")
        return 0
    if dry_run:
        print(f"would update hermes: {config_path}")
        return 0
    backup_existing(config_path, backup_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(merged, encoding="utf-8", newline="\n")
    print(f"updated hermes: {config_path}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Merge the shared core into Hermes global rules.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--out-dir", type=Path, default=repo_root / "build" / "generated")
    parser.add_argument("--path", type=Path, help="Hermes config.yaml (default: $HERMES_HOME/config.yaml).")
    parser.add_argument("--deploy", action="store_true", help="Merge into Hermes config.yaml.")
    parser.add_argument("--dry-run", action="store_true", help="Print the target without writing.")
    parser.add_argument("--backup-dir", type=Path, default=repo_root / ".backups", help="Directory for backups.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = args.path or hermes_config_path()
    if args.deploy or args.dry_run:
        return deploy(args.repo_root, config_path, args.backup_dir, args.dry_run)
    preview = render_preview(args.repo_root, args.out_dir)
    print(f"rendered hermes: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

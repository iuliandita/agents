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
import sys
from pathlib import Path

import render_prompts
from render_prompts import EXIT_CODES_HELP, JsonArgumentParser, backup_existing, json_record, run_json


KEY = "coding_instructions"
AGENT = "agent"
INDENT = "  "


def hermes_config_path(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    if values.get("HERMES_CONFIG_PATH"):
        return Path(values["HERMES_CONFIG_PATH"]).expanduser()
    if values.get("HERMES_HOME"):
        return Path(values["HERMES_HOME"]).expanduser() / "config.yaml"
    if os.name == "nt" and values.get("LOCALAPPDATA"):
        return Path(values["LOCALAPPDATA"]) / "hermes" / "config.yaml"
    return Path.home() / ".hermes" / "config.yaml"


def render_rules(repo_root: Path, *, with_overlays: bool = True) -> str:
    harness = render_prompts.harness_by_name("hermes")
    overlays = render_prompts.load_overlays(repo_root)
    notice = render_prompts.withheld_notice(overlays, [harness.name]) if with_overlays else None
    if notice:
        print(notice, file=sys.stderr)
    core = (repo_root / "prompts" / "core.md").read_text(encoding="utf-8")
    # agent.coding_instructions is a global rules slot, unlike Hermes' project-file target.
    return render_prompts.render_for(repo_root, harness, core, overlays, with_overlays=with_overlays)


def _key_pattern(key: str) -> str:
    return rf"(?:{key}|\"{key}\"|'{key}')\s*:"


def _block_end(lines: list[str], start: int, min_indent: int) -> int:
    """First index whose indent is <= min_indent (blanks and comments peek ahead)."""
    index = start
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            peek = index
            while peek < len(lines) and (not lines[peek].strip() or lines[peek].lstrip().startswith("#")):
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


def _value_block(rules: str, indent: str = INDENT) -> list[str]:
    body = rules.rstrip("\n").split("\n")
    content_indent = indent + INDENT
    return [f"{indent}{KEY}: |"] + [f"{content_indent}{line}" if line else "" for line in body]


def _child_indent(lines: list[str], start: int, end: int) -> str:
    """Indent of the first key in lines[start:end]; the default when the block is empty."""
    for line in lines[start:end]:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = line[: len(line) - len(stripped)]
        if "\t" in indent:
            raise SystemExit(f"error: {AGENT}: block is indented with tabs; YAML does not allow that")
        return indent
    return INDENT


def _structure(text: str) -> tuple[list[str], int]:
    """Inspect block-mapping keys without a YAML dependency or scalar contents."""
    top_keys: list[str] = []
    coding_keys = 0
    in_agent = False
    child_indent = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            match = re.match(r'''^(?:"([^"]*)"|'((?:[^']|'')*)'|([^'"#][^:]*?))\s*:''', line)
            key = next((group for group in match.groups() if group is not None), "").strip() if match else ""
            if match:
                top_keys.append(key)
            in_agent = key == AGENT
            child_indent = None
        elif in_agent:
            if child_indent is None:
                child_indent = indent
            if indent == child_indent and re.match(rf"^\s+{_key_pattern(KEY)}", line):
                coding_keys += 1
    return top_keys, coding_keys


def _check_structure(original: str, merged: str) -> None:
    before, _ = _structure(original)
    after, coding_keys = _structure(merged)
    if after.count(AGENT) > 1 or coding_keys > 1:
        raise SystemExit(f"error: duplicate {AGENT} or {AGENT}.{KEY} keys; refusing to write")
    missing = set(before) - set(after)
    if missing:
        raise SystemExit(f"error: merge removed top-level keys: {', '.join(sorted(missing))}; refusing to write")


def merge_coding_instructions(text: str, rules: str) -> str:
    """Set agent.coding_instructions while preserving every other line verbatim."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    agent_index = None
    for index, line in enumerate(lines):
        match = re.match(rf"^{_key_pattern(AGENT)}(.*)$", line)
        if match is None:
            continue
        rest = match.group(1).strip()
        if rest and not rest.startswith("#"):
            # A flow mapping or scalar here cannot take a block key; appending a
            # second agent: key would make YAML loaders drop the first.
            raise SystemExit(
                f"error: top-level '{AGENT}:' has an inline value ({rest}); "
                f"rewrite it as a block mapping, then rerun"
            )
        agent_index = index
        break

    if agent_index is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{AGENT}:")
        lines.extend(_value_block(rules))
    else:
        end = _block_end(lines, agent_index + 1, 0)
        indent = _child_indent(lines, agent_index + 1, end)
        block = _value_block(rules, indent)
        key_index = next(
            (
                index
                for index in range(agent_index + 1, end)
                if re.match(rf"^{re.escape(indent)}{_key_pattern(KEY)}", lines[index])
            ),
            None,
        )
        if key_index is None:
            lines[agent_index + 1 : agent_index + 1] = block
        else:
            # Block scalars, multi-line plain scalars, and nested values all end
            # at the next line indented no deeper than the key itself.
            value_end = _block_end(lines, key_index + 1, len(indent))
            lines[key_index:value_end] = block

    result = "\n".join(lines) + "\n"
    _check_structure(text, result)
    return result


def render_preview(repo_root: Path, out_dir: Path) -> Path:
    destination = out_dir / "hermes" / "coding_instructions.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_rules(repo_root), encoding="utf-8", newline="\n")
    return destination


def _inside_work_tree(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    return any((parent / ".git").exists() for parent in resolved.parents)


def deploy(
    repo_root: Path, config_path: Path, backup_dir: Path, dry_run: bool, *, env_override: bool = False
) -> int:
    if config_path.is_symlink():
        raise SystemExit(
            f"error: {config_path} is a symlink; refusing to write through it. "
            "Move it aside or point HERMES_CONFIG_PATH at a regular file."
        )
    withheld = env_override and _inside_work_tree(config_path)
    if withheld:
        print(
            "note: prompts/local.md and prompts/private.md withheld from hermes; "
            "environment-selected config resolves inside a git work tree",
            file=sys.stderr,
        )
    rules = render_rules(repo_root, with_overlays=not withheld)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else f"{AGENT}:\n"
    merged = merge_coding_instructions(original, rules)
    if merged == original:
        print(f"unchanged hermes: {config_path}")
        json_record(harness="hermes", action="unchanged", path=str(config_path))
        return 0
    if dry_run:
        if KEY in original and render_prompts.PROMPT_MARKER not in original:
            print(f"would replace unmanaged hermes {AGENT}.{KEY}: {config_path} (not written by this repo; backed up first)")
            json_record(harness="hermes", action="would-replace-unmanaged", path=str(config_path))
        else:
            print(f"would update hermes: {config_path}")
            json_record(harness="hermes", action="would-update", path=str(config_path))
        return 0
    backup_existing(config_path, backup_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(merged, encoding="utf-8", newline="\n")
    print(f"updated hermes: {config_path}")
    json_record(harness="hermes", action="updated", path=str(config_path))
    return 0


HELP_EPILOG = """\
Environment:
  AGENTS_PYTHON            Python 3.11+ executable the launcher runs (a path, not a command).
  HERMES_CONFIG_PATH       Hermes config.yaml (wins over HERMES_HOME).
  HERMES_HOME              Hermes home; the config is <HERMES_HOME>/config.yaml.
  LOCALAPPDATA             On Windows, the default config is %LOCALAPPDATA%\\hermes\\config.yaml.
  AGENTS_PRIVATE_HARNESSES Comma-separated harnesses that receive prompts/private.md; 'all' for every one.
  HOME                     Resolves the default ~/.hermes/config.yaml.

""" + EXIT_CODES_HELP


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = JsonArgumentParser(
        description="Merge the shared core into Hermes global rules.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--out-dir", type=Path, default=repo_root / "build" / "generated")
    parser.add_argument("--path", type=Path, help="Hermes config.yaml (default: $HERMES_HOME/config.yaml).")
    parser.add_argument("--deploy", action="store_true", help="Merge into Hermes config.yaml.")
    parser.add_argument("--dry-run", action="store_true", help="Print the target without writing.")
    parser.add_argument("--backup-dir", type=Path, default=repo_root / ".backups", help="Directory for backups.")
    parser.add_argument("--json", action="store_true", help="Print one JSON object to stdout; human output goes to stderr.")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    config_path = args.path or hermes_config_path()
    if args.deploy or args.dry_run:
        env_override = args.path is None and bool(os.environ.get("HERMES_CONFIG_PATH") or os.environ.get("HERMES_HOME"))
        return deploy(args.repo_root, config_path, args.backup_dir, args.dry_run, env_override=env_override)
    preview = render_preview(args.repo_root, args.out_dir)
    print(f"rendered hermes: {preview}")
    json_record(harness="hermes", path=str(preview))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.json:
        return run(args)
    if args.deploy or args.dry_run:
        return run_json(lambda: run(args), "render-hermes", "actions", mode="deploy", dry_run=args.dry_run)
    return run_json(lambda: run(args), "render-hermes", "rendered", mode="render")


if __name__ == "__main__":
    raise SystemExit(main())

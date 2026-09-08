#!/usr/bin/env python3
"""Copy the canonical consolidation skill to explicitly selected locations."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "consolidate-agents-md"


def checked_path(path: Path, *, directory: bool = False) -> Path:
    path = path.expanduser().absolute()
    if ".." in path.parts:
        raise ValueError(f"Parent traversal is not supported: {path}")
    for ancestor in reversed(path.parents):
        if ancestor.is_symlink():
            raise ValueError(f"Symlink ancestor refused: {ancestor}")
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError(f"Ancestor is not a directory: {ancestor}")
    if path.is_symlink():
        raise ValueError(f"Symlink target refused: {path}")
    if path.exists() and not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f"Target has the wrong file type: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, action="append", required=True,
                        help="Skill directory to install into; repeat for multiple locations")
    parser.add_argument("--legacy-command", type=Path,
                        help="Optional legacy Markdown command to migrate")
    parser.add_argument("--deploy", action="store_true", help="Write files (default: dry run)")
    args = parser.parse_args(argv)
    try:
        source = REPO_ROOT / "skills" / SKILL_NAME / "SKILL.md"
        content = source.read_bytes()
        lines = content.decode("utf-8").splitlines()
        if not lines or lines[0] != "---" or "---" not in lines[1:]:
            raise ValueError("Canonical skill must have YAML frontmatter")
        end = lines.index("---", 1)
        try:
            metadata = yaml.safe_load("\n".join(lines[1:end]))
        except yaml.YAMLError:
            raise ValueError("Canonical skill has invalid YAML frontmatter") from None
        if (not isinstance(metadata, dict) or metadata.get("name") != source.parent.name
                or not isinstance(metadata.get("description"), str)
                or not metadata["description"].strip()):
            raise ValueError("Canonical skill needs a matching name and nonempty description")

        targets = [directory / SKILL_NAME / "SKILL.md" for directory in args.skills_dir]
        if args.legacy_command is not None:
            targets.append(args.legacy_command)
        targets = list(dict.fromkeys(checked_path(target) for target in targets))
        if any(left in right.parents for left in targets for right in targets):
            raise ValueError("Destination files cannot be ancestors of other destinations")
        changed = [target for target in targets
                   if not target.exists() or target.read_bytes() != content]
        overwritten = [target for target in changed if target.exists()]
        backup_root = REPO_ROOT / ".backups"
        if overwritten:
            checked_path(backup_root, directory=True)
            if any(target == backup_root or target in backup_root.parents for target in targets):
                raise ValueError("Destination conflicts with the backup directory")
        if not args.deploy:
            for target in changed:
                print(f"Would install: {target}")
            print(f"Dry run: {len(changed)} change(s); use --deploy to write")
            return 0

        if overwritten:
            backup_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            backup_dir = Path(tempfile.mkdtemp(prefix="workflow-", dir=backup_root))
            for index, target in enumerate(overwritten):
                backup = backup_dir / f"{index}-{target.name}"
                backup.write_bytes(target.read_bytes())
                backup.chmod(0o600)
                print(f"Backup: {target} -> {backup}")
        for target in changed:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".workflow-", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
            print(f"Installed: {target}")
        print(f"Installed {len(changed)} change(s)")
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

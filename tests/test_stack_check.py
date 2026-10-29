import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STACK = REPO / ".github" / "stack"
SHA = "a" * 40
CANON = json.loads((STACK / "canon.json").read_text(encoding="utf-8"))
NAME = "mods"


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IEND", b"")


def stack_lines() -> str:
    cfg = CANON["readme"]
    lines = []
    for item in cfg["stack_repos"]:
        if item["name"] == NAME:
            lines.append(f"- {item['name']}: {item['description']}")
        else:
            lines.append(f"- [{item['name']}]({cfg['stack_url_prefix']}{item['name']}): {item['description']}")
    return "\n".join(lines) + "\n\n" + cfg["stack_closing"]


README = f"""<h1><img src="assets/wordmark.png" alt="{NAME}" width="360"></h1>

Hooks for coding agents that run with your permissions, installed one at a time, for people who use several harnesses and want each guard kept small.

It adds checks before tools run and writes only to the harness settings you name.

Status: prerelease. `main` is the stable channel and `develop` the nightly.

## Install

Run the installer.

## Usage

Run the tool.

## Compatibility

Works with three harnesses.

## License

MIT.

## Part of the stack

{stack_lines()}

## Project and support

{CANON['readme']['project_line']}
"""

CONTRIBUTING = f"""# Contributing

{CANON['contributing']['opening']}

## Sources and generated files

Edit sources.

## Checks and documentation

```sh
python -m pytest -q
```

## Releases

Feature PRs target `develop`. Move the `Unreleased` entries under the new version, merge to `main`, and tag.
"""

WORKFLOW = f"""name: CI

on:
  pull_request:

permissions:
  contents: read

jobs:
  lint:
    name: lint
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - name: Check out
        uses: actions/checkout@{SHA} # v4.2.2
        with:
          persist-credentials: false
      - uses: actions/setup-python@{SHA} # v5.0.0
        with:
          python-version: "3.12"
      - run: echo hi

  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@{SHA} # v4.2.2
        with:
          persist-credentials: false
      - run: echo hi
"""

TOOL = """import sys

if "--help" in sys.argv:
    print("usage: tool [--check] [--json]\\n\\nOptions:\\n  --check  read only\\n  --json   JSON output")
    print("\\nEnvironment:\\n  none\\n\\nExit codes:\\n  0 ok\\n  1 failed")
    raise SystemExit(0)
raise SystemExit("error: tool: nothing to do; run tool --help")
"""

REPO_JSON = {
    "repo": NAME,
    "required_jobs": ["lint", "test"],
    "installers": [{"argv": ["python3", "bin/tool.py", "--help"], "flags": ["--check", "--json"]}],
    "error_scan": {"paths": ["bin"], "exclude": []},
    "allow": [],
}


def write(repo: Path, rel: str, text: str | bytes) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")


def edit(repo: Path, rel: str, old: str, new: str) -> None:
    text = (repo / rel).read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {rel}"
    (repo / rel).write_text(text.replace(old, new, 1), encoding="utf-8")


def run(repo: Path, *args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(repo / ".github/stack/stack-check.py"), "--json", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return proc.returncode, json.loads(proc.stdout)


def hits(data: dict) -> set[str]:
    return {f["check"] for f in data["findings"]}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    stack = tmp_path / ".github" / "stack"
    stack.mkdir(parents=True)
    for name in ("canon.json", "stack-check.py"):
        shutil.copy(STACK / name, stack / name)
    write(tmp_path, ".github/stack/repo.json", json.dumps(REPO_JSON))
    write(tmp_path, "README.md", README)
    write(tmp_path, "CONTRIBUTING.md", CONTRIBUTING)
    write(tmp_path, ".github/workflows/ci.yml", WORKFLOW)
    write(tmp_path, "bin/tool.py", TOOL)
    write(tmp_path, "assets/logo.png", png(1024, 1024))
    write(tmp_path, "assets/logo-256.png", png(256, 256))
    write(tmp_path, "assets/wordmark.png", png(900, 200))
    source = subprocess.run(
        [sys.executable, str(stack / "stack-check.py"), "--print-source", SHA],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    write(tmp_path, ".github/stack/SOURCE", source)
    return tmp_path


def test_fixture_repo_passes(repo: Path) -> None:
    code, data = run(repo)
    assert data["errors"] == []
    assert code == 0
    assert data["ok"] is True
    assert data["repo"] == NAME


def test_json_shape_on_findings(repo: Path) -> None:
    edit(repo, "README.md", f'alt="{NAME}"', 'alt="wrong"')
    code, data = run(repo)
    assert code == 1
    assert data["ok"] is False
    assert set(data) == {"ok", "errors", "findings", "checks", "repo"}
    assert len(data["errors"]) == len(data["findings"]) == 1
    finding = data["findings"][0]
    assert set(finding) == {"check", "file", "line", "message", "fix"}
    assert data["errors"][0].startswith("error: readme-title: README.md:1: ")
    assert "; " in data["errors"][0]


def test_human_output_goes_to_stderr_with_exit_one(repo: Path) -> None:
    edit(repo, "README.md", f'alt="{NAME}"', 'alt="wrong"')
    proc = subprocess.run(
        [sys.executable, str(repo / ".github/stack/stack-check.py")], cwd=repo, capture_output=True, text=True
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.splitlines()[0].startswith("error: readme-title: ")


def test_list_checks(repo: Path) -> None:
    code, data = run(repo, "--list-checks")
    assert code == 0 and data["ok"] is True
    ids = [c["id"] for c in data["checks"]]
    assert "readme-title" in ids and "private-patterns" in ids and len(ids) == len(set(ids))


def test_usage_errors_exit_two(repo: Path) -> None:
    code, data = run(repo, "--only", "no-such-check")
    assert code == 2 and data["ok"] is False and data["errors"][0].startswith("error: stack-check: ")
    (repo / ".github/stack/repo.json").unlink()
    code, data = run(repo)
    assert code == 2 and "repo.json" in data["errors"][0]


def test_unknown_flag_exits_two(repo: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(repo / ".github/stack/stack-check.py"), "--bogus"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert proc.stderr.startswith("error: stack-check: ")


def test_help_has_environment_and_exit_codes(repo: Path) -> None:
    out = subprocess.run(
        [sys.executable, str(repo / ".github/stack/stack-check.py"), "--help"], capture_output=True, text=True
    ).stdout
    assert "Environment:" in out and "Exit codes:" in out and "--json" in out


def stack_edit(repo: Path) -> None:
    edit(repo, "README.md", f"- {NAME}: ", f"- [{NAME}](https://github.com/iuliandita/{NAME}): ")


def long_intro(repo: Path) -> None:
    edit(repo, "README.md", "Hooks for coding agents", "Hooks for coding agents " + "that matter a great deal " * 20)


# Built from parts so this file does not trip the private-pattern scan of the repo that ships it.
HOME_PATH = "/home" + "/someone/project/"
MAC_PATH = "/Users" + "/someone/x"
PRIVATE_IP = "192.168" + ".4.20"
AT = "@"

MD_TITLE = f'# {NAME}\n\n<p><img src="assets/wordmark.png" alt="{NAME} wordmark" width="360"></p>'

def drop_json_flag(repo: Path) -> None:
    edit(repo, "bin/tool.py", "  --json   JSON output", "")
    edit(repo, "bin/tool.py", " [--json]", "")


FAILURES = [
    ("readme-title", lambda r: edit(r, "README.md", f'alt="{NAME}"', f'alt="{NAME}."')),
    ("readme-title", lambda r: edit(r, "README.md", README.splitlines()[0], MD_TITLE.replace(NAME, NAME + ".", 1))),
    ("readme-wordmark", lambda r: edit(r, "README.md", "assets/wordmark.png", "assets/other.png")),
    ("readme-intro", lambda r: edit(r, "README.md", "Hooks for coding agents that run with your permissions, installed one at a time, for people who use several harnesses and want each guard kept small.", "Hooks for coding agents.")),
    ("readme-intro", long_intro),
    ("readme-intro", lambda r: edit(r, "README.md", "Hooks for coding agents", "**Hooks** for coding agents")),
    ("readme-intro", lambda r: edit(r, "README.md", "kept small.", "kept small in v1.2.0.")),
    ("readme-status", lambda r: edit(r, "README.md", "Status: prerelease. `main` is the stable channel and `develop` the nightly.", "")),
    ("readme-status", lambda r: edit(r, "README.md", "and `develop` the nightly", "only")),
    ("readme-sections", lambda r: edit(r, "README.md", "## Compatibility", "## Supported Harnesses")),
    ("readme-sections", lambda r: edit(r, "README.md", "## Install\n\nRun the installer.\n\n## Usage\n\nRun the tool.", "## Usage\n\nRun the tool.\n\n## Install\n\nRun the installer.")),
    ("readme-stack", stack_edit),
    ("readme-stack", lambda r: edit(r, "README.md", "Installing one does not install the others.", "Install them all.")),
    ("readme-project", lambda r: edit(r, "README.md", CANON["readme"]["project_line"], CANON["readme"]["project_line"] + "\n\nSee [skills](https://github.com/iuliandita/skills).")),
    ("assets", lambda r: (r / "assets/wordmark.png").unlink()),
    ("assets", lambda r: write(r, "assets/logo.png", png(512, 512))),
    ("assets", lambda r: write(r, "assets/logo-256.png", b"not a png")),
    ("contributing", lambda r: edit(r, "CONTRIBUTING.md", "Branch from `develop`, ", "")),
    ("contributing", lambda r: edit(r, "CONTRIBUTING.md", "## Releases", "## Shipping")),
    ("contributing", lambda r: edit(r, "CONTRIBUTING.md", "```sh", "```text")),
    ("contributing", lambda r: edit(r, "CONTRIBUTING.md", "`Unreleased`", "the")),
    ("workflow-jobs", lambda r: edit(r, ".github/workflows/ci.yml", "  lint:\n    name: lint", "  check:\n    name: check")),
    ("workflow-jobs", lambda r: edit(r, ".github/workflows/ci.yml", "name: lint", "name: Lint and test")),
    ("workflow-pins", lambda r: edit(r, ".github/workflows/ci.yml", f"actions/setup-python@{SHA} # v5.0.0", "actions/setup-python@v5")),
    ("workflow-pins", lambda r: edit(r, ".github/workflows/ci.yml", f"actions/setup-python@{SHA} # v5.0.0", f"actions/setup-python@{SHA}")),
    ("workflow-timeouts", lambda r: edit(r, ".github/workflows/ci.yml", "    timeout-minutes: 10\n    steps:\n      - uses", "    steps:\n      - uses")),
    ("workflow-checkout", lambda r: edit(r, ".github/workflows/ci.yml", "        with:\n          persist-credentials: false\n      - uses: actions/setup-python", "      - uses: actions/setup-python")),
    ("workflow-checkout", lambda r: edit(r, ".github/workflows/ci.yml", f"      - uses: actions/checkout@{SHA} # v4.2.2\n        with:\n          persist-credentials: false", f"      - uses: actions/checkout@{SHA} # v4.2.2")),
    ("installer-help", drop_json_flag),
    ("installer-help", lambda r: edit(r, "bin/tool.py", "Exit codes", "Returns")),
    ("installer-help", lambda r: edit(r, "bin/tool.py", "Environment", "Variables")),
    ("installer-help", lambda r: edit(r, "bin/tool.py", "raise SystemExit(0)", "raise SystemExit(4)")),
    ("error-format", lambda r: write(r, "bin/a.sh", 'echo "ERROR: broken" >&2\n')),
    ("error-format", lambda r: write(r, "bin/a.py", 'raise SystemExit("broken thing")\n')),
    ("error-format", lambda r: write(r, "bin/a.py", 'raise SystemExit(f"{name} is broken")\n')),
    ("error-format", lambda r: write(r, "bin/a.py", 'import sys\nsys.exit("Error: broken")\n')),
    ("ascii-markdown", lambda r: edit(r, "README.md", "Run the tool.", "Run the tool \u2014 now.")),
    ("private-patterns", lambda r: write(r, "notes.txt", "see " + HOME_PATH + "\n")),
    ("private-patterns", lambda r: write(r, "notes.txt", "host " + PRIVATE_IP + " is down\n")),
    ("private-patterns", lambda r: write(r, "notes.txt", "contact someone" + AT + "corp.example.io\n")),
    ("private-patterns", lambda r: write(r, "notes.txt", "path " + MAC_PATH + "\n")),
    ("private-patterns", lambda r: write(r, "wide.txt", ("host " + PRIVATE_IP + "\n").encode("utf-16"))),
    ("vendor", lambda r: edit(r, ".github/stack/canon.json", '"canon_version": 1,', '"canon_version": 1,\n  ')),
    ("vendor", lambda r: (r / ".github/stack/SOURCE").unlink()),
    ("vendor", lambda r: edit(r, ".github/stack/SOURCE", f"commit: {SHA}", "commit: abc")),
]


@pytest.mark.parametrize("expected,mutate", FAILURES, ids=[f"{c}-{i}" for i, (c, _) in enumerate(FAILURES)])
def test_each_check_family_fails(repo: Path, expected: str, mutate) -> None:
    mutate(repo)
    code, data = run(repo)
    assert code == 1
    assert expected in hits(data), data["errors"]
    assert hits(data) <= {expected}, data["errors"]


@pytest.mark.parametrize(
    "rel,text",
    [
        ("bin/a.py", 'raise SystemExit("error: a: broke; rerun")\n'),
        ("bin/a.py", 'raise SystemExit(f"error: {x}: broke; rerun")\n'),
        ("bin/a.py", 'raise SystemExit("mods: error: broke; rerun")\n'),
        ("bin/a.py", "raise SystemExit(main())\n"),
        ("bin/a.py", "raise SystemExit(2)\n"),
        ("notes.txt", "mail iulian.dita@gmail.com or a@example.com or git@github.com:o/r\n"),
        ("notes.txt", "version 10.x and 1.10.3 and 172.15.0.1 are fine\n"),
    ],
)
def test_allowed_forms_pass(repo: Path, rel: str, text: str) -> None:
    write(repo, rel, text)
    code, data = run(repo)
    assert data["errors"] == [] and code == 0


def test_markdown_title_with_wordmark_below_passes(repo: Path) -> None:
    edit(repo, "README.md", README.splitlines()[0], MD_TITLE)
    code, data = run(repo)
    assert data["errors"] == [] and code == 0


def test_vendor_check_skipped_in_source_repo(repo: Path) -> None:
    (repo / ".github/stack/SOURCE").unlink()
    cfg = dict(REPO_JSON, source_of_truth=True)
    write(repo, ".github/stack/repo.json", json.dumps(cfg))
    assert run(repo)[0] == 0


def test_allowlist_suppresses_matching_finding(repo: Path) -> None:
    write(repo, "notes.txt", "see " + HOME_PATH + "\n")
    allow = {"check": "private-patterns", "path": "notes.txt", "match": "pattern home-path", "reason": "fixture"}
    write(repo, ".github/stack/repo.json", json.dumps(dict(REPO_JSON, allow=[allow])))
    code, data = run(repo)
    assert code == 0, data["errors"]


def test_stale_allowlist_entry_is_reported(repo: Path) -> None:
    allow = {"check": "private-patterns", "path": "gone.txt", "reason": "fixture"}
    write(repo, ".github/stack/repo.json", json.dumps(dict(REPO_JSON, allow=[allow])))
    code, data = run(repo)
    assert code == 1 and hits(data) == {"allowlist"}


def test_allowlist_entry_needs_a_reason(repo: Path) -> None:
    allow = {"check": "private-patterns", "path": "notes.txt"}
    write(repo, ".github/stack/repo.json", json.dumps(dict(REPO_JSON, allow=[allow])))
    code, data = run(repo)
    assert code == 2 and "reason" in data["errors"][0]


def test_ignored_files_are_not_scanned_in_a_git_checkout(repo: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    write(repo, ".gitignore", "ignored.md\n")
    write(repo, "ignored.md", "caf\u00e9\n")
    assert run(repo)[0] == 0
    write(repo, "tracked.md", "caf\u00e9\n")
    code, data = run(repo)
    assert code == 1 and hits(data) == {"ascii-markdown"}


def test_repo_ships_a_valid_source_of_truth_config() -> None:
    repo_json = json.loads((STACK / "repo.json").read_text(encoding="utf-8"))
    assert repo_json["repo"] == "agents" and repo_json["source_of_truth"] is True
    assert all(entry["reason"].strip() for entry in repo_json["allow"])
    assert [r["name"] for r in CANON["readme"]["stack_repos"]] == ["agents", "skills", "mods", "idstack"]


def test_this_repo_keeps_the_canonical_error_format() -> None:
    proc = subprocess.run(
        [sys.executable, str(STACK / "stack-check.py"), "--json", "--only", "error-format"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert json.loads(proc.stdout)["errors"] == []
    assert proc.returncode == 0

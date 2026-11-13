import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

OVERRIDE_PREFIXES = (
    "AGENTS_", "CLAUDE_", "CODEX_", "OPENCODE_", "COMMANDCODE_",
    "ANTIGRAVITY_", "OMP_", "PI_", "HERMES_",
)


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    for name in os.environ:
        if name.startswith(OVERRIDE_PREFIXES + ("GIT_CONFIG_", "GIT_AUTHOR_", "GIT_COMMITTER_")):
            monkeypatch.delenv(name)
    home = tmp_path / "isolated-home"
    home.mkdir()
    for name in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(name, str(home))
    for name in ("APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(home / name.lower()))
    config = tmp_path / "gitconfig"
    config.write_text("[core]\n\tautocrlf = false\n[commit]\n\tgpgsign = false\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    templates = tmp_path / "git-templates"
    templates.mkdir()
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(templates))


WINDOWS_POSIX_TESTS = {
    "test_render_prompts.py": {
        "test_sync_ai_prompts_check_mode_validates_render_shape",
        "test_sync_ai_prompts_dry_run_reports_manual_skips",
        "test_cli_deploy_requires_target",
        "test_backup_existing_flattens_windows_style_paths",
    },
    "test_render_agents.py": {"test_cli_agent_deploy_requires_target"},
    "test_render_invariants.py": {
        "test_antigravity_hook_emits_valid_preinvocation_json",
        "test_hook_is_executable_and_emits_invariants",
        "test_deploy_installs_hook_and_merges_settings",
        "test_deploy_merges_into_existing_settings_without_clobber",
        "test_channel_refresh_preserves_settings_and_backs_up_files",
    },
    "test_install_workflow.py": {"test_overwrite_preserves_private_backups"},
    "test_ci_config.py": {
        "test_release_notes_come_from_the_tagged_changelog_section",
        "test_release_notes_step_fails_without_a_section_for_the_tag",
        "test_release_notes_extract_from_the_real_changelog",
        "test_release_requires_successful_checks_for_the_tagged_commit",
    },
}


def pytest_collection_modifyitems(items):
    if os.name != "nt":
        return
    posix_only = pytest.mark.skip(reason="requires POSIX shell paths, filenames, or Unix permission bits")
    for item in items:
        name = item.originalname or item.name
        if item.path.name == "test_python_runtime.py" and "runtime" in item.fixturenames:
            item.add_marker(posix_only)
        elif name in WINDOWS_POSIX_TESTS.get(item.path.name, set()):
            item.add_marker(posix_only)
        elif (item.path.name == "test_render_hermes.py"
              and name == "test_environment_config_withholds_overlays_only_inside_work_tree"
              and item.callspec.params["override"] is None):
            item.add_marker(pytest.mark.skip(reason="fixture assumes the Unix ~/.hermes default; Windows uses LOCALAPPDATA"))

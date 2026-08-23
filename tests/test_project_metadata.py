from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_readme_leads_with_pypi_install_and_has_current_status() -> None:
    readme = (ROOT / "README.md").read_text()
    pypi_install = "python -m pip install reactorcheck"
    source_install = "python -m pip install -e ."
    assert pypi_install in readme
    assert source_install in readme
    assert readme.index(pypi_install) < readme.index(source_install)
    assert "publication is prepared but has not been performed" not in readme


def test_general_ci_targets_dgx_and_blocks_fork_pull_requests() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "runs-on: [self-hosted, dgx-spark]" in workflow
    assert "ubuntu-latest" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "PIP_NO_CACHE_DIR" in workflow
    assert "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09" in workflow
    assert "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1" in workflow
    assert 'machine in {"aarch64", "arm64"}' in workflow
    assert "/opt/catalysttwin-actions/shared-gui-runtime" in workflow
    assert "usr/lib/aarch64-linux-gnu" in workflow
    assert "usr/share/tcltk/tk8.6" in workflow
    assert "command -v Xvfb" in workflow
    assert "command -v xvfb-run" in workflow
    assert "python -c 'import tkinter" in workflow
    assert "sudo apt-get" not in workflow
    assert "xvfb-run" in workflow


def test_experimental_schema_is_valid_json_and_not_stable() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "reactorcheck-interchange.experimental.schema.json").read_text()
    )
    assert schema["properties"]["schema_version"]["const"] == "0.2-draft"
    assert "stability guarantee" in schema["description"]


def test_release_workflow_is_trusted_publishing_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "types: [published]" in workflow
    assert "if: github.event.release.prerelease == false" in workflow
    assert "RELEASE_TAG: ${{ github.event.release.tag_name }}" in workflow
    assert "GITHUB_REF_NAME" not in workflow
    assert "/tmp/reactorcheck-release-venv/bin/python -m pip check" in workflow
    assert "id-token: write" in workflow
    assert "name: pypi" in workflow
    assert "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33" in workflow
    assert "PYPI_API_TOKEN" not in workflow
    assert "secrets." not in workflow
    publish = workflow.split("  publish:\n", maxsplit=1)[1]
    assert publish.count("- uses:") == 2

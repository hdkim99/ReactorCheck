from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_experimental_schema_is_valid_json_and_not_stable() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "reactorcheck-interchange.experimental.schema.json").read_text()
    )
    assert schema["properties"]["schema_version"]["const"] == "0.2-draft"
    assert "stability guarantee" in schema["description"]


def test_release_workflow_is_trusted_publishing_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "types: [published]" in workflow
    assert "GITHUB_REF_NAME" in workflow
    assert "id-token: write" in workflow
    assert "name: pypi" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "PYPI_API_TOKEN" not in workflow
    assert "secrets." not in workflow
    publish = workflow.split("  publish:\n", maxsplit=1)[1]
    assert publish.count("- uses:") == 2

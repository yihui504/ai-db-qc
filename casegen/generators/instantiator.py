"""Template loader and instantiator for test case generation."""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List

from schemas.case import TestCase
from schemas.common import OperationType, InputValidity


def load_templates(path: str | Path) -> List[Dict[str, Any]]:
    """Load templates from YAML file."""
    data = yaml.safe_load(Path(path).read_text())
    return data.get("templates", [])


def _substitute_placeholders(value: Any, substitutions: Dict[str, Any]) -> Any:
    """Recursively substitute placeholders in value."""
    if isinstance(value, str):
        for key, val in substitutions.items():
            placeholder = f"{{{key}}}"
            if placeholder in value:
                value = value.replace(placeholder, str(val))
        return value
    elif isinstance(value, list):
        return [_substitute_placeholders(v, substitutions) for v in value]
    elif isinstance(value, dict):
        return {k: _substitute_placeholders(v, substitutions) for k, v in value.items()}
    else:
        return value


def instantiate_template(template: Dict[str, Any], substitutions: Dict[str, Any]) -> TestCase:
    """Instantiate a single template with substitutions."""
    # Substitute placeholders in param_template
    params = _substitute_placeholders(
        template.get("param_template", {}),
        substitutions
    )

    # Parse operation type
    op_str = template.get("operation", "")
    try:
        operation = OperationType(op_str)
    except ValueError:
        operation = OperationType.SEARCH  # fallback

    # Parse expected_validity
    validity_str = template.get("expected_validity", "legal")
    expected_validity = InputValidity(validity_str)

    # Get required_preconditions
    required_preconditions = template.get("required_preconditions", [])
    if isinstance(required_preconditions, str):
        required_preconditions = [required_preconditions]

    # Get oracle_refs
    oracle_refs = template.get("oracle_refs", [])
    if isinstance(oracle_refs, str):
        oracle_refs = [oracle_refs]

    return TestCase(
        case_id=template.get("template_id", "unknown"),
        operation=operation,
        params=params,
        expected_validity=expected_validity,
        required_preconditions=required_preconditions,
        oracle_refs=oracle_refs,
        rationale=template.get("rationale", "")
    )


def instantiate_all(
    templates: List[Dict[str, Any]],
    substitutions: Dict[str, Any]
) -> List[TestCase]:
    """Instantiate all templates with substitutions."""
    cases = []
    for tmpl in templates:
        case = instantiate_template(tmpl, substitutions)
        cases.append(case)
    return cases

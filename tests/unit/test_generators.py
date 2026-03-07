"""Unit tests for case generators."""

import pytest
from casegen.generators.instantiator import (
    load_templates,
    instantiate_template,
    instantiate_all,
    _substitute_placeholders
)
from schemas.common import OperationType, InputValidity


def test_load_templates():
    """Test loading templates from YAML."""
    templates = load_templates("casegen/templates/basic_templates.yaml")
    assert len(templates) == 10


def test_substitute_placeholders():
    """Test placeholder substitution."""
    result = _substitute_placeholders("{collection}_{k}", {"collection": "test", "k": 10})
    assert result == "test_10"


def test_substitute_in_dict():
    """Test substitution in nested dict."""
    template = {"top_k": "{k}", "collection": "{collection}"}
    result = _substitute_placeholders(template, {"k": 10, "collection": "test"})
    # Substitution returns strings, this is expected behavior
    assert result["top_k"] == "10"
    assert result["collection"] == "test"


def test_instantiate_template():
    """Test instantiating a single template."""
    template = {
        "template_id": "test-001",
        "operation": "search",
        "param_template": {"top_k": "{k}"},
        "expected_validity": "legal",
        "required_preconditions": ["collection_exists"],
        "oracle_refs": [],
        "rationale": "Test"
    }

    case = instantiate_template(template, {"k": 10})

    assert case.case_id == "test-001"
    assert case.operation == OperationType.SEARCH
    # Params can be strings after substitution - this is fine
    assert case.params["top_k"] == "10"
    assert case.expected_validity == InputValidity.LEGAL
    assert case.required_preconditions == ["collection_exists"]


def test_instantiate_all():
    """Test instantiating all templates."""
    templates = load_templates("casegen/templates/basic_templates.yaml")
    cases = instantiate_all(templates, {"collection": "test", "k": 10})

    assert len(cases) == 10

    # Check that valid cases are marked correctly
    valid_cases = [c for c in cases if c.case_id.startswith("tmpl-valid")]
    assert len(valid_cases) == 3
    for case in valid_cases:
        assert case.expected_validity == InputValidity.LEGAL

    # Check that invalid cases are marked correctly
    invalid_cases = [c for c in cases if c.case_id.startswith("tmpl-invalid")]
    assert len(invalid_cases) == 4
    for case in invalid_cases:
        assert case.expected_validity == InputValidity.ILLEGAL


def test_pseudo_valid_cases_have_preconditions():
    """Test that pseudo-valid cases have preconditions."""
    templates = load_templates("casegen/templates/basic_templates.yaml")
    cases = instantiate_all(templates, {"collection": "test"})

    pseudo_cases = [c for c in cases if c.case_id.startswith("tmpl-pseudo")]
    assert len(pseudo_cases) == 3

    for case in pseudo_cases:
        assert len(case.required_preconditions) > 0, \
            f"Pseudo-valid case {case.case_id} should have preconditions"

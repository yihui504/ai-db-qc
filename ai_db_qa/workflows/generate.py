"""Generate case packs from templates/campaigns."""

from pathlib import Path
import json
import yaml

from casegen.generators.instantiator import load_templates, instantiate_all


def run_generate(args):
    """Execute generate workflow."""
    if args.campaign:
        config = _load_yaml(args.campaign)
        template_path = Path(config['template'])
        substitutions = config.get('substitutions', {})
        output_path = Path(config.get('output', args.output))
    else:
        template_path = args.template
        substitutions = _parse_substitutions(args.substitutions or '')
        output_path = args.output

    print(f"[Generate] Loading templates from {template_path}...")
    templates = load_templates(template_path)
    print(f"[Generate] Found {len(templates)} templates")

    print(f"[Generate] Instantiating cases...")
    cases = instantiate_all(templates, substitutions)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        # Use centralized serialization helper (avoids hand-maintaining field list)
        case_data = [_serialize_case(c) for c in cases]
        pack_meta = {
            "pack_meta": {
                "name": "Generated Case Pack",
                "version": "1.0",
                "description": f"From {template_path.name}",
                "author": "ai-db-qa",
            },
            "cases": case_data
        }
        json.dump(pack_meta, f, indent=2)

    print(f"[Generate] Generated {len(cases)} cases -> {output_path}")


def _load_yaml(path: Path) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def _parse_substitutions(subst_str: str) -> dict:
    if not subst_str:
        return {}
    result = {}
    for pair in subst_str.split(','):
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    return result


def _serialize_case(case) -> dict:
    """Centralized serialization helper for TestCase objects.

    Aligned with existing schemas.case.TestCase schema.
    If schema changes, update this single function.
    """
    return {
        "case_id": case.case_id,
        "operation": case.operation.value,
        "params": case.params,
        "expected_validity": case.expected_validity.value,
        "required_preconditions": case.required_preconditions,
        "oracle_refs": case.oracle_refs,
        "rationale": case.rationale
    }

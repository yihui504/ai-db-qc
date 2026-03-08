"""CLI argument parsers for each workflow."""

from pathlib import Path


def add_generate_parser(subparsers):
    """Add generate subcommand parser."""
    parser = subparsers.add_parser('generate', help='Generate case packs from templates/campaigns')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--campaign', type=Path, help='Campaign YAML file')
    input_group.add_argument('--template', type=Path, help='Template YAML file')
    parser.add_argument('--substitutions', type=str, help='Substitutions as key=value,key2=value2')
    parser.add_argument('--output', type=Path, default=Path('packs/generated_pack.json'))


def add_validate_parser(subparsers):
    """Add validate subcommand parser."""
    parser = subparsers.add_parser('validate', help='Validate a single database')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--campaign', type=Path, help='Campaign YAML file')
    input_group.add_argument('--db', choices=['milvus', 'seekdb'], help='Database type')
    parser.add_argument('--pack', type=Path, help='Case pack JSON file')
    parser.add_argument('--contract', type=Path, help='Contract/profile YAML')
    parser.add_argument('--host', type=str, help='Database host (overrides campaign)')
    parser.add_argument('--port', type=int, help='Database port (overrides campaign)')
    parser.add_argument('--output', type=Path, default=Path('results'), help='Output directory')


def add_compare_parser(subparsers):
    """Add compare subcommand parser."""
    parser = subparsers.add_parser('compare', help='Compare two databases')
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--campaign', type=Path, help='Campaign YAML file')
    input_group.add_argument('--databases', type=str, help='Comma-separated: milvus,seekdb')
    parser.add_argument('--pack', type=Path, help='Shared case pack JSON')
    parser.add_argument('--tag', type=str, help='Run identifier')
    parser.add_argument('--output', type=Path, default=Path('results'), help='Output directory')


def add_export_parser(subparsers):
    """Add export subcommand parser."""
    parser = subparsers.add_parser('export', help='Export results to reports')
    parser.add_argument('--input', type=str, required=True, help='Results directory')
    parser.add_argument('--type', required=True, choices=['issue-report', 'paper-cases', 'summary'])
    parser.add_argument('--output', type=Path, required=True, help='Output file')

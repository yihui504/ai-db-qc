"""AI Database QA Tool - Minimum Viable CLI

Four primary workflows:
1. generate - Create case packs from templates/campaigns
2. validate - Single-database validation
3. compare  - Cross-database differential comparison
4. export   - Result export to reports
"""

import argparse


def main():
    parser = argparse.ArgumentParser(
        description="AI Database QA Tool - Test databases, judge correctness, generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Start:
  ai-db-qa generate --campaign campaigns/generate_milvus.yaml
  ai-db-qa validate --campaign campaigns/milvus_validation.yaml
  ai-db-qa export --input results/run/ --type issue-report

Documentation: docs/plans/2026-03-08-cli-productization-design.md
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    from .cli_parsers import (
        add_generate_parser, add_validate_parser,
        add_compare_parser, add_export_parser
    )

    add_generate_parser(subparsers)
    add_validate_parser(subparsers)
    add_compare_parser(subparsers)
    add_export_parser(subparsers)

    args = parser.parse_args()

    # Workflows will be implemented in Blocks 2-5
    if args.command == 'generate':
        from .workflows.generate import run_generate
        run_generate(args)
    elif args.command == 'validate':
        from .workflows.validate import run_validate
        run_validate(args)
    elif args.command == 'compare':
        from .workflows.compare import run_compare
        run_compare(args)
    elif args.command == 'export':
        from .workflows.export import run_export
        run_export(args)


if __name__ == '__main__':
    main()

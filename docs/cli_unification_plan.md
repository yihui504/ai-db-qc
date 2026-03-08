# CLI Unification Implementation Plan

> **Goal**: Create single `ai-db-qa` CLI entry point wrapping existing components
> **Timeline**: Week 1
> **Approach**: Wrap existing scripts, don't rewrite core logic

---

## Product Requirements

### User-Facing Commands

```bash
# Generate test cases from template
ai-db-qa generate --template <file> --output <file>

# Run tests on single database
ai-db-qa run --adapter <name> --cases <file> --output <dir>

# Run differential comparison
ai-db-qa run --diff <db1>,<db2> --cases <file> --output <dir>

# Generate reports
ai-db-qa report --input <dir> --template <type> --output <dir>

# Survey database capabilities
ai-db-qa survey --adapter <name> --output <file>

# Show version info
ai-db-qa version
```

### Success Criteria

1. ✅ Can run end-to-end campaign with single CLI
2. ✅ Help command works for all subcommands
3. ✅ Error messages are user-friendly
4. ✅ Output formats are consistent
5. ✅ No breaking changes to existing components

---

## Implementation Plan

### Step 1: Create Package Structure

**File**: `ai_db_qa/__init__.py`

```python
"""AI Database QA Tool - Automated testing and correctness judgment."""

__version__ = "0.1.0"
```

**File**: `ai_db_qa/cli.py`

```python
"""Main CLI entry point."""

import click
from .commands import generate, run, report, survey, version

@click.group()
@click.version_option(version="0.1.0")
def main():
    """AI Database QA Tool - Test databases, judge correctness, generate reports."""
    pass

# Register subcommands
main.add_command(generate.cli)
main.add_command(run.cli)
main.add_command(report.cli)
main.add_command(survey.cli)
main.add_command(version.cli)

if __name__ == "__main__":
    main()
```

### Step 2: Implement Generate Command

**File**: `ai_db_qa/commands/generate.py`

```python
"""Generate test cases from templates."""

import click
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from casegen.generators.instantiator import load_templates, instantiate_all

@click.command()
@click.option('--template', '-t', required=True, help='Template YAML file')
@click.option('--output', '-o', required=True, help='Output JSON file')
@click.option('--overrides', '-O', multiple=True, help='Parameter overrides (key=value)')
def cli(template, output, overrides):
    """Generate test cases from template."""
    # Parse overrides
    override_dict = {}
    for ov in overrides:
        if '=' in ov:
            k, v = ov.split('=', 1)
            override_dict[k] = v

    # Load and instantiate
    templates = load_templates(template)
    cases = instantiate_all(templates, override_dict)

    # Write output
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump([c.__dict__ for c in cases], f, indent=2, default=str)

    click.echo(f"Generated {len(cases)} test cases → {output}")
```

### Step 3: Implement Run Command

**File**: `ai_db_qa/commands/run.py`

```python
"""Run test campaigns."""

import click
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile

@click.command()
@click.option('--adapter', '-a', help='Database adapter (milvus or seekdb)')
@click.option('--diff', '-d', help='Differential mode: comma-separated databases')
@click.option('--cases', '-c', required=True, help='Test cases JSON file')
@click.option('--output', '-o', required=True, help='Output directory')
@click.option('--run-tag', '-t', required=True, help='Run identifier')
def cli(adapter, diff, cases, output, run_tag):
    """Run test campaign on database(s)."""

    cases_path = Path(cases)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    if diff:
        # Differential campaign
        databases = [d.strip() for d in diff.split(',')]
        click.echo(f"Running differential campaign on: {', '.join(databases)}")
        # ... wrap run_differential_campaign.py logic
    else:
        # Single database campaign
        click.echo(f"Running campaign on: {adapter}")
        # ... wrap executor logic
```

### Step 4: Implement Report Command

**File**: `ai_db_qa/commands/report.py`

```python
"""Generate reports from results."""

import click
from pathlib import Path

@click.command()
@click.option('--input', '-i', required=True, help='Input results directory')
@click.option('--template', '-t', default='summary', type=click.Choice(['summary', 'bugs', 'differential', 'issues']))
@click.option('--output', '-o', required=True, help='Output directory/file')
def cli(input, template, output):
    """Generate reports from test results."""
    click.echo(f"Generating {template} report from {input}")
    # ... wrap analyze_differential_results.py logic
```

### Step 5: Implement Survey Command

**File**: `ai_db_qa/commands/survey.py`

```python
"""Survey database capabilities."""

import click
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

@click.command()
@click.option('--adapter', '-a', required=True, help='Database adapter')
@click.option('--endpoint', '-e', help='Connection endpoint')
@click.option('--output', '-o', required=True, help='Output JSON file')
def cli(adapter, endpoint, output, **kwargs):
    """Survey database capabilities."""
    click.echo(f"Surveying {adapter} capabilities...")
    # ... wrap get_runtime_snapshot() logic
```

### Step 6: Implement Version Command

**File**: `ai_db_qa/commands/version.py`

```python
"""Show version information."""

import click

@click.command()
def cli():
    """Show tool and database version information."""
    from .. import __version__
    click.echo(f"AI Database QA Tool v{__version__}")

    # Database versions if available
    try:
        from ..adapters.milvus_adapter import MilvusAdapter
        from ..adapters.seekdb_adapter import SeekDBAdapter
        click.echo("\nSupported databases:")
        click.echo("  - milvus")
        click.echo("  - seekdb")
    except:
        pass
```

---

## Testing Plan

### Test 1: Help Commands

```bash
# Main help
ai-db-qa --help

# Subcommand helps
ai-db-qa generate --help
ai-db-qa run --help
ai-db-qa report --help
ai-db-qa survey --help
```

### Test 2: End-to-End Campaign

```bash
# Using existing templates
ai-db-qa generate \
  -t casegen/templates/differential_v3_phase1.yaml \
  -o cases/v3_phase1.json

# Run campaign
ai-db-qa run \
  -a milvus \
  -c cases/v3_phase1.json \
  -o results/v3_phase1 \
  -t v3_phase1_test

# Generate report
ai-db-qa report \
  -i results/v3_phase1 \
  -t differential \
  -o reports/v3_phase1.md
```

### Test 3: Survey

```bash
ai-db-qa survey -a milvus -o surveys/milvus.json
```

---

## File Structure

```
ai_db_qa/
├── __init__.py             # Package init
├── __main__.py              # Entry point for python -m
├── cli.py                   # Main CLI group
└── commands/
    ├── __init__.py
    ├── generate.py          # generate command
    ├── run.py               # run command
    ├── report.py            # report command
    ├── survey.py            # survey command
    └── version.py           # version command
```

---

## Development Tasks

### Task 1: Setup Package (Day 1)
- [ ] Create ai_db_qa package directory
- [ ] Create __init__.py with version
- [ ] Create __main__.py for python -m execution
- [ ] Test: `python -m ai_db_qa --help`

### Task 2: Implement Generate (Day 1-2)
- [ ] Create commands/generate.py
- [ ] Wrap instantiator logic
- [ ] Add overrides parsing
- [ ] Test: `ai-db-qa generate -t template.yaml -o cases.json`

### Task 3: Implement Run (Day 2-3)
- [ ] Create commands/run.py
- [ ] Wrap executor logic for single DB
- [ ] Wrap run_differential_campaign.py for diff
- [ ] Test: End-to-end campaign

### Task 4: Implement Report (Day 3-4)
- [ ] Create commands/report.py
- [ ] Wrap analyze_differential_results.py
- [ ] Add template types (summary, bugs, differential, issues)
- [ ] Test: Generate all report types

### Task 5: Implement Survey (Day 4-5)
- [ ] Create commands/survey.py
- [ ] Wrap get_runtime_snapshot() logic
- [ ] Test: Survey Milvus and seekdb

### Task 6: Documentation (Day 5)
- [ ] Create README.md with examples
- [ ] Document each command
- [ ] Add quick start guide
- [ ] Test: User can run first campaign

---

## Success Verification

### End-to-End Test

```bash
# 1. Generate cases
ai-db-qa generate \
  -t casegen/templates/differential_v3_phase1.yaml \
  -o /tmp/v3_p1.json

# 2. Run campaign
ai-db-qa run \
  --diff milvus,seekdb \
  -c /tmp/v3_p1.json \
  -o /tmp/v3_results \
  -t test

# 3. Generate report
ai-db-qa report \
  -i /tmp/v3_results \
  -t differential \
  -o /tmp/v3_report.md

# 4. Verify output exists
ls -la /tmp/v3_report.md
```

### Exit Conditions

**Week 1 Complete When**:
- ✅ All 5 commands implemented
- ✅ End-to-end test passes
- ✅ Help text is clear
- ✅ Error messages are user-friendly
- ✅ README.md with quick start

---

## Week 1 Deliverables

1. **ai-db-qa Package**: Working CLI tool
2. **README.md**: User-facing documentation
3. **Quick Start Guide**: 5-minute tutorial
4. **End-to-End Demo**: v3 Phase 1 campaign via CLI

---

## Next Phase Preview (Week 2-4)

After CLI unification, focus on **template library expansion**:

1. **Template Audit**: What operations are covered?
2. **Gap Analysis**: What operations are missing?
3. **Systematic Expansion**: Add templates to reach 50 cases
4. **Validation**: Test all templates on real databases

This continues the product strategy: **systematic expansion of working components**.

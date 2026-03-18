"""Phase 5.3 Ablation Study Runner.

Automatically runs all four ablation variants and produces a comparison table
to quantify each component's contribution to bug-detection effectiveness.

Four variants:
  V1: Full system          (gate=ON,  oracle=ON,  triage=diagnostic)
  V2: No gate              (gate=OFF, oracle=ON,  triage=diagnostic)
  V3: No oracle            (gate=ON,  oracle=OFF, triage=diagnostic)
  V4: Naive triage         (gate=ON,  oracle=ON,  triage=naive)

Metrics per variant:
  - total_cases: test cases executed
  - bugs_found: triage results classified as bugs
  - precision: bugs_found / total_cases  (higher = less noise)
  - noise_rate: (total_cases - bugs_found) / total_cases
  - unique_bug_types: set of BugType values observed

Usage:
    python scripts/run_ablation_study.py
    python scripts/run_ablation_study.py --adapter mock --output-dir runs/ablation
    python scripts/run_ablation_study.py --adapter milvus --host localhost --port 19530
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────────────────────
# Variant definitions
# ─────────────────────────────────────────────────────────────

VARIANTS = [
    {
        "id": "V1",
        "name": "Full System",
        "description": "Gate=ON, Oracle=ON, Triage=Diagnostic (baseline)",
        "flags": [],
    },
    {
        "id": "V2",
        "name": "No Gate",
        "description": "Gate=OFF — all cases reach executor regardless of preconditions",
        "flags": ["--no-gate"],
    },
    {
        "id": "V3",
        "name": "No Oracle",
        "description": "Oracle=OFF — only structural triage, no behavioral checking",
        "flags": ["--no-oracle"],
    },
    {
        "id": "V4",
        "name": "Naive Triage",
        "description": "Triage=Naive — all illegal-fail classified as Type-2 without diagnostic check",
        "flags": ["--naive-triage"],
    },
]


# ─────────────────────────────────────────────────────────────
# Result parsing
# ─────────────────────────────────────────────────────────────

def _find_latest_run_dir(base_dir: Path, tag: str) -> Optional[Path]:
    """Find the most recently created run directory matching the tag."""
    candidates = list(base_dir.glob(f"phase5.3-{tag}-*"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _parse_run_results(run_dir: Path) -> Dict[str, Any]:
    """Parse run metadata and triage results from a run directory."""
    meta_file = run_dir / "run_metadata.json"
    triage_file = run_dir / "triage_results.json"

    meta: Dict[str, Any] = {}
    triage_data: List[Dict] = []

    if meta_file.exists():
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)

    if triage_file.exists():
        with open(triage_file, encoding="utf-8") as f:
            triage_data = json.load(f)

    # Count bug types
    bug_types: Dict[str, int] = {}
    for t in triage_data:
        if t:
            bt = t.get("final_type", "UNKNOWN")
            bug_types[bt] = bug_types.get(bt, 0) + 1

    total_cases = meta.get("case_count", 0)
    bugs_found = meta.get("bug_count", 0)

    return {
        "total_cases": total_cases,
        "bugs_found": bugs_found,
        "success_count": meta.get("success_count", 0),
        "failure_count": meta.get("failure_count", 0),
        "precision": bugs_found / total_cases if total_cases > 0 else 0.0,
        "noise_rate": (total_cases - bugs_found) / total_cases if total_cases > 0 else 0.0,
        "bug_types": bug_types,
        "adapter_actual": meta.get("adapter_actual", "unknown"),
        "adapter_fallback": meta.get("adapter_fallback", False),
        "run_dir": str(run_dir),
    }


# ─────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────

def _render_ablation_table(results: List[Dict[str, Any]]) -> str:
    """Render a Markdown comparison table from variant results."""
    lines = [
        "| Variant | Description | Total Cases | Bugs Found | Precision | Noise Rate | Bug Types |",
        "|---------|-------------|-------------|------------|-----------|------------|-----------|",
    ]
    for r in results:
        v = r["variant"]
        m = r["metrics"]
        bt_summary = ", ".join(f"{k}×{v}" for k, v in sorted(m["bug_types"].items())) or "—"
        fallback_note = " ⚠️fallback" if m.get("adapter_fallback") else ""
        lines.append(
            f"| **{v['id']}** {v['name']}{fallback_note} "
            f"| {v['description']} "
            f"| {m['total_cases']} "
            f"| {m['bugs_found']} "
            f"| {m['precision']:.1%} "
            f"| {m['noise_rate']:.1%} "
            f"| {bt_summary} |"
        )
    return "\n".join(lines)


def _component_delta(results: List[Dict[str, Any]]) -> List[str]:
    """Compute component contribution deltas vs V1 (full system)."""
    v1 = next((r for r in results if r["variant"]["id"] == "V1"), None)
    if not v1:
        return ["V1 (full system) result not found — cannot compute deltas."]

    v1_bugs = v1["metrics"]["bugs_found"]
    lines = [
        "**Component Contribution Analysis** (delta vs V1 full system):",
        "",
    ]
    for r in results:
        vid = r["variant"]["id"]
        if vid == "V1":
            continue
        delta = r["metrics"]["bugs_found"] - v1_bugs
        sign = "+" if delta >= 0 else ""
        name = r["variant"]["name"]
        lines.append(
            f"- **{name}** ({vid}): bugs={r['metrics']['bugs_found']} "
            f"(delta={sign}{delta} vs V1={v1_bugs})"
        )

    # Gate contribution: V1.bugs - V2.bugs (cases blocked by gate that produced bugs in V1)
    v2 = next((r for r in results if r["variant"]["id"] == "V2"), None)
    v3 = next((r for r in results if r["variant"]["id"] == "V3"), None)
    v4 = next((r for r in results if r["variant"]["id"] == "V4"), None)

    lines.append("")
    lines.append("**Interpretation:**")
    if v2:
        gate_contribution = v1_bugs - v2["metrics"]["bugs_found"]
        lines.append(
            f"- Gate contribution: {gate_contribution:+d} bugs "
            f"(V1 vs V2: gate filtering {'reduces' if gate_contribution > 0 else 'increases'} bug count, "
            f"suggesting gate {'correctly blocks false positives' if gate_contribution > 0 else 'may over-block'})"
        )
    if v3:
        oracle_contribution = v1_bugs - v3["metrics"]["bugs_found"]
        lines.append(
            f"- Oracle contribution: {oracle_contribution:+d} bugs "
            f"(V1 vs V3: oracle {'adds' if oracle_contribution > 0 else 'subtracts'} {abs(oracle_contribution)} bug detections)"
        )
    if v4:
        triage_contribution = v1_bugs - v4["metrics"]["bugs_found"]
        lines.append(
            f"- Triage refinement: {triage_contribution:+d} bugs "
            f"(V1 vs V4: diagnostic triage {'more precise' if triage_contribution > 0 else 'same'} than naive)"
        )
    return lines


def _generate_ablation_report(
    results: List[Dict[str, Any]],
    output_dir: Path,
    run_timestamp: str,
    adapter_name: str,
) -> Path:
    """Generate a Markdown ablation study report."""
    report_path = output_dir / f"ablation_report_{run_timestamp}.md"

    table_md = _render_ablation_table(results)
    delta_lines = _component_delta(results)

    lines = [
        "# Phase 5.3 Ablation Study Report",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Adapter**: {adapter_name}",
        f"**Run Timestamp**: {run_timestamp}",
        "",
        "## Objective",
        "",
        "Quantify the contribution of each framework component to bug-detection",
        "effectiveness by systematically disabling one component at a time.",
        "",
        "## Variant Definitions",
        "",
        "| ID | Name | Components Active |",
        "|----|------|-------------------|",
        "| V1 | Full System       | Gate ✓ + Oracle ✓ + Diagnostic Triage ✓ |",
        "| V2 | No Gate           | ~~Gate~~ + Oracle ✓ + Diagnostic Triage ✓ |",
        "| V3 | No Oracle         | Gate ✓ + ~~Oracle~~ + Diagnostic Triage ✓ |",
        "| V4 | Naive Triage      | Gate ✓ + Oracle ✓ + ~~Diagnostic Triage~~ |",
        "",
        "## Results Comparison",
        "",
        table_md,
        "",
        "## Component Contribution Analysis",
        "",
        *delta_lines,
        "",
        "## Run Details",
        "",
    ]

    for r in results:
        v = r["variant"]
        m = r["metrics"]
        lines += [
            f"### {v['id']}: {v['name']}",
            "",
            f"- **Flags**: `{' '.join(v['flags']) or 'none (full system)'}`",
            f"- **Run Dir**: `{m['run_dir']}`",
            f"- **Adapter**: {m['adapter_actual']}{' (fallback)' if m.get('adapter_fallback') else ''}",
            f"- **Cases**: {m['total_cases']} (success={m['success_count']}, failure={m['failure_count']})",
            f"- **Bugs**: {m['bugs_found']}",
            f"- **Bug Type Breakdown**: {json.dumps(m['bug_types'])}",
            "",
        ]

    report_content = "\n".join(lines)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_path


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run Phase 5.3 ablation study: four variants auto-batch execution"
    )
    parser.add_argument(
        "--adapter",
        default="milvus",
        choices=["mock", "milvus", "qdrant", "weaviate", "pgvector"],
        help="Adapter to use (default: milvus, falls back to mock if unavailable)",
    )
    parser.add_argument("--host", default="localhost", help="Milvus host")
    parser.add_argument("--port", type=int, default=19530, help="Milvus port")
    # ── New adapters (Layer I) ──
    parser.add_argument("--qdrant-url", default="http://localhost:6333",
                        help="Qdrant URL (default: http://localhost:6333)")
    parser.add_argument("--weaviate-host", default="localhost",
                        help="Weaviate host (default: localhost)")
    parser.add_argument("--weaviate-port", type=int, default=8080,
                        help="Weaviate HTTP port (default: 8080)")
    parser.add_argument("--pgvector-container", default="pgvector_container",
                        help="pgvector Docker container name (default: pgvector_container)")
    parser.add_argument("--pgvector-db", default="vectordb",
                        help="pgvector database name (default: vectordb)")
    parser.add_argument(
        "--output-dir",
        default="runs/ablation",
        help="Output directory for all variant runs (default: runs/ablation)",
    )
    parser.add_argument(
        "--templates",
        default="casegen/templates/test_phase5_comprehensive.yaml",
        help="Test template file(s) to use",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip execution; just re-parse existing run dirs and regenerate report",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    runner_script = Path(__file__).parent / "run_phase5_3_eval.py"

    print("=" * 65)
    print("  PHASE 5.3 ABLATION STUDY")
    print(f"  Timestamp : {run_timestamp}")
    print(f"  Adapter   : {args.adapter}")
    print(f"  Output    : {args.output_dir}")
    print("=" * 65)
    print()

    all_results = []

    for variant in VARIANTS:
        vid = variant["id"]
        print(f"--- Running variant {vid}: {variant['name']} ---")

        run_tag = f"ablation-{vid.lower()}-{run_timestamp}"

        if not args.report_only:
            cmd = [
                sys.executable,
                str(runner_script),
                "--adapter", args.adapter,
                "--host", args.host,
                "--port", str(args.port),
                "--run-tag", run_tag,
                "--output-dir", str(output_dir),
                "--templates", args.templates,
                # ── New adapters (Layer I) ──
                "--qdrant-url", args.qdrant_url,
                "--weaviate-host", args.weaviate_host,
                "--weaviate-port", str(args.weaviate_port),
                "--pgvector-container", args.pgvector_container,
                "--pgvector-db", args.pgvector_db,
            ] + variant["flags"]

            print(f"  Command: {' '.join(cmd[2:])}")
            proc = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                cwd=str(Path(__file__).parent.parent),
            )
            if proc.returncode != 0:
                print(f"  WARNING: Variant {vid} exited with code {proc.returncode}")
        else:
            print(f"  --report-only mode: skipping execution for {vid}")

        # Find & parse run dir
        run_dir = _find_latest_run_dir(output_dir, f"ablation-{vid.lower()}-{run_timestamp}")
        if run_dir is None:
            # Fallback: find any matching dir
            run_dir = _find_latest_run_dir(output_dir, f"ablation-{vid.lower()}")

        if run_dir:
            metrics = _parse_run_results(run_dir)
            print(
                f"  => bugs={metrics['bugs_found']}/{metrics['total_cases']} "
                f"precision={metrics['precision']:.1%} "
                f"adapter={metrics['adapter_actual']}"
            )
        else:
            print(f"  WARNING: No run dir found for {vid}")
            metrics = {
                "total_cases": 0, "bugs_found": 0, "success_count": 0, "failure_count": 0,
                "precision": 0.0, "noise_rate": 0.0, "bug_types": {},
                "adapter_actual": "not_run", "adapter_fallback": False, "run_dir": "N/A",
            }

        all_results.append({"variant": variant, "metrics": metrics})
        print()

    # Generate aggregated report
    print("Generating ablation report...")
    report_path = _generate_ablation_report(
        all_results, output_dir, run_timestamp, args.adapter
    )
    print(f"Report saved: {report_path}")
    print()

    # Save raw JSON summary
    summary_path = output_dir / f"ablation_summary_{run_timestamp}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_timestamp": run_timestamp,
                "adapter": args.adapter,
                "variants": [
                    {"variant": r["variant"], "metrics": {
                        k: v for k, v in r["metrics"].items() if k != "run_dir"
                    }}
                    for r in all_results
                ],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Summary JSON: {summary_path}")

    # Print final comparison table
    print()
    print("=" * 65)
    print("  ABLATION RESULTS SUMMARY")
    print("=" * 65)
    print()
    header = f"{'Variant':<8} {'Name':<18} {'Cases':>7} {'Bugs':>5} {'Precision':>10} {'Noise':>8}"
    print(header)
    print("-" * len(header))
    for r in all_results:
        v = r["variant"]
        m = r["metrics"]
        fb = " *" if m.get("adapter_fallback") else ""
        print(
            f"{v['id']:<8} {v['name']:<18} {m['total_cases']:>7} "
            f"{m['bugs_found']:>5} {m['precision']:>9.1%} {m['noise_rate']:>7.1%}{fb}"
        )
    print()
    print("* = adapter fallback (mock used instead of real DB)")
    print()
    print(f"Full report: {report_path}")


if __name__ == "__main__":
    main()

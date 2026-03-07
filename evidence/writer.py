"""Evidence writer for run-scoped artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from schemas.case import TestCase
from schemas.result import ExecutionResult
from schemas.triage import TriageResult


class EvidenceWriter:
    """Write evidence artifacts to run-scoped directory.

    Minimal JSON-based output for reproducibility and analysis.
    """

    def create_run_dir(self, run_id: str, base_path: str = "runs") -> Path:
        """Create run directory and return path."""
        run_dir = Path(base_path) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_all(
        self,
        run_dir: Path,
        run_metadata: Dict[str, Any],
        cases: List[TestCase],
        results: List[ExecutionResult],
        triage_results: List[TriageResult | None],
        fingerprint = None,
        runtime_snapshots = None
    ) -> None:
        """Write all evidence files."""
        self._write_run_metadata(run_dir, run_metadata)
        self._write_cases(run_dir, cases)
        self._write_execution_results(run_dir, results)
        self._write_triage_report(run_dir, triage_results)
        if fingerprint:
            self._write_fingerprint(run_dir, fingerprint)
        if runtime_snapshots:
            self._write_runtime_snapshots(run_dir, runtime_snapshots)

    def _write_run_metadata(self, run_dir: Path, metadata: Dict) -> None:
        """Write run_metadata.json."""
        with open(run_dir / "run_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def _write_cases(self, run_dir: Path, cases: List[TestCase]) -> None:
        """Write cases.jsonl."""
        with open(run_dir / "cases.jsonl", "w") as f:
            for c in cases:
                json.dump(c.model_dump(mode="json"), f)
                f.write("\n")

    def _write_execution_results(self, run_dir: Path, results: List) -> None:
        """Write execution_results.jsonl."""
        with open(run_dir / "execution_results.jsonl", "w") as f:
            for r in results:
                json.dump(r.model_dump(mode="json"), f)
                f.write("\n")

    def _write_triage_report(self, run_dir: Path, triage_results: List) -> None:
        """Write triage_report.json."""
        # Filter out None (not bugs)
        bugs = [t.model_dump(mode="json") for t in triage_results if t]
        with open(run_dir / "triage_report.json", "w") as f:
            json.dump(bugs, f, indent=2)

    def _write_fingerprint(self, run_dir: Path, fingerprint) -> None:
        """Write fingerprint.json."""
        with open(run_dir / "fingerprint.json", "w") as f:
            json.dump(fingerprint.model_dump(mode="json"), f, indent=2)

    def _write_runtime_snapshots(self, run_dir: Path, snapshots) -> None:
        """Write runtime_snapshots.jsonl."""
        with open(run_dir / "runtime_snapshots.jsonl", "w") as f:
            for snapshot in snapshots:
                json.dump(snapshot, f)
                f.write("\n")

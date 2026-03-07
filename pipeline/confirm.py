"""Confirm placeholder - stub for Phase 3."""

from __future__ import annotations

from schemas.triage import TriageResult


class ConfirmPlaceholder:
    """Placeholder for confirm logic (Phase 3).

    Phase 2 does not implement rerun verification.
    """

    def confirm(self, triage_result: TriageResult) -> TriageResult:
        """Placeholder confirm method.

        In Phase 3, this will:
        - Rerun the case
        - Check stability
        - Return confirmed status

        For now, returns input unchanged.
        """
        return triage_result

    def needs_confirmation(self, triage_result: TriageResult) -> bool:
        """Check if triage result needs confirmation."""
        return False  # Phase 2: no confirmation logic

"""Pipeline base class and envelope (spec Wave 5 §36).

Provides the common PipelineRun lifecycle: create → run → gate → finish.
Concrete pipelines (one-target-venue, venue-deep-profile, etc.) will
subclass PipelineBase in future batches.
"""

from __future__ import annotations

from ..enums import OutputLevel, PipelineRunStatus, QualityGateStatus
from ..quality import QualityGateResult
from ..schema import PipelineRun
from ..traces import OperationTrace, finish_trace, start_trace


class PipelineBase:
    """Abstract base for Kairoskopion pipelines."""

    pipeline_type: str = "base"

    def __init__(self) -> None:
        self.run = PipelineRun(pipeline_type=self.pipeline_type)
        self.trace = start_trace(
            f"pipeline_{self.pipeline_type}",
            pipeline_run_id=self.run.pipeline_run_id,
        )

    def mark_running(self) -> None:
        self.run.status = PipelineRunStatus.RUNNING.value

    def record_gate(self, gate: QualityGateResult) -> None:
        self.run.quality_gate_results.append(gate.to_dict())
        self.trace.quality_gate_status = gate.status

    def finish(self, *, output_level: OutputLevel = OutputLevel.PRELIMINARY) -> PipelineRun:
        self.run.status = PipelineRunStatus.COMPLETED.value
        self.run.output_level = output_level.value
        finish_trace(self.trace)
        self.run.finished_at = self.trace.ended_at
        return self.run

    def fail(self, error: str) -> PipelineRun:
        self.run.status = PipelineRunStatus.FAILED.value
        self.run.errors.append(error)
        finish_trace(self.trace)
        self.run.finished_at = self.trace.ended_at
        return self.run

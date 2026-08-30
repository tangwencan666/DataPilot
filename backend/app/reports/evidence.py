import json
from app.reports.schemas import ArtifactEvidence, ReportEvidence, StepEvidence


class ReportEvidenceBuilder:
    def __init__(self, settings, repo, profiles, charts, queries, analyses):
        self.s = settings
        self.repo = repo
        self.profiles = profiles
        self.charts = charts
        self.queries = queries
        self.analyses = analyses

    def build(self, dataset, run):
        steps = self.repo.steps(run.id)[: self.s.report_max_step_evidence]
        truncated = run.step_count > len(steps)
        evidence = []
        artifacts = []
        refs = []
        limitations = []
        for x in steps:
            out = x.output_summary_json or {}
            summary = str(out.get("summary", x.error_message or ""))[:1000]
            item = StepEvidence(
                step_id=x.step_id,
                tool=x.tool_name,
                purpose=x.purpose,
                status=x.status.value,
                was_repaired=x.repair_count > 0,
                attempt_count=x.attempt_count,
                result_summary=summary,
                row_count=int(out.get("row_count", 0)),
                warnings=list(out.get("warnings", []))[:10],
                artifact_type=x.artifact_type,
                artifact_id=x.artifact_id,
            )
            evidence.append(item)
            refs.append(f"step:{x.step_id}")
            if x.status.value in ("FAILED", "SKIPPED"):
                limitations.append(f"{x.step_id}: {x.error_message or x.status.value}")
            if x.artifact_id:
                ref = f"{x.artifact_type}:{x.artifact_id}"
                refs.append(ref)
                title = x.purpose
                summary = item.result_summary
                if x.artifact_type == "chart":
                    obj = self.charts.get(dataset.id, x.artifact_id)
                    if obj:
                        title = obj.title
                        summary = f"{obj.chart_type} chart with {obj.rendered_point_count} rendered points."
                artifacts.append(ArtifactEvidence(ref=ref, type=x.artifact_type, id=x.artifact_id, title=title, summary=summary))
        profile = self.profiles.get_by_dataset_id(dataset.id)
        p = {}
        if profile and profile.profile_json:
            p = {
                "quality_score": profile.quality_score,
                "issues": profile.profile_json.get("issues", [])[: self.s.report_max_profile_issues],
                "correlations": profile.profile_json.get("correlations", [])[: self.s.report_max_correlations],
            }
            refs.append("profile:quality")
            refs.extend(f"profile:correlation:{c['column_a']}:{c['column_b']}" for c in p["correlations"])
        ev = ReportEvidence(
            dataset_summary={"name": dataset.name, "row_count": dataset.row_count, "column_count": dataset.column_count},
            question=run.user_question,
            goal=run.goal,
            planner_summary=run.planner_summary,
            execution_summary={
                "steps": run.step_count,
                "completed": run.completed_step_count,
                "failed": sum(x.status.value == "FAILED" for x in steps),
                "skipped": sum(x.status.value == "SKIPPED" for x in steps),
                "repaired": sum(x.repair_count > 0 for x in steps),
            },
            step_evidence=evidence,
            profile_evidence=p,
            artifact_evidence=artifacts[: self.s.report_max_artifacts],
            final_synthesis=run.final_summary_json,
            limitations=limitations,
            evidence_refs=refs,
            evidence_truncated=truncated,
        )
        if len(json.dumps(ev.model_dump(mode="json"), ensure_ascii=False)) > self.s.report_max_evidence_chars:
            ev = ev.model_copy(update={"step_evidence": ev.step_evidence[:5], "evidence_truncated": True})
        return ev

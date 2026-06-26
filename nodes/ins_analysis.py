from pydantic import BaseModel, Field

from helper import NutritionState, ins_dataset


class INSAnalysisFinding(BaseModel):
    ins_code: str = Field(description="The INS code")
    additive_name: str = Field(description="Name of the additive")
    category: str = Field(description="Category/type of additive")
    safety_level: str = Field(description="'approved', 'restricted', 'controversial', or 'unknown'")
    health_impact: str = Field(description="Potential health impact description")
    approval_status: str = Field(description="Regions where this additive is approved")
    recommendation: str = Field(description="'safe', 'caution', 'avoid', or 'limited'")
    reason: str = Field(description="Detailed reasoning for the classification")


class INSAnalysisOutput(BaseModel):
    total_additives: int = Field(description="Total number of INS additives found")
    findings: list[INSAnalysisFinding] = Field(description="Findings for each INS additive")
    overall_safety_score: float = Field(description="Overall safety score from 0 to 5")
    safety_summary: str = Field(description="Summary of additive safety")
    recommendations: list[str] = Field(description="Recommendations based on additive analysis")


def _approval_status(additive) -> tuple[int, str]:
    approved_regions = []
    if additive.approvals.A:
        approved_regions.append("Australia/NZ")
    if additive.approvals.E:
        approved_regions.append("Europe")
    if additive.approvals.U:
        approved_regions.append("USA")

    status = ", ".join(approved_regions) if approved_regions else "Not approved in major regions"
    return len(approved_regions), status


def ins_analysis(state: NutritionState) -> dict:
    """Analyze INS additives by looking them up in the local dataset."""

    parsed = state["parsed_label"]
    ins_codes = parsed.get("ins_codes", [])

    if not ins_codes:
        return {
            "ins_analysis": {
                "total_additives": 0,
                "findings": [],
                "overall_safety_score": 5.0,
                "safety_summary": "No food additives found in this product.",
                "recommendations": ["This product appears to be additive-free."],
            }
        }

    findings = []
    total_approved = 0
    total_controversial = 0

    for code in ins_codes:
        additive = ins_dataset.lookup_by_code(code)
        if additive:
            approved_count, approval_status = _approval_status(additive)

            if approved_count == 3:
                safety_level = "approved"
                recommendation = "safe"
                total_approved += 1
            elif approved_count == 2:
                safety_level = "restricted"
                recommendation = "caution"
            elif approved_count == 1:
                safety_level = "controversial"
                recommendation = "limited"
                total_controversial += 1
            else:
                safety_level = "unknown"
                recommendation = "avoid"
                total_controversial += 1

            findings.append(
                INSAnalysisFinding(
                    ins_code=additive.ins_code,
                    additive_name=additive.name,
                    category=additive.type,
                    safety_level=safety_level,
                    health_impact=f"Categorized as {additive.type}. {additive.text}",
                    approval_status=approval_status,
                    recommendation=recommendation,
                    reason=(
                        f"{additive.name} is approved in {approved_count}/3 major regions "
                        f"({approval_status}). Classified as {safety_level}."
                    ),
                )
            )
        else:
            findings.append(
                INSAnalysisFinding(
                    ins_code=str(code),
                    additive_name=f"Unknown (INS {code})",
                    category="Unknown",
                    safety_level="unknown",
                    health_impact="Additive not found in database.",
                    approval_status="Unknown",
                    recommendation="caution",
                    reason=f"INS code {code} was not found in the additive database. Caution advised.",
                )
            )
            total_controversial += 1

    safety_score = max(0.0, min(5.0, 5.0 - (total_controversial * 0.5)))

    if safety_score >= 4.5:
        safety_summary = (
            f"This product contains {len(findings)} well-established food additives. "
            "Overall safety profile is excellent."
        )
    elif safety_score >= 4.0:
        safety_summary = (
            f"This product contains {len(findings)} food additives. "
            "Overall safety profile is good."
        )
    elif safety_score >= 3.0:
        safety_summary = (
            f"This product contains {len(findings)} additives, with "
            f"{total_controversial} limited or uncertain additive(s)."
        )
    elif safety_score >= 2.0:
        safety_summary = (
            f"This product contains {len(findings)} additives, with "
            f"{total_controversial} controversial or unapproved additive(s)."
        )
    else:
        safety_summary = (
            f"This product contains {len(findings)} additives with significant approval concerns."
        )

    recommendations = []
    if total_approved == len(findings):
        recommendations.append("All additives are universally approved.")
    if total_controversial > 0:
        recommendations.append(
            f"{total_controversial} additive(s) have limited approval; consider alternatives."
        )
    if len(findings) > 5:
        recommendations.append("This product contains many additives; consider simpler products.")
    recommendations.append(f"Overall Safety Score: {safety_score:.1f}/5")

    result = INSAnalysisOutput(
        total_additives=len(findings),
        findings=findings,
        overall_safety_score=safety_score,
        safety_summary=safety_summary,
        recommendations=recommendations,
    )

    return {"ins_analysis": result.model_dump()}

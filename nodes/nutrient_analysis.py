from pydantic import BaseModel, Field

from helper import NUTRIENT_SCALES, NutritionState, get_openrouter_llm, pydantic_to_dict


class NutrientAnalysis(BaseModel):
    nutrient: str
    value_per_100g: float | None
    value_per_serving: float | None
    unit: str
    scale_breakpoints: list[float]
    classification: str
    score: float
    explanation: str


class NutrientAnalysisOutput(BaseModel):
    nutrients: list[NutrientAnalysis] = Field(
        description=(
            "Analyses for each nutrient with values, units, scale breakpoints, "
            "classification, score, and explanation."
        )
    )


nutrient_analysis_structured = get_openrouter_llm("openai/gpt-oss-20b:free").with_structured_output(NutrientAnalysisOutput)


POSITIVE_NUTRIENTS = {"protein", "fiber"}
NUTRIENT_SCALE_KEYS = {
    "protein": "protein",
    "dietary_fiber": "fiber",
    "fiber": "fiber",
    "total_sugars": "sugar",
    "added_sugars": "sugar",
    "sugar": "sugar",
    "sodium": "sodium",
    "saturated_fat": "saturated_fat",
}


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)

    import re

    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def _score_from_scale(nutrient: str, value: float, scale: list[float]) -> tuple[float, str]:
    thresholds = scale[1:-1]
    bucket = sum(value > threshold for threshold in thresholds)

    if nutrient in POSITIVE_NUTRIENTS:
        score = min(5.0, float(bucket + 1))
        labels = ["very low", "low", "moderate", "good", "excellent"]
    else:
        score = max(1.0, float(5 - bucket))
        labels = ["excellent", "good", "moderate", "high", "very high"]

    return score, labels[bucket]


def _fallback_nutrient_analysis(nutrition_table: dict) -> list[dict]:
    analyses = []

    for nutrient, row in nutrition_table.items():
        if not isinstance(row, dict):
            row = {"per_100g": row, "unit": ""}

        value_per_100g = _float_or_none(row.get("per_100g"))
        value_per_serving = _float_or_none(row.get("per_serving"))
        unit = str(row.get("unit", ""))
        scale_key = NUTRIENT_SCALE_KEYS.get(nutrient)
        scale = NUTRIENT_SCALES.get(scale_key, []) if scale_key else []

        if value_per_100g is None:
            classification = "unknown"
            score = 0.0
            explanation = f"{nutrient} is missing or could not be parsed from the label."
        elif scale:
            score, classification = _score_from_scale(scale_key, value_per_100g, scale)
            explanation = (
                f"{nutrient} has {value_per_100g:g}{unit} per 100g, "
                f"classified as {classification} using the {scale_key} scale."
            )
        else:
            classification = "not evaluated"
            score = 0.0
            explanation = f"No predefined scale is configured for {nutrient}."

        analyses.append(
            {
                "nutrient": nutrient,
                "value_per_100g": value_per_100g,
                "value_per_serving": value_per_serving,
                "unit": unit,
                "scale_breakpoints": scale,
                "classification": classification,
                "score": score,
                "explanation": explanation,
            }
        )

    return analyses


def nutrient_analysis(state: NutritionState) -> dict:
    """Analyze nutrition values against predefined nutrient scales."""

    parsed = state["parsed_label"]
    nutrition_table = parsed["nutrition_table"]
    serving_info = parsed["serving_info"]

    messages = [
        {
            "role": "system",
            "content": (
                "You are a nutrition scientist. Classify nutrients according to "
                "the provided scales and explain each classification."
            ),
        },
        {
            "role": "user",
            "content": f"""
Here is the nutrition table:

{nutrition_table}

Here is the serving information:

{serving_info}

Classify the nutritional content using these scales:

{NUTRIENT_SCALES}

For each nutrient:
- Identify the nutrient name.
- Determine a score from 0 to 5.
- Explain the classification using the specific values from the table.
- Do not invent missing values.
- If a nutrient is missing, classify it as "unknown".
- If a nutrient has no predefined scale, classify it as "not evaluated".
""",
        },
    ]

    try:
        result = nutrient_analysis_structured.invoke(messages)
        analysis = result.get("nutrients", result) if isinstance(result, dict) else result.nutrients
    except Exception:
        analysis = _fallback_nutrient_analysis(nutrition_table)

    return {"nutrient_analysis": pydantic_to_dict(analysis)}

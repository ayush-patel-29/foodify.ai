from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field

from helper import NutritionState, get_openrouter_llm, pydantic_to_dict


class ProcessingIndicator(BaseModel):
    ingredient: str = Field(description="The ingredient being analyzed")
    reason: str = Field(description="Why this ingredient has this processing level")
    impact: str = Field(description="positive, negative, or neutral health impact")


class NOVAAnalysis(BaseModel):
    nova_group: int = Field(description="1-4")
    classification: str = Field(
        description=(
            "Unprocessed, Processed Culinary Ingredient, Processed Food, "
            "or Ultra Processed Food"
        )
    )
    processing_score: float = Field(description="0-5")
    indicators: list[ProcessingIndicator]
    summary: str


nova_analysis_llm = get_openrouter_llm("openai/gpt-oss-20b:free").with_structured_output(NOVAAnalysis)


def analyze_single_nova(ingredient: str) -> tuple[str, dict]:
    """Analyze NOVA processing level for one ingredient."""

    messages = [
        {
            "role": "system",
            "content": (
                "Classify ingredient NOVA group: 1=unprocessed, 2=culinary ingredient, "
                "3=processed, 4=ultra-processed. Return group, classification, score, "
                "indicators, and summary."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Classify {ingredient}. Group 1-4. Score 0-5. "
                "List 2-3 indicators with reason and health impact."
            ),
        },
    ]

    try:
        result = nova_analysis_llm.invoke(messages)
        return ingredient, pydantic_to_dict(result)
    except Exception as exc:
        return ingredient, {
            "error": str(exc),
            "nova_group": 3,
            "classification": "Unknown",
            "processing_score": 3.0,
            "indicators": [],
            "summary": "Analysis failed.",
        }


def nova_analysis(state: NutritionState) -> dict:
    """Classify ingredients according to the NOVA processing system."""

    parsed = state["parsed_label"]
    ingredients = parsed.get("ingredients", [])
    if not ingredients:
        return {"processing_analysis": {}}

    all_analyses = {}
    with ThreadPoolExecutor(max_workers=min(4, len(ingredients))) as executor:
        futures = {executor.submit(analyze_single_nova, ingredient): ingredient for ingredient in ingredients}
        for future in as_completed(futures):
            ingredient, result = future.result()
            all_analyses[ingredient] = result

    return {"processing_analysis": all_analyses}

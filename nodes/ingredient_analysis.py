from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field

from helper import NutritionState, get_openrouter_llm, pydantic_to_dict


class IngredientFinding(BaseModel):
    ingredient: str
    category: str
    impact: str
    reason: str


class IngredientAnalysis(BaseModel):
    ingredient_quality_score: float = Field(
        description="Overall ingredient quality score from 0 to 5."
    )
    positives: list[IngredientFinding] = Field(description="Positive ingredient findings.")
    negatives: list[IngredientFinding] = Field(description="Negative ingredient findings.")
    concerns: list[IngredientFinding] = Field(description="Ingredient concerns.")
    processing_indicator: str = Field(
        description="'unprocessed', 'minimally processed', 'processed', or 'ultra-processed'."
    )
    summary: str = Field(description="Concise ingredient quality summary.")


ingredient_analysis_structured = get_openrouter_llm("openai/gpt-oss-20b:free").with_structured_output(IngredientAnalysis)


def analyze_single_ingredient(ingredient: str) -> tuple[str, dict]:
    """Analyze a single ingredient for parallel execution."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are an ingredient expert evaluating ingredient quality. "
                "Return score, positives, negatives, concerns, processing level, and summary."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Analyze: {ingredient}. Rate 0-5 where 5 is an excellent whole food "
                "and 0 is harmful. Include positives, negatives, concerns, and processing level."
            ),
        },
    ]

    try:
        result = ingredient_analysis_structured.invoke(messages)
        return ingredient, pydantic_to_dict(result)
    except Exception as exc:
        return ingredient, {"error": str(exc)}


def ingredient_analysis(state: NutritionState) -> dict:
    """Evaluate the quality of all ingredients in the product."""

    parsed = state["parsed_label"]
    ingredients = parsed.get("ingredients", [])
    if not ingredients:
        return {"ingredient_analysis": {}}

    all_analyses = {}
    with ThreadPoolExecutor(max_workers=min(4, len(ingredients))) as executor:
        futures = {executor.submit(analyze_single_ingredient, ingredient): ingredient for ingredient in ingredients}
        for future in as_completed(futures):
            ingredient, result = future.result()
            all_analyses[ingredient] = result

    return {"ingredient_analysis": all_analyses}

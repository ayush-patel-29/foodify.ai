import json

from pydantic import BaseModel, Field

from helper import NutritionState, get_openrouter_llm, pydantic_to_dict


class AllergenFinding(BaseModel):
    allergen: str = Field(description="Standard allergen name")
    source: str = Field(description="Ingredient that triggered detection")
    severity: str = Field(description="low, moderate, high")
    detected: bool = True


class AllergenAnalysis(BaseModel):
    allergens_detected: list[AllergenFinding]
    allergen_free_claims: list[str] = Field(description="Allergens not detected")
    summary: str


allergen_llm = get_openrouter_llm("openai/gpt-oss-20b:free")
allergen_analysis_llm = allergen_llm.with_structured_output(AllergenAnalysis)


def allergen_analysis(state: NutritionState) -> dict:
    """Detect common allergens from the ingredient list."""

    parsed = state["parsed_label"]
    ingredients = parsed.get("ingredients", [])

    messages = [
        {
            "role": "system",
            "content": (
                "You are an allergen expert. Detect common allergens and assess severity. "
                "Return allergens_detected, allergen_free_claims, and summary."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Analyze these ingredients for potential allergens: {ingredients}\n\n"
                "Common allergens: Milk, Eggs, Fish, Shellfish, Tree Nuts, Peanuts, "
                "Wheat, Soy, Sesame."
            ),
        },
    ]

    try:
        result = allergen_analysis_llm.invoke(messages)
        analysis = pydantic_to_dict(result)
    except Exception:
        result = allergen_llm.invoke(messages)
        response_text = result.content if hasattr(result, "content") else str(result)
        try:
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            analysis = {
                "allergens_detected": [],
                "allergen_free_claims": ["Unable to parse allergens"],
                "summary": response_text[:200],
            }

    return {"allergen_analysis": analysis}

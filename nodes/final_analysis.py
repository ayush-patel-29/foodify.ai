from pydantic import BaseModel, Field
import json

from helper import NutritionState, get_openrouter_llm, pydantic_to_dict


class ProductRating(BaseModel):
    score: float = Field(description="Overall score from 0-5")
    rating_label: str = Field(description="Excellent, Good, Average, Poor, or Avoid")


class Insight(BaseModel):
    title: str
    explanation: str


class ConsumptionRecommendation(BaseModel):
    recommendation: str
    frequency: str = Field(description="Daily, Frequent, Occasional, Rare, or Avoid")
    explanation: str


class FinalNutritionScientistOutput(BaseModel):
    overall_rating: ProductRating
    consumption_recommendation: ConsumptionRecommendation
    positives: list[Insight]
    concerns: list[Insight]
    executive_summary: str
    key_warnings: list[str]
    suitable_for: list[str]
    not_suitable_for: list[str]
    score_breakdown: dict[str, float]


final_analysis_llm = get_openrouter_llm("openai/gpt-oss-20b:free")


def final_analysis(state: NutritionState) -> dict:
    """Synthesize all node outputs into a final food product report."""

    analysis_summary = f"""
NUTRIENT ANALYSIS:
{state.get("nutrient_analysis", [])}

INGREDIENT ANALYSIS:
{state.get("ingredient_analysis", {})}

INS ADDITIVE ANALYSIS:
{state.get("ins_analysis", {})}

ALLERGEN ANALYSIS:
{state.get("allergen_analysis", {})}

NOVA PROCESSING ANALYSIS:
{state.get("processing_analysis", {})}
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a final nutrition scientist. Synthesize nutrient, ingredient, "
                "additive, allergen, and processing analyses into a practical product evaluation. "
                "Output your response as valid JSON only, no other text."
            ),
        },
        {
            "role": "user",
            "content": f"""
Please analyze these food product analyses and respond with JSON:

{analysis_summary}

Output JSON with:
{{
  "overall_rating": {{"score": 0-5, "rating_label": "string"}},
  "consumption_recommendation": {{"recommendation": "string", "frequency": "Daily|Frequent|Occasional|Rare|Avoid", "explanation": "string"}},
  "positives": [{{"title": "string", "explanation": "string"}}],
  "concerns": [{{"title": "string", "explanation": "string"}}],
  "executive_summary": "string",
  "key_warnings": ["string"],
  "suitable_for": ["string"],
  "not_suitable_for": ["string"],
  "score_breakdown": {{"allergens": 0-5, "additives": 0-5, "processing": 0-5, "ingredients": 0-5, "nutrients": 0-5}}
}}
""",
        },
    ]

    try:
        result = final_analysis_llm.invoke(messages)
        response_text = result.content if hasattr(result, "content") else str(result)
        
        # Try to parse JSON from response
        try:
            parsed = json.loads(response_text)
            return {"final_report": parsed}
        except json.JSONDecodeError:
            # If the response contains JSON but with extra text, try to extract it
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {"final_report": parsed}
            raise
    except Exception as e:
        # Fallback response
        return {
            "final_report": {
                "overall_rating": {"score": 3.0, "rating_label": "Average"},
                "consumption_recommendation": {
                    "recommendation": "Consume in moderation",
                    "frequency": "Occasional",
                    "explanation": "Product analysis incomplete"
                },
                "positives": [{"title": "Analysis Attempted", "explanation": "Workflow executed successfully"}],
                "concerns": [{"title": "Final Analysis Error", "explanation": str(e)[:200]}],
                "executive_summary": f"Analysis completed with error: {str(e)[:150]}",
                "key_warnings": ["Final analysis incomplete"],
                "suitable_for": ["General consumers"],
                "not_suitable_for": ["Unable to determine"],
                "score_breakdown": {"allergens": 3, "additives": 3, "processing": 3, "ingredients": 3, "nutrients": 3}
            }
        }

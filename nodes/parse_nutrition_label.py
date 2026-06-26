from pydantic import BaseModel, Field
import json

from helper import EvaluationInput, NutritionState, get_openrouter_llm, pydantic_to_dict


class NutritionParser(BaseModel):
    parsed_label: EvaluationInput = Field(
        description=(
            "Structured representation of the nutrition label, including the "
            "nutrition table, serving information, ingredients, and INS codes."
        )
    )


structured_parser_llm = get_openrouter_llm("openai/gpt-oss-20b:free")


def parse_nutrition_label(state: NutritionState) -> dict:
    """Parse raw OCR text into structured nutrition label data."""

    raw_text = state["raw_ocr_text"]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a nutrition label parser. Extract and return ONLY valid JSON (no extra text). "
                "Return JSON with: {\"parsed_label\": {\"nutrition_table\": {...}, \"serving_info\": {...}, "
                "\"ingredients\": [...], \"ins_codes\": [...]}}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Parse this nutrition label and return ONLY JSON:\n\n{raw_text}\n\n"
                "Extract nutrition_table, serving_info, ingredients list, and ins_codes list. "
                "Return valid JSON only."
            ),
        },
    ]

    try:
        result = structured_parser_llm.invoke(messages)
        response_text = result.content if hasattr(result, "content") else str(result)
        
        # Try to parse JSON from response
        try:
            data = json.loads(response_text)
            parsed_label = data.get("parsed_label", data)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                parsed_label = data.get("parsed_label", data)
            else:
                raise ValueError(f"Could not parse JSON from: {response_text[:200]}")
        
        # Ensure all required fields exist
        return {
            "parsed_label": {
                "nutrition_table": parsed_label.get("nutrition_table", {}),
                "serving_info": parsed_label.get("serving_info", {}),
                "ingredients": parsed_label.get("ingredients", []),
                "ins_codes": parsed_label.get("ins_codes", []),
            }
        }
    except Exception as e:
        # Fallback: return minimal valid structure
        return {
            "parsed_label": {
                "nutrition_table": {},
                "serving_info": {},
                "ingredients": [],
                "ins_codes": [],
            }
        }

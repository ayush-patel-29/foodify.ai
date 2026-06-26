from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NotRequired, Optional, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()


DEFAULT_MODEL = "openai/gpt-oss-20b:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
FALLBACK_MODEL = "google/gemma-4-31B-it:fastest"
FALLBACK_BASE_URL = "https://router.huggingface.co/v1"
LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = 1

DATASET_DIR = Path(__file__).resolve().parent / "dataset"

NUTRIENT_SCALES = {
    "protein": [0, 3, 6, 12, 20, 75],
    "fiber": [0, 1.5, 3, 6, 9, 30],
    "sugar": [0, 2.5, 5, 10, 15, 50],
    "sodium": [0, 120, 300, 600, 1200, 3000],
    "saturated_fat": [0, 1.5, 3, 5, 10, 25],
}


class NutrientRow(TypedDict):
    per_100g: NotRequired[float]
    per_serving: NotRequired[float]
    unit: str


class NutritionTable(TypedDict):
    energy: NotRequired[NutrientRow]
    protein: NotRequired[NutrientRow]
    carbohydrates: NotRequired[NutrientRow]
    total_sugars: NotRequired[NutrientRow]
    added_sugars: NotRequired[NutrientRow]
    dietary_fiber: NotRequired[NutrientRow]
    total_fat: NotRequired[NutrientRow]
    saturated_fat: NotRequired[NutrientRow]
    trans_fat: NotRequired[NutrientRow]
    sodium: NotRequired[NutrientRow]


class ServingInfo(TypedDict):
    serving_size: NotRequired[float]
    serving_unit: NotRequired[str]


class EvaluationInput(TypedDict):
    nutrition_table: NutritionTable
    serving_info: ServingInfo
    ingredients: list[str]
    ins_codes: list[str]


class NutritionState(TypedDict):
    raw_ocr_text: str
    image_path: NotRequired[str]
    parsed_label: EvaluationInput | None
    nutrient_analysis: dict | list | None
    ingredient_analysis: dict | None
    ins_analysis: dict | None
    allergen_analysis: dict | None
    processing_analysis: dict | None
    final_report: dict | str | None


class INSApprovals(BaseModel):
    """Food additive approval status by region."""

    A: bool = Field(description="Approved in Australia/NZ")
    E: bool = Field(description="Approved in Europe")
    U: bool = Field(description="Approved in United States")


class INSAdditive(BaseModel):
    """Complete INS additive information from dataset."""

    id: str = Field(description="Unique identifier, e.g. INS-650")
    ins_code: str = Field(description="INS code, e.g. 650")
    name: str = Field(description="Name of the food additive")
    type: str = Field(description="Type/category of additive")
    approvals: INSApprovals = Field(description="Approval status by region")
    text: str = Field(description="Full text description of the additive")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_openrouter_llm(model: str = DEFAULT_MODEL) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=DEFAULT_BASE_URL,
        api_key=_required_env("OPENROUTER_API_KEY"),
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def get_huggingface_llm(model: str = FALLBACK_MODEL) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=FALLBACK_BASE_URL,
        api_key=_required_env("HF_API_KEY"),
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def json_output_instruction(model_class: type[BaseModel]) -> str:
    schema = model_class.model_json_schema()
    return f"\nOutput Format: {json.dumps(schema, indent=2)}"


def pydantic_to_dict(value):
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [pydantic_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: pydantic_to_dict(item) for key, item in value.items()}
    return value


def normalize_ins_code(ins_code: str) -> str:
    code = str(ins_code).strip().lower()
    code = code.replace("ins", "").replace("-", "").strip()
    return code


class INSDataset:
    """Loads and searches INS additive data from the dataset directory."""

    def __init__(self, dataset_dir: str | Path = DATASET_DIR):
        self.dataset_dir = Path(dataset_dir)
        self.additives: dict[str, INSAdditive] = {}
        self.synonyms: dict[str, str] = {}
        self.load_data()

    def load_data(self) -> None:
        jsonl_path = self.dataset_dir / "INS_agent_dataset.jsonl"
        if jsonl_path.exists():
            with jsonl_path.open("r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        data = json.loads(line)
                        additive = INSAdditive(**data)
                        self.additives[normalize_ins_code(additive.ins_code)] = additive

        synonyms_path = self.dataset_dir / "INS_synonyms.json"
        if synonyms_path.exists():
            with synonyms_path.open("r", encoding="utf-8") as file:
                self.synonyms = json.load(file)

    def lookup_by_code(self, ins_code: str) -> Optional[INSAdditive]:
        return self.additives.get(normalize_ins_code(ins_code))

    def lookup_by_name(self, name: str) -> Optional[INSAdditive]:
        name_lower = name.lower().strip()

        if name_lower in self.synonyms:
            return self.lookup_by_code(self.synonyms[name_lower])

        for additive in self.additives.values():
            if additive.name.lower() == name_lower:
                return additive

        return None

    def search(self, query: str) -> list[INSAdditive]:
        results = []
        query_lower = query.lower().strip()

        direct = self.lookup_by_code(query) or self.lookup_by_name(query)
        if direct:
            results.append(direct)

        for additive in self.additives.values():
            if query_lower in additive.name.lower() or query_lower in additive.type.lower():
                if additive not in results:
                    results.append(additive)

        return results[:10]


ins_dataset = INSDataset()


def lookup_food_additive(query: str) -> dict:
    """Lookup food additive by INS code or additive name."""

    results = ins_dataset.search(query)
    if not results:
        return {
            "found": False,
            "query": query,
            "message": "No additive found matching the query",
        }

    return {
        "found": True,
        "query": query,
        "results": [additive.model_dump() for additive in results],
        "count": len(results),
    }

from __future__ import annotations

import argparse
import json
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from helper import NutritionState
from nodes import (
    allergen_analysis,
    extract_text_from_image,
    final_analysis,
    ingredient_analysis,
    ins_analysis,
    nova_analysis,
    nutrient_analysis,
    parse_nutrition_label,
)


IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}

SAMPLE_OCR_TEXT = (
    "IngredientsPotato (88%), edible vegetable oil (palmolein), edible common salt, "
    "spices & condiments 0.5% (cumin, chilli, parsley, ginger, cinnamon, black pepper, "
    "dry mango), dehydrated vegetable powder (onion, garlic), sugar, maltodextrin, "
    "flavour enhancer (INS 627, INS 631), acidity regulator (INS 296, INS 330), "
    "anticaking agent (INS 551), natural & nature identical flavouring substances "
    "(chaat). Nutritional Information (per 100g)NutrientAmountEnergy545 kcal"
    "Protein7.4gCarbohydrates53.5gTotal Sugars3.0gAdded Sugars2.2gTotal Fat32.2g"
    "Saturated Fat15.3gTrans Fat0.1gCholesterol<1mgSodium982mg"
)


def label_extractor(state: NutritionState) -> dict:
    """Populate raw OCR text from an image path, or keep supplied text."""

    if state.get("raw_ocr_text"):
        return {"raw_ocr_text": state["raw_ocr_text"]}

    image_path = state.get("image_path")
    if not image_path:
        raise ValueError("Provide raw label text, a text file, or an image file.")

    return {"raw_ocr_text": extract_text_from_image(image_path)}


def build_workflow():
    graph = StateGraph(NutritionState)

    graph.add_node("label_extractor", label_extractor)
    graph.add_node("parse_nutrition_label", parse_nutrition_label)
    graph.add_node("allergen_analysis", allergen_analysis)
    graph.add_node("ingredient_analysis", ingredient_analysis)
    graph.add_node("ins_analysis", ins_analysis)
    graph.add_node("nova_analysis", nova_analysis)
    graph.add_node("nutrient_analysis", nutrient_analysis)
    graph.add_node("final_analysis", final_analysis)

    graph.add_edge(START, "label_extractor")
    graph.add_edge("label_extractor", "parse_nutrition_label")
    graph.add_edge("parse_nutrition_label", "allergen_analysis")
    graph.add_edge("parse_nutrition_label", "ingredient_analysis")
    graph.add_edge("parse_nutrition_label", "ins_analysis")
    graph.add_edge("parse_nutrition_label", "nova_analysis")
    graph.add_edge("parse_nutrition_label", "nutrient_analysis")
    graph.add_edge("allergen_analysis", "final_analysis")
    graph.add_edge("ingredient_analysis", "final_analysis")
    graph.add_edge("ins_analysis", "final_analysis")
    graph.add_edge("nova_analysis", "final_analysis")
    graph.add_edge("nutrient_analysis", "final_analysis")
    graph.add_edge("final_analysis", END)
    
    return graph.compile()


def initial_state(raw_ocr_text: str = "", image_path: str | None = None) -> NutritionState:
    state: NutritionState = {
        "raw_ocr_text": raw_ocr_text,
        "parsed_label": None,
        "nutrient_analysis": None,
        "ingredient_analysis": None,
        "ins_analysis": None,
        "allergen_analysis": None,
        "processing_analysis": None,
        "final_report": None,
    }
    if image_path:
        state["image_path"] = image_path
    return state


def state_from_args(args: argparse.Namespace) -> NutritionState:
    if args.image:
        return initial_state(image_path=args.image)

    if args.file:
        return initial_state(raw_ocr_text=Path(args.file).read_text(encoding="utf-8"))

    if args.text:
        return initial_state(raw_ocr_text=args.text)

    if args.input:
        input_path = Path(args.input)
        if input_path.suffix.lower() in IMAGE_EXTENSIONS:
            return initial_state(image_path=args.input)
        return initial_state(raw_ocr_text=input_path.read_text(encoding="utf-8"))

    return initial_state(raw_ocr_text=SAMPLE_OCR_TEXT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Foodify AI nutrition workflow.")
    parser.add_argument(
        "input",
        nargs="?",
        help="Optional path to an image file or text file containing label text.",
    )
    parser.add_argument("--text", help="Raw OCR nutrition label text.")
    parser.add_argument("--file", help="Path to a text file containing raw OCR nutrition label text.")
    parser.add_argument("--image", help="Path to a nutrition label image file.")
    args = parser.parse_args()

    workflow = build_workflow()
    state = state_from_args(args)
    final_report = {}

    print("Starting Foodify AI workflow...", flush=True)
    for update in workflow.stream(state, stream_mode="updates"):
        for node_name, node_update in update.items():
            print(f"Completed node: {node_name}", flush=True)
            if node_name == "final_analysis":
                final_report = node_update.get("final_report", {})

    print("Workflow execution complete.")
    print(json.dumps(final_report, indent=2))


if __name__ == "__main__":
    main()

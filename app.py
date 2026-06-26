from __future__ import annotations

import json
import re
import tempfile
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from helper import NUTRIENT_SCALES


APP_NAME = "foodify.ai"
UPLOAD_TYPES = ["png", "jpg", "jpeg", "webp", "bmp"]
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


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

        :root {
            color-scheme: dark;
            --ink: #f4f7ed;
            --muted: #a4b0a5;
            --line: rgba(211, 232, 205, 0.15);
            --mint: #42e58b;
            --mint-soft: rgba(66, 229, 139, 0.13);
            --lime: #cbff69;
            --amber: #ffbd55;
            --red: #ff6b5f;
            --paper: #080d0a;
            --panel: rgba(17, 25, 20, 0.92);
            --panel-strong: #111914;
            --panel-soft: rgba(255, 255, 255, 0.055);
        }

        html, body, [class*="css"] {
            font-family: 'Manrope', system-ui, sans-serif;
            color: var(--ink);
        }

        .stApp {
            background-color: var(--paper);
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
            background-size: 42px 42px;
        }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }

        h1, h2, h3 {
            font-family: 'Space Grotesk', 'Manrope', system-ui, sans-serif;
            letter-spacing: 0;
        }

        .hero {
            border: 1px solid var(--line);
            background: linear-gradient(135deg, rgba(22, 34, 27, 0.96), rgba(9, 14, 11, 0.94));
            border-radius: 24px;
            padding: 34px;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
            margin-bottom: 22px;
        }

        .brand {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            border: 1px solid rgba(66, 229, 139, 0.34);
            border-radius: 999px;
            padding: 8px 14px;
            background: rgba(66, 229, 139, 0.11);
            color: var(--mint);
            font-weight: 800;
            font-size: 0.92rem;
        }

        .hero h1 {
            font-size: clamp(2.4rem, 5vw, 5.2rem);
            line-height: 0.94;
            margin: 18px 0 14px;
        }

        .hero p {
            color: var(--muted);
            max-width: 760px;
            font-size: 1.08rem;
            line-height: 1.65;
            margin: 0;
        }

        .panel {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 18px;
            padding: 20px;
            box-shadow: 0 18px 56px rgba(0, 0, 0, 0.24);
        }

        .metric-card {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 16px;
            padding: 18px;
            min-height: 138px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 800;
            text-transform: uppercase;
        }

        .metric-value {
            font-family: 'Space Grotesk', 'Manrope', system-ui, sans-serif;
            font-size: 2.15rem;
            font-weight: 700;
            margin: 7px 0;
        }

        .bar-track {
            width: 100%;
            height: 12px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--red), var(--amber), var(--mint));
        }

        .scale-card {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .scale-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 10px;
        }

        .scale-name {
            font-weight: 800;
            font-size: 1rem;
            text-transform: capitalize;
        }

        .scale-value {
            color: var(--muted);
            font-weight: 700;
            font-size: 0.9rem;
            text-align: right;
        }

        .scale-track {
            position: relative;
            height: 12px;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--red), var(--amber), var(--mint));
            margin: 12px 0 9px;
        }

        .scale-pin {
            position: absolute;
            top: -5px;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #f4f7ed;
            border: 4px solid #121a15;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.45);
            transform: translateX(-50%);
        }

        .scale-breaks {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }

        .scale-break {
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 4px 8px;
            color: var(--muted);
            background: rgba(255, 255, 255, 0.04);
            font-size: 0.78rem;
            font-weight: 700;
        }

        .chip {
            display: inline-block;
            margin: 0;
            padding: 7px 11px;
            border-radius: 999px;
            background: var(--mint-soft);
            color: #baf8ce;
            border: 1px solid rgba(66, 229, 139, 0.28);
            font-weight: 700;
            font-size: 0.86rem;
        }

        .chip-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }

        .warn-chip {
            background: rgba(255, 189, 85, 0.14);
            color: #ffd38a;
            border-color: rgba(255, 184, 77, 0.3);
        }

        .danger-chip {
            background: rgba(255, 107, 95, 0.14);
            color: #ffb6af;
            border-color: rgba(239, 99, 81, 0.3);
        }

        .insight-card {
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .insight-title {
            font-weight: 800;
            margin-bottom: 6px;
        }

        .section-title {
            font-family: 'Space Grotesk', 'Manrope', system-ui, sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin: 28px 0 12px;
        }

        .tiny-note {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.55;
        }

        div[data-testid="stFileUploader"] {
            border: 1px dashed rgba(66, 229, 139, 0.42);
            background: rgba(255, 255, 255, 0.045);
            border-radius: 16px;
            padding: 12px;
        }

        .stButton > button {
            width: 100%;
            border-radius: 12px;
            border: 0;
            background: var(--mint);
            color: #07100b;
            font-weight: 800;
            padding: 0.78rem 1rem;
        }

        .stButton > button:hover {
            background: var(--lime);
            color: #07100b;
            border: 0;
        }

        .stDataFrame, div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
        }

        div[data-testid="stExpander"] {
            border-color: var(--line);
            background: rgba(255, 255, 255, 0.035);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def score_color(score: float) -> str:
    if score >= 4:
        return "#2fbf71"
    if score >= 2.8:
        return "#ffb84d"
    return "#ef6351"


def clean_text(value: Any) -> str:
    return escape(str(value or ""))


def nutrient_scale_for(item: dict[str, Any]) -> tuple[str | None, list[float]]:
    nutrient = str(item.get("nutrient", "")).lower()
    scale_key = NUTRIENT_SCALE_KEYS.get(nutrient)
    scale = item.get("scale_breakpoints") or NUTRIENT_SCALES.get(scale_key or "", [])
    return scale_key, scale


def clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(5.0, float(value)))
    except (TypeError, ValueError):
        return default


def render_score_bar(label: str, score: Any, caption: str = "") -> None:
    score_value = clamp_score(score)
    width = score_value / 5 * 100
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{clean_text(label)}</div>
            <div class="metric-value" style="color:{score_color(score_value)}">{score_value:.1f}/5</div>
            <div class="bar-track"><div class="bar-fill" style="width:{width:.0f}%"></div></div>
            <div class="tiny-note" style="margin-top:10px;">{clean_text(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scale_meter(item: dict[str, Any]) -> None:
    score_value = clamp_score(item.get("score"))
    pin = score_value / 5 * 100
    nutrient = clean_text(str(item.get("nutrient", "Nutrient")).replace("_", " "))
    scale_key, scale = nutrient_scale_for(item)
    value = item.get("value_per_100g")
    unit = clean_text(item.get("unit") or "")
    classification = clean_text(item.get("classification", "unknown"))
    explanation = clean_text(item.get("explanation", ""))

    value_text = "missing"
    if value is not None:
        value_text = f"{value:g}{unit} per 100g" if isinstance(value, int | float) else f"{clean_text(value)}{unit} per 100g"

    scale_label = clean_text(scale_key or "no configured scale")
    scale_breaks = "".join(f'<span class="scale-break">{breakpoint:g}</span>' for breakpoint in scale)

    st.markdown(
        f"""
        <div class="scale-card">
            <div class="scale-head">
                <div>
                    <div class="scale-name">{nutrient}</div>
                    <div class="tiny-note">{classification}</div>
                </div>
                <div class="scale-value">{value_text}<br>{score_value:.1f}/5</div>
            </div>
            <div class="scale-track"><div class="scale-pin" style="left:{pin:.0f}%"></div></div>
            <div class="tiny-note">{explanation}</div>
            <div class="tiny-note" style="margin-top:10px;">helper scale: {scale_label}</div>
            <div class="scale-breaks">{scale_breaks}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_insights(title: str, insights: list[dict[str, Any]], empty_text: str) -> None:
    st.markdown(f'<div class="section-title">{clean_text(title)}</div>', unsafe_allow_html=True)
    if not insights:
        st.markdown(f'<div class="tiny-note">{clean_text(empty_text)}</div>', unsafe_allow_html=True)
        return

    for insight in insights:
        if not isinstance(insight, dict):
            continue
        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-title">{clean_text(insight.get("title", "Insight"))}</div>
                <div class="tiny-note">{clean_text(insight.get("explanation", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def normalize_chip_values(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, list | tuple | set):
        return list(values)
    return [values]


def normalize_ins_codes(values: Any) -> list[str]:
    codes: list[str] = []

    for value in normalize_chip_values(values):
        text = str(value).strip()
        if not text:
            continue

        parts = re.split(r"[,;/\s]+", text)
        if len(parts) == 1 and re.fullmatch(r"\d{6,}[a-zA-Z]?", text):
            parts = re.findall(r"\d{3}[a-zA-Z]?", text)

        for part in parts:
            code = part.strip()
            if not code:
                continue
            code = re.sub(r"^ins[-\s]*", "", code, flags=re.IGNORECASE)
            codes.append(f"INS {code}")

    return codes


def render_chips(values: Any, style: str = "chip") -> None:
    values = normalize_chip_values(values)
    if not values:
        st.markdown('<div class="tiny-note">Nothing detected.</div>', unsafe_allow_html=True)
        return

    html = " ".join(f'<span class="{style}">{clean_text(value)}</span>' for value in values)
    html = f'<div class="chip-wrap">{html}</div>'
    st.markdown(html, unsafe_allow_html=True)


def workflow_from_image(image_path: str, on_node_complete=None) -> tuple[dict[str, Any], list[str]]:
    from main import build_workflow, initial_state

    workflow = build_workflow()
    state = initial_state(image_path=image_path)
    completed: list[str] = []

    for update in workflow.stream(state, stream_mode="updates"):
        for node_name, node_update in update.items():
            completed.append(node_name)
            if isinstance(node_update, dict):
                state.update(node_update)
            if on_node_complete:
                on_node_complete(node_name, len(completed))

    return state, completed


def save_uploaded_image(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


def get_final_report(state: dict[str, Any]) -> dict[str, Any]:
    report = state.get("final_report") or {}
    if isinstance(report, str):
        try:
            return json.loads(report)
        except json.JSONDecodeError:
            return {"executive_summary": report}
    return report


def render_report(state: dict[str, Any], completed: list[str]) -> None:
    report = get_final_report(state)
    parsed = state.get("parsed_label") or {}
    nutrient_items = state.get("nutrient_analysis") or []
    score_breakdown = report.get("score_breakdown") or {}
    rating = report.get("overall_rating") or {}
    recommendation = report.get("consumption_recommendation") or {}
    positives = report.get("positives") or []
    concerns = report.get("concerns") or []

    st.markdown('<div class="section-title">Product Snapshot</div>', unsafe_allow_html=True)
    top_cols = st.columns([1.15, 1, 1])
    with top_cols[0]:
        render_score_bar(
            "Overall rating",
            rating.get("score", 0),
            rating.get("rating_label", "Awaiting rating"),
        )
    with top_cols[1]:
        render_score_bar(
            "Nutrients",
            score_breakdown.get("nutrients", 0),
            "Balance of key label nutrients.",
        )
    with top_cols[2]:
        render_score_bar(
            "Additives",
            score_breakdown.get("additives", 0),
            "INS additive safety signal.",
        )

    st.markdown('<div class="section-title">Recommendation</div>', unsafe_allow_html=True)
    rec_cols = st.columns([1, 2])
    with rec_cols[0]:
        st.markdown(
            f"""
            <div class="panel">
                <div class="metric-label">Frequency</div>
                <div class="metric-value">{clean_text(recommendation.get("frequency", "Review"))}</div>
                <div class="tiny-note">{clean_text(recommendation.get("recommendation", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with rec_cols[1]:
        st.markdown(
            f"""
            <div class="panel">
                <div class="metric-label">Executive summary</div>
                <div style="font-size:1.05rem; line-height:1.7; margin-top:8px;">
                    {clean_text(report.get("executive_summary", "The analysis completed, but no summary was returned."))}
                </div>
                <div class="tiny-note" style="margin-top:12px;">{clean_text(recommendation.get("explanation", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Score Breakdown</div>', unsafe_allow_html=True)
    score_cols = st.columns(5)
    for index, key in enumerate(["allergens", "additives", "processing", "ingredients", "nutrients"]):
        with score_cols[index]:
            render_score_bar(key.title(), score_breakdown.get(key, 0))

    insight_cols = st.columns(2)
    with insight_cols[0]:
        render_insights("Positives", positives, "No positive signals were returned.")
    with insight_cols[1]:
        render_insights("Concerns", concerns, "No concerns were returned.")

    st.markdown('<div class="section-title">Nutrient Scales</div>', unsafe_allow_html=True)
    if isinstance(nutrient_items, list) and nutrient_items:
        left, right = st.columns(2)
        for index, item in enumerate(nutrient_items):
            with left if index % 2 == 0 else right:
                if isinstance(item, dict):
                    render_scale_meter(item)
    else:
        st.info("No nutrient scale data was returned.")

    st.markdown('<div class="section-title">Label Data</div>', unsafe_allow_html=True)
    data_cols = st.columns([1, 1])
    with data_cols[0]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Ingredients")
        render_chips(parsed.get("ingredients", []))
        st.subheader("INS codes")
        render_chips(normalize_ins_codes(parsed.get("ins_codes", [])), "warn-chip")
        st.markdown("</div>", unsafe_allow_html=True)
    with data_cols[1]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Warnings")
        render_chips(report.get("key_warnings", []), "danger-chip")
        st.subheader("Suitable for")
        render_chips(report.get("suitable_for", []))
        st.subheader("Not suitable for")
        render_chips(report.get("not_suitable_for", []), "danger-chip")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Nutrition Table</div>', unsafe_allow_html=True)
    nutrition_table = parsed.get("nutrition_table") or {}
    if nutrition_table:
        rows = []
        for nutrient, row in nutrition_table.items():
            if isinstance(row, dict):
                rows.append(
                    {
                        "Nutrient": nutrient.replace("_", " ").title(),
                        "Per 100g": row.get("per_100g"),
                        "Per Serving": row.get("per_serving"),
                        "Unit": row.get("unit"),
                    }
                )
            else:
                rows.append({"Nutrient": nutrient.replace("_", " ").title(), "Per 100g": row})
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No nutrition table was parsed from the label.")

    with st.expander("Processing details"):
        st.write("Completed nodes:", completed)
        st.json(
            {
                "parsed_label": parsed,
                "nutrient_analysis": state.get("nutrient_analysis"),
                "ingredient_analysis": state.get("ingredient_analysis"),
                "ins_analysis": state.get("ins_analysis"),
                "allergen_analysis": state.get("allergen_analysis"),
                "processing_analysis": state.get("processing_analysis"),
            }
        )

    with st.expander("Raw OCR text"):
        st.text(state.get("raw_ocr_text") or "")


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="F",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()

    st.markdown(
        f"""
        <div class="hero">
            <div class="brand">fresh label intelligence</div>
            <h1>{APP_NAME}</h1>
            <p>
                Upload a packaged-food label and get OCR, ingredient analysis, additive safety,
                allergen checks, nutrient scoring against helper.py scales, and a practical eating recommendation in one dark view.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    upload_col, preview_col = st.columns([0.95, 1.05])
    with upload_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload nutrition label image",
            type=UPLOAD_TYPES,
            accept_multiple_files=False,
        )
        analyze = st.button("Analyze label", disabled=uploaded_file is None)
        st.markdown(
            '<div class="tiny-note">For best results, upload a clear photo where the nutrition table and ingredients are readable.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with preview_col:
        if uploaded_file is not None:
            st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
        else:
            st.markdown(
                """
                <div class="panel" style="min-height:260px; display:flex; align-items:center; justify-content:center;">
                    <div style="text-align:center;">
                        <div style="font-family:'Space Grotesk'; font-size:2rem; font-weight:700;">Ready for a label</div>
                        <div class="tiny-note">PNG, JPG, JPEG, WEBP, or BMP</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if analyze and uploaded_file is not None:
        image_path = save_uploaded_image(uploaded_file)
        progress = st.progress(0, text="Starting foodify.ai analysis...")
        status = st.empty()

        expected_nodes = 8

        def update_status(node_name: str, completed_count: int) -> None:
            percent = min(95, int(completed_count / expected_nodes * 100))
            progress.progress(percent, text=f"Completed {node_name.replace('_', ' ')}")

        try:
            with st.spinner("Reading the label and building your report..."):
                state, completed = workflow_from_image(image_path, update_status)
            progress.progress(100, text="Analysis complete")
            status.success("Done. Your product report is ready.")
            st.session_state["foodify_state"] = state
            st.session_state["foodify_completed"] = completed
        except Exception as exc:
            progress.empty()
            status.error(f"Analysis failed: {exc}")

    if "foodify_state" in st.session_state:
        render_report(
            st.session_state["foodify_state"],
            st.session_state.get("foodify_completed", []),
        )


if __name__ == "__main__":
    main()

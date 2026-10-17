"""Transparent step-by-step calculation protocol with rendered formulas."""

from __future__ import annotations

from imgui_bundle import hello_imgui, imgui

from ui.latex import formula_asset, render_dynamic_formula
from ui.state import AppState

# Static formula fallback for each of the 14 steps (used if steps_latex is absent).
STEP_FORMULAS: list[str | None] = [
    "w0", "w1_prof", "w_day", "e_sigma", "c_req", "n_total_prof", "p_pv",
    "n_pv", "voc_string", "i_charge", "inverter_surge", "cable", "cable", None,
]


def _draw_asset_scaled(asset: str) -> None:
    """Draw a formula image scaled to the available width."""
    max_width = max(120.0, imgui.get_content_region_avail().x - 16.0)
    try:
        from pathlib import Path

        from PIL import Image

        path = Path(__file__).resolve().parent.parent / asset
        with Image.open(path) as image:
            width, height = image.size
    except Exception:  # noqa: BLE001
        hello_imgui.image_from_asset(asset)
        return
    if width > max_width:
        scale = max_width / width
        hello_imgui.image_from_asset(asset, imgui.ImVec2(max_width, height * scale))
    else:
        hello_imgui.image_from_asset(asset)


def _draw_step(step: str, latex: str | None, fallback_key: str | None) -> None:
    """Draw step description as text and the value substitution as a rendered formula."""
    description = str(step).split(":", 1)[0]
    imgui.text_colored((0.0, 0.45, 0.75, 1.0), description)

    rendered = False
    if latex:
        asset = render_dynamic_formula(latex)
        if asset:
            _draw_asset_scaled(asset)
            rendered = True
    if not rendered:
        if fallback_key:
            fallback = formula_asset(fallback_key)
            if fallback:
                _draw_asset_scaled(fallback)
        imgui.text_wrapped(str(step))
    imgui.separator()


def draw(state: AppState) -> None:
    imgui.text("Пошаговый инженерный расчет с формулами и подстановкой значений:")
    imgui.separator()

    if state.error_message:
        imgui.text_colored((0.95, 0.35, 0.35, 1.0), state.error_message)
        return
    if not state.results:
        imgui.text_colored(
            (0.9, 0.6, 0.2, 1.0),
            "⚠️ Выполните расчет на вкладке «Исходные данные», чтобы увидеть ход решения.",
        )
        return

    steps = list(state.results.get("steps", []))
    steps_latex = list(state.results.get("steps_latex", []))
    for index, step in enumerate(steps):
        latex = steps_latex[index] if index < len(steps_latex) else None
        fallback = STEP_FORMULAS[index] if index < len(STEP_FORMULAS) else None
        _draw_step(str(step), latex, fallback)

    warnings = list(state.results.get("warnings", []))
    if warnings:
        imgui.text_colored((0.95, 0.65, 0.2, 1.0), "Предупреждения:")
        for warning in warnings:
            imgui.text_wrapped(f"• {warning}")

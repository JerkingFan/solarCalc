"""Mission / trainer panel shown inside the input tab."""

from __future__ import annotations

from typing import Any

from imgui_bundle import imgui

from ui.state import AppState


def _progress_bar(fraction: float, ok: bool) -> None:
    color = (0.2, 0.75, 0.2, 1.0) if ok else (0.95, 0.35, 0.35, 1.0)
    imgui.push_style_color(imgui.Col_.plot_histogram, color)
    imgui.progress_bar(fraction, size_arg=imgui.ImVec2(imgui.get_content_region_avail().x, 18))
    imgui.pop_style_color()


def _recalculate_for_mission(state: AppState) -> None:
    """Force a full recalculation and mission evaluation."""
    state.recalculate(force=True)


def draw_mission_panel(state: AppState) -> None:
    if not state.current_mission:
        return

    mission_dict = state.current_mission
    imgui.separator()
    imgui.text_colored((0.95, 0.85, 0.35, 1.0), f"Задание тренажёра: {mission_dict.get('title', '')}")
    imgui.text_wrapped(mission_dict.get("description", ""))

    budget = float(mission_dict.get("budget_byn", 0.0))
    capex = 0.0
    eval_data = state.mission_evaluation
    if eval_data:
        capex = float(eval_data.get("capex_byn", 0.0))

    fraction = min(1.0, capex / budget) if budget > 0 else 0.0
    over_budget = capex > budget
    imgui.text(f"Бюджет: {capex:,.0f} / {budget:,.0f} BYN")
    _progress_bar(fraction, not over_budget)

    imgui.spacing()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Обязательные нагрузки:")
    for load in mission_dict.get("required_ac_loads", []):
        imgui.bullet_text(f"AC: {load.get('name')} {load.get('power'):g} Вт × {load.get('hours_week'):g} ч/нед")
    for load in mission_dict.get("required_dc_loads", []):
        imgui.bullet_text(f"DC: {load.get('name')} {load.get('power'):g} Вт × {load.get('hours_week'):g} ч/нед")

    if eval_data:
        imgui.spacing()
        score = int(eval_data.get("score", 0))
        passed = bool(eval_data.get("passed"))
        score_color = (0.2, 0.75, 0.2, 1.0) if passed else (0.95, 0.35, 0.35, 1.0)
        imgui.text_colored(score_color, f"Оценка решения: {score}/100")
        if passed:
            imgui.text_colored((0.2, 0.75, 0.2, 1.0), "✅ Задание выполнено!")
        else:
            imgui.text_colored((0.95, 0.35, 0.35, 1.0), "❌ Есть нарушения условий задания.")

        imgui.spacing()
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Критерии:")
        if imgui.begin_table("MissionCriteria", 3, 0):
            imgui.table_setup_column("Критерий")
            imgui.table_setup_column("Значение")
            imgui.table_setup_column("Статус")
            imgui.table_headers_row()
            for criterion in eval_data.get("criteria", []):
                imgui.table_next_row()
                imgui.table_set_column_index(0)
                imgui.text(str(criterion.get("name", "")))
                imgui.table_set_column_index(1)
                imgui.text(str(criterion.get("value", "")))
                imgui.table_set_column_index(2)
                if criterion.get("ok"):
                    imgui.text_colored((0.2, 0.75, 0.2, 1.0), "OK")
                else:
                    imgui.text_colored((0.95, 0.35, 0.35, 1.0), "FAIL")
            imgui.end_table()

        hints = eval_data.get("hints", [])
        if hints:
            imgui.spacing()
            imgui.text_colored((0.95, 0.75, 0.2, 1.0), "Подсказки:")
            for hint in hints[:4]:
                imgui.text_wrapped(f"• {hint}")

    if imgui.button("🔄 Проверить решение", size=(260, 34)):
        _recalculate_for_mission(state)

"""PV-Calc Pro desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Guard against running with the system Python that may miss dependencies.
try:
    import numpy  # noqa: F401
except ImportError as exc:
    print(
        "Ошибка: не найден пакет numpy. "
        "Запускайте проект через ./run.sh или .venv/bin/python main.py"
    )
    raise SystemExit(1) from exc

from imgui_bundle import hello_imgui, imgui, implot

from ui import inspector, view_catalog, view_charts, view_input, view_results, view_scheme, view_steps
from ui.diagnostics import compute_diagnostics
from ui.state import AppState
from ui.widgets import help_marker, tooltip

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    hello_imgui.override_assets_folder(str(BASE_DIR))
except Exception:  # noqa: BLE001
    hello_imgui.set_assets_folder(str(BASE_DIR))

app_state = AppState()


def _load_system_font(size_pixels: float):
    """Load a readable system font with Cyrillic support."""
    candidates = (
        # Windows
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )
    params = hello_imgui.FontLoadingParams()
    params.inside_assets = False
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return hello_imgui.load_font(candidate, size_pixels, params)
            except Exception:  # noqa: BLE001
                continue
    return None


def _load_fonts() -> None:
    implot.create_context()
    font = _load_system_font(16.0)
    if font is not None:
        imgui.get_io().font_default = font


def _tab(label: str, draw_callback, scroll_id: str) -> None:
    opened, _ = imgui.begin_tab_item(label)
    if opened:
        imgui.begin_child(scroll_id, imgui.ImVec2(0, 700), 1)
        draw_callback()
        imgui.end_child()
        imgui.end_tab_item()


def _draw_onboarding() -> None:
    if not app_state.show_onboarding:
        return
    imgui.open_popup("Добро пожаловать в PV-Calc Pro")
    visible, _ = imgui.begin_popup_modal(
        "Добро пожаловать в PV-Calc Pro",
        None,
        imgui.WindowFlags_.always_auto_resize,
    )
    if visible:
        imgui.text_wrapped(
            "Это главный экран проектирования автономной фотоэлектрической системы. "
            "Начните с готового сценария, затем скорректируйте нагрузки, климат и оборудование."
        )
        imgui.separator()
        if imgui.button("Начать со сценария 'Дача'", size=(280, 38)):
            app_state.apply_preset("Дача")
            app_state.show_onboarding = False
            imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("Закрыть", size=(120, 38)):
            app_state.show_onboarding = False
            imgui.close_current_popup()
        imgui.end_popup()


def _draw_metric(label: str, value: str, ok: bool | None = None) -> None:
    """Draw a compact metric line with optional OK/FAIL color."""
    if ok is True:
        color = (0.2, 0.75, 0.2, 1.0)
    elif ok is False:
        color = (0.95, 0.35, 0.35, 1.0)
    else:
        color = (0.9, 0.9, 0.9, 1.0)
    imgui.text_colored((0.6, 0.75, 0.95, 1.0), f"{label}:")
    imgui.same_line()
    imgui.text_colored(color, value)


def _draw_trainer_hud(state: AppState) -> None:
    """Persistent trainer mission status panel (visible alongside inputs)."""
    if state.mode != "trainer" or not state.current_mission:
        return

    imgui.set_next_window_pos((1070, 10), imgui.Cond_.once)
    imgui.set_next_window_size((340, 560), imgui.Cond_.once)
    imgui.begin(
        "Тренажёр: статус задания",
        flags=imgui.WindowFlags_.no_collapse,
    )

    mission = state.current_mission
    imgui.text_colored((0.95, 0.85, 0.35, 1.0), mission.get("title", ""))
    imgui.text_wrapped(mission.get("description", ""))
    imgui.separator()

    eval_data = state.mission_evaluation
    results = state.results
    budget = float(mission.get("budget_byn", 0.0))
    capex = float(eval_data.get("capex_byn", 0.0)) if eval_data else 0.0
    fraction = min(1.0, capex / budget) if budget > 0 else 0.0
    over_budget = capex > budget

    imgui.text("Бюджет:")
    imgui.same_line()
    imgui.text_colored(
        (0.95, 0.35, 0.35, 1.0) if over_budget else (0.2, 0.75, 0.2, 1.0),
        f"{capex:,.0f} / {budget:,.0f} BYN",
    )
    color = (0.2, 0.75, 0.2, 1.0) if not over_budget else (0.95, 0.35, 0.35, 1.0)
    imgui.push_style_color(imgui.Col_.plot_histogram, color)
    imgui.progress_bar(fraction, size_arg=imgui.ImVec2(imgui.get_content_region_avail().x, 16))
    imgui.pop_style_color()

    if results:
        daily_energy = float(results.get("daily_energy_wh", 0.0))
        pv_actual = float(results.get("pv_actual_w", 0.0))
        batt_count = int(results.get("battery_count", 0))
        batt_capacity = float(results.get("battery_capacity_actual", 0.0))
        autonomy = float(state.days_autonomy)

        imgui.separator()
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Ключевые расчётные показатели:")
        _draw_metric("Энергия суточная", f"{daily_energy:.0f} Вт·ч")
        _draw_metric("Мощность PV", f"{pv_actual:.0f} Вт")
        _draw_metric("АКБ", f"{batt_count} шт × {batt_capacity:.0f} А·ч")
        _draw_metric("Автономность", f"{autonomy:.1f} дн")

    if eval_data:
        score = int(eval_data.get("score", 0))
        passed = bool(eval_data.get("passed"))
        score_color = (0.2, 0.75, 0.2, 1.0) if passed else (0.95, 0.35, 0.35, 1.0)
        imgui.separator()
        imgui.text_colored(score_color, f"Оценка: {score}/100")
        if passed:
            imgui.text_colored((0.2, 0.75, 0.2, 1.0), "✅ Задание выполнено!")
        else:
            imgui.text_colored((0.95, 0.35, 0.35, 1.0), "❌ Есть нарушения")

        imgui.separator()
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Критерии:")
        for criterion in eval_data.get("criteria", [])[:7]:
            ok = criterion.get("ok")
            marker = "✓" if ok else "✗"
            col = (0.2, 0.75, 0.2, 1.0) if ok else (0.95, 0.35, 0.35, 1.0)
            imgui.text_colored(col, f"{marker} {criterion.get('name', '')}")
            imgui.text(f"   {criterion.get('value', '')}")

        hints = eval_data.get("hints", [])
        if hints:
            imgui.separator()
            imgui.text_colored((0.95, 0.75, 0.2, 1.0), "Подсказка:")
            imgui.text_wrapped(hints[0])
    else:
        imgui.text_colored(
            (0.9, 0.6, 0.2, 1.0),
            "Нажмите «Рассчитать АФС» или включите авто-расчёт.",
        )

    # --- Engineering diagnostics inside the trainer status window --------------
    if results:
        diagnostics = compute_diagnostics(state, results)
        if diagnostics:
            imgui.separator()
            imgui.text_colored((0.95, 0.65, 0.2, 1.0), "Инженерная диагностика:")
            tooltip(
                "Автоматические проверки совместимости компонентов: напряжения, токи, "
                "пусковые режимы, сечения кабелей. Критические сбои блокируют зачёт задания."
            )
            critical = sum(1 for d in diagnostics if d["level"] == "critical")
            warning = sum(1 for d in diagnostics if d["level"] == "warning")
            if critical:
                imgui.text_colored((0.95, 0.15, 0.15, 1.0), f"Критических сбоев: {critical}")
            if warning:
                imgui.text_colored((0.95, 0.75, 0.15, 1.0), f"Предупреждений: {warning}")
            for item in diagnostics[:6]:
                if item["level"] == "critical":
                    color = (0.95, 0.15, 0.15, 1.0)
                elif item["level"] == "warning":
                    color = (0.95, 0.75, 0.15, 1.0)
                else:
                    color = (0.25, 0.65, 0.95, 1.0)
                imgui.text_colored(color, f"• {item['message']}")
                recommendation = item.get("recommendation")
                if recommendation:
                    tooltip(f"Рекомендация: {recommendation}")
            if len(diagnostics) > 6:
                imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"... и ещё {len(diagnostics) - 6} (см. инспектор)")

    imgui.separator()
    if imgui.button("🔄 Проверить", size=(120, 30)):
        state.recalculate(force=True)
    imgui.same_line()
    if imgui.button("Следующее задание", size=(140, 30)):
        import random
        from core.missions import get_mission_by_title

        titles = state.missions
        idx = random.randrange(len(titles))
        state.trainer_mission_idx = idx
        state.apply_mission(get_mission_by_title(titles[idx]))

    imgui.end()


def gui() -> None:
    imgui.set_next_window_size((1050, 860), imgui.Cond_.once)
    imgui.set_next_window_pos((10, 10), imgui.Cond_.once)
    imgui.begin(
        "PV-Calc Pro - Расчет автономной фотоэлектрической системы",
        flags=imgui.WindowFlags_.no_collapse,
    )

    if app_state.error_message:
        imgui.text_colored((0.95, 0.35, 0.35, 1.0), app_state.error_message)
        imgui.separator()
    elif app_state.status_message:
        imgui.text_colored((0.0, 0.45, 0.0, 1.0), app_state.status_message)
        imgui.separator()

    _, app_state.detailed_analysis = imgui.checkbox(
        "Детальный анализ", app_state.detailed_analysis
    )
    help_marker(
        "Если выключено — в инспекторе показываются строгие академические формулы по методичке БГУИР. "
        "Если включено — добавляется инженерный уровень с пояснениями PSH, DoD по химии, пусковыми токами и проверкой холодного Voc."
    )
    imgui.separator()

    _draw_onboarding()
    inspector.draw(app_state)

    if imgui.begin_tab_bar("MainTabs"):
        _tab("Главная / Параметры", lambda: view_input.draw(app_state), "ScrollInput")
        _tab("Результаты и спецификация", lambda: view_results.draw(app_state), "ScrollResults")
        _tab("Графики / Симуляция", lambda: view_charts.draw(app_state), "ScrollCharts")
        _tab("Структурная схема", lambda: view_scheme.draw(app_state), "ScrollScheme")
        _tab("Ход расчета", lambda: view_steps.draw(app_state), "ScrollSteps")
        _tab("Каталог оборудования", view_catalog.draw, "ScrollCatalog")
        imgui.end_tab_bar()

    imgui.end()
    _draw_trainer_hud(app_state)
    if app_state.mode == "trainer":
        imgui.set_next_window_pos((1070, 440), imgui.Cond_.once)
        inspector.draw_side_panel(app_state)


def main() -> None:
    from ui.latex import ensure_formula_images

    ensure_formula_images()
    params = hello_imgui.RunnerParams()
    params.app_window_params.window_title = "PV-Calc Pro ImGui Edition (PV-SAPR)"
    params.app_window_params.window_geometry.size = (1050, 860)
    params.imgui_window_params.tweaked_theme.theme = hello_imgui.ImGuiTheme_.imgui_colors_light
    params.callbacks.load_additional_fonts = _load_fonts
    params.callbacks.show_gui = gui
    hello_imgui.run(params)


if __name__ == "__main__":
    main()

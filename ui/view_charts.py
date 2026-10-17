"""Charts / simulation tab for PV-Calc Pro.

Uses implot (bundled with imgui-bundle) to show hourly PV/load/SOC curves and
monthly production/consumption bar charts.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from imgui_bundle import imgui, implot

from core.simulation import monthly_energy_data, simulate_day
from ui.state import AppState


def _has_results(state: AppState) -> bool:
    return bool(state.results and not state.error_message)


def _draw_daily_simulation(state: AppState) -> None:
    payload = state.calculation_payload()
    sim = simulate_day(payload, state.results or {})
    hours = np.array(sim["hours"], dtype=np.float64)
    pv = np.array(sim["pv_power_w"], dtype=np.float64)
    load = np.array(sim["load_power_w"], dtype=np.float64)
    soc = np.array(sim["battery_soc"], dtype=np.float64)

    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Суточная симуляция (часовой профиль)")
    imgui.text(
        f"PV за сутки: {sim['total_pv_wh']:.0f} Вт·ч | "
        f"Нагрузка: {sim['total_load_wh']:.0f} Вт·ч | "
        f"Часов дефицита: {sim['shortfall_hours']}"
    )

    size = imgui.ImVec2(imgui.get_content_region_avail().x, 220)
    y_max = max(float(np.max(pv)) if pv.size else 0.0, float(np.max(load)) if load.size else 0.0) * 1.1
    if implot.begin_plot("Мощность, Вт", size):
        implot.setup_axes("Час", "Мощность, Вт")
        implot.setup_axis_limits(implot.ImAxis_.x1, 0.0, 23.0)
        implot.setup_axis_limits(implot.ImAxis_.y1, 0.0, max(y_max, 1.0))
        implot.plot_line("PV", hours, pv)
        implot.plot_line("Нагрузка", hours, load)
        implot.end_plot()

    size2 = imgui.ImVec2(imgui.get_content_region_avail().x, 180)
    if implot.begin_plot("Заряд АКБ (SOC)", size2):
        implot.setup_axes("Час", "SOC")
        implot.setup_axis_limits(implot.ImAxis_.x1, 0.0, 23.0)
        implot.setup_axis_limits(implot.ImAxis_.y1, 0.0, 1.0)
        implot.plot_line("SOC", hours, soc)
        implot.end_plot()


def _draw_monthly_chart(state: AppState) -> None:
    payload = state.calculation_payload()
    data = monthly_energy_data(payload, state.results or {})
    months = data["months"]
    prod = np.array(data["production_kwh"], dtype=np.float64)
    cons = np.array(data["consumption_kwh"], dtype=np.float64)
    x = np.arange(len(months), dtype=np.float64)

    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Месячный энергобаланс, кВт·ч/сутки")
    imgui.text(f"Город: {data['city']}")

    size = imgui.ImVec2(imgui.get_content_region_avail().x, 260)
    if implot.begin_plot("Энергобаланс", size):
        implot.setup_axes("Месяц", "кВт·ч/сутки")
        implot.setup_axis_ticks(
            implot.ImAxis_.x1,
            0.0,
            float(len(months) - 1),
            len(months),
            list(months),
        )
        y_max = max(float(np.max(prod)) if prod.size else 0.0, float(np.max(cons)) if cons.size else 0.0) * 1.2
        implot.setup_axis_limits(implot.ImAxis_.y1, 0.0, max(y_max, 1.0))
        implot.plot_bars("Потребление", x, cons, bar_size=0.35)
        implot.plot_bars("Выработка PV", x, prod, bar_size=0.35)
        implot.end_plot()


def draw(state: AppState) -> None:
    imgui.text("Графики и симуляция АФС")
    imgui.separator()

    if not _has_results(state):
        imgui.text_colored(
            (0.9, 0.6, 0.2, 1.0),
            "⚠️ Нет данных для построения графиков. Выполните расчёт на вкладке «Главная / Параметры».",
        )
        return

    _draw_daily_simulation(state)
    imgui.spacing()
    _draw_monthly_chart(state)

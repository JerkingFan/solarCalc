"""Feasibility tests: every training mission must have a passing configuration.

The reference configurations were found by brute-force search over
months / voltages / batteries / panels and are expected to stay passable
as the equipment database evolves.
"""

from __future__ import annotations

import pytest

from core.calculator import SolarSystemCalculator
from core.climate import get_min_design_temperature, get_monthly_psh, get_relief_coefficient
from core.missions import get_mission_by_title, evaluate_mission
from ui.diagnostics import compute_diagnostics


class _DummyState:
    def __init__(self, payload):
        self.__dict__.update(payload)
        self.auto_controller = True


# title, month, system_voltage, battery_model, panel_model
REFERENCE_BUILDS = [
    ("Дача", "Июнь", 24.0, "Гелевая Delta GOR 120Ач (24 В)", "LONGi Hi-MO 5 (540 Вт, Mono-PERC Half-Cut)"),
    ("Мелкое производство", "Июнь", 48.0, "Гелевая Delta GOR 120Ач (24 В)", "JA Solar DeepBlue 4.0 Pro (440 Вт, Bycium+)"),
    ("Автономный вагон / поезд", "Май", 24.0, "Гелевая Delta GOR 120Ач (24 В)", "JA Solar DeepBlue 4.0 Pro (440 Вт, Bycium+)"),
    ("Школа", "Июнь", 48.0, "Гелевая Delta GOR 120Ач (24 В)", "Jinko Tiger Neo 72HL4V (580 Вт, TOPCon)"),
]


def _mission_payload(title: str, month: str, voltage: float, battery_model: str, panel_model: str) -> dict:
    mission = get_mission_by_title(title)
    city = mission.city or "Минск"
    payload = mission.to_dict()
    payload["ac_loads"] = list(mission.required_ac_loads)
    payload["dc_loads"] = list(mission.required_dc_loads)
    payload["days_autonomy"] = float(mission.min_autonomy_days)
    payload["use_climate_data"] = True
    payload["month"] = month
    payload["psh"] = get_monthly_psh(city, month)
    payload["min_temperature_c"] = get_min_design_temperature(city)
    payload["relief_coefficient"] = get_relief_coefficient(mission.relief_name or "Открытая равнина (1.00)")
    payload["cable_length"] = 10.0
    payload["ac_cable_length"] = 5.0
    payload["inverter_efficiency"] = 0.90
    payload["pv_system_efficiency"] = 0.78
    payload["electricity_tariff_byn_kwh"] = 0.30
    payload["project_lifetime_years"] = 15.0
    payload["system_voltage"] = voltage
    payload["battery_model"] = battery_model
    payload["panel_model"] = panel_model
    return payload


@pytest.mark.parametrize(("title", "month", "voltage", "battery", "panel"), REFERENCE_BUILDS)
def test_mission_is_winnable(title, month, voltage, battery, panel):
    mission = get_mission_by_title(title)
    payload = _mission_payload(title, month, voltage, battery, panel)
    results = SolarSystemCalculator(payload).calculate()
    diagnostics = compute_diagnostics(_DummyState(payload), results)
    evaluation = evaluate_mission(mission, payload, results, diagnostics)

    assert evaluation["passed"], [c for c in evaluation["criteria"] if not c["ok"]]
    assert evaluation["score"] == 100
    assert evaluation["capex_byn"] <= mission.budget_byn

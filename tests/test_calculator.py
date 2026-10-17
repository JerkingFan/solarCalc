"""Reference tests for the PV engineering calculator."""

import pytest

from core.calculator import SolarSystemCalculator


def make_payload(**overrides):
    payload = {
        "ac_loads": [
            {"name": "Лампа", "power": 100.0, "hours_week": 7.0, "surge_factor": 1.0}
        ],
        "dc_loads": [],
        "system_voltage": 12.0,
        "days_autonomy": 1.0,
        "psh": 2.0,
        "relief_coefficient": 1.0,
        "panel_model": "МС-50-4 (Базовая)",
        "battery_model": "Leoch LDC 200Ач (12 В)",
        "cable_length": 1.0,
        "ac_cable_length": 1.0,
        "inverter_efficiency": 0.5,
        "pv_system_efficiency": 0.5,
        "min_temperature_c": -25.0,
        "electricity_tariff_byn_kwh": 0.30,
        "project_lifetime_years": 15.0,
    }
    payload.update(overrides)
    return payload


def test_reference_energy_balance():
    result = SolarSystemCalculator(make_payload()).calculate()

    assert result["total_w_ac"] == pytest.approx(700.0)
    assert result["w1_energy"] == pytest.approx(1400.0)
    assert result["daily_energy_wh"] == pytest.approx(200.0)
    assert result["e_sigma"] == pytest.approx(200.0 / 12.0)
    assert result["battery_capacity_total"] == pytest.approx(200.0 / (12.0 * 0.55))
    assert result["p_panel_req"] == pytest.approx(200.0)
    assert result["nm_modules"] == 4
    assert result["pv_actual_w"] == pytest.approx(200.0)
    assert result["battery_series_count"] == 1
    assert result["battery_parallel_count"] == 1
    assert result["battery_count"] == 1
    assert result["inverter_model"]
    assert result["controller_current"] >= result["controller_required_current"]
    assert result["bom"]
    assert result["economics"]["capex_byn"] > 0


def test_panel_count_rounds_up():
    payload = make_payload(
        ac_loads=[{"name": "Нагрузка", "power": 101.0, "hours_week": 7.0, "surge_factor": 1.0}],
        inverter_efficiency=1.0,
        pv_system_efficiency=1.0,
        psh=1.0,
    )
    result = SolarSystemCalculator(payload).calculate()
    assert result["daily_energy_wh"] == pytest.approx(101.0)
    assert result["p_panel_req"] == pytest.approx(101.0)
    assert result["nm_modules"] == 3  # ceil(101 / 50)


def test_battery_series_parallel_configuration():
    payload = make_payload(
        system_voltage=24.0,
        ac_loads=[{"name": "Нагрузка", "power": 50.0, "hours_week": 7.0, "surge_factor": 1.0}],
        inverter_efficiency=1.0,
        pv_system_efficiency=1.0,
        psh=1.0,
    )
    result = SolarSystemCalculator(payload).calculate()
    assert result["battery_series_count"] == 2
    assert result["battery_parallel_count"] == 1
    assert result["battery_count"] == 2


def test_battery_voltage_incompatibility_raises():
    payload = make_payload(system_voltage=24.0, battery_model="Pylontech US5000 (4.8 кВт·ч / 48 В)")
    with pytest.raises(ValueError, match="Несовместимое напряжение АКБ"):
        SolarSystemCalculator(payload).calculate()


def test_controller_is_selected_by_current_and_voltage():
    payload = make_payload(
        system_voltage=24.0,
        panel_model="LONGi Hi-MO 6 (450 Вт)",
        battery_model="Гелевая Delta GOR 120Ач (24 В)",
        ac_loads=[{"name": "Нагрузка", "power": 1000.0, "hours_week": 7.0, "surge_factor": 1.0}],
        inverter_efficiency=1.0,
        pv_system_efficiency=1.0,
        psh=1.0,
    )
    result = SolarSystemCalculator(payload).calculate()
    assert result["controller_required_current"] == pytest.approx((1350.0 / 24.0) * 1.25)
    assert result["controller_current"] >= result["controller_required_current"]
    assert "FM80" in result["controller_model"]
    assert result["pv_cold_string_voc"] < result["controller_max_input_voltage"]


def test_inverter_sizing_accounts_for_surge():
    payload = make_payload(
        system_voltage=24.0,
        battery_model="Гелевая Delta GOR 120Ач (24 В)",
        ac_loads=[
            {"name": "Насос", "power": 500.0, "hours_week": 7.0, "surge_factor": 4.0},
            {"name": "Свет", "power": 100.0, "hours_week": 7.0, "surge_factor": 1.0},
        ],
    )
    result = SolarSystemCalculator(payload).calculate()
    assert result["continuous_ac_power_w"] == pytest.approx(600.0)
    assert result["surge_ac_power_w"] == pytest.approx(2100.0)
    assert result["inverter_required_surge_w"] == pytest.approx(2100.0 * 1.25)
    assert result["inverter_surge_w"] >= result["inverter_required_surge_w"]

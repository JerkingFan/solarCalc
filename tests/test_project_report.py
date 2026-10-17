"""Project IO and report export tests."""

import pytest

from core.calculator import SolarSystemCalculator
from core.project import load_project, save_project
from core.report import export_bom_xlsx, generate_report


def make_payload():
    return {
        "ac_loads": [
            {"name": "Холодильник", "power": 150.0, "hours_week": 84.0, "surge_factor": 5.0}
        ],
        "dc_loads": [{"name": "Роутер", "power": 15.0, "hours_week": 168.0, "surge_factor": 1.0}],
        "system_voltage": 24.0,
        "days_autonomy": 2.0,
        "psh": 1.5,
        "relief_coefficient": 1.0,
        "panel_model": "LONGi Hi-MO 6 (450 Вт)",
        "battery_model": "Гелевая Delta GOR 120Ач (24 В)",
        "cable_length": 5.0,
        "ac_cable_length": 3.0,
        "inverter_efficiency": 0.9,
        "pv_system_efficiency": 0.8,
        "min_temperature_c": -25.0,
        "electricity_tariff_byn_kwh": 0.30,
        "project_lifetime_years": 15.0,
    }


def test_project_save_load_roundtrip(tmp_path):
    payload = make_payload()
    path = save_project(tmp_path / "project.json", payload)
    loaded = load_project(path)
    assert loaded == payload


def test_docx_report_is_generated(tmp_path):
    payload = make_payload()
    result = SolarSystemCalculator(payload).calculate()
    path = generate_report(tmp_path / "report.docx", payload, result)
    assert path.exists()
    assert path.stat().st_size > 0


def test_xlsx_bom_export_is_generated(tmp_path):
    pytest.importorskip("openpyxl")
    payload = make_payload()
    result = SolarSystemCalculator(payload).calculate()
    path = export_bom_xlsx(tmp_path / "bom.xlsx", result)
    assert path.exists()
    assert path.stat().st_size > 0

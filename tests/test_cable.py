"""Cable sizing tests: voltage drop and continuous ampacity."""

import pytest

from core.cable import calculate_cable_section


def test_cable_selected_by_voltage_drop():
    result = calculate_cable_section(current_a=10.0, length_m=10.0, system_voltage_v=24.0)
    assert result.max_drop_v == pytest.approx(0.48)
    assert result.required_section_mm2 == pytest.approx(7.2916666667)
    assert result.section_mm2 == pytest.approx(10.0)
    assert result.actual_drop_v == pytest.approx(0.35)
    assert result.actual_drop_v <= result.max_drop_v


def test_cable_selected_by_ampacity():
    result = calculate_cable_section(current_a=100.0, length_m=1.0, system_voltage_v=48.0)
    # 100 A continuous requires 125 A ampacity with the 1.25 design margin.
    assert result.section_mm2 == pytest.approx(25.0)
    assert result.ampacity_a >= 125.0

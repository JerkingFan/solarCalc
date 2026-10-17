"""Climate model tests."""

import pytest

from core.climate import (
    get_min_design_temperature,
    get_monthly_psh,
    get_relief_coefficient,
)


def test_minsk_december_psh():
    assert get_monthly_psh("Минск", "Декабрь") == pytest.approx(0.9)


def test_relief_coefficient():
    assert get_relief_coefficient("Открытая равнина (1.00)") == pytest.approx(1.0)
    assert get_relief_coefficient("Городская застройка (0.85)") == pytest.approx(0.85)


def test_min_design_temperature():
    assert get_min_design_temperature("Витебск") == pytest.approx(-26.0)

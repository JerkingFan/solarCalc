"""Ready-made PV system scenarios for onboarding and quick start."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScenarioPreset:
    name: str
    description: str
    payload: dict[str, Any]


PRESETS: tuple[ScenarioPreset, ...] = (
    ScenarioPreset(
        name="Дача",
        description="Небольшая дача: свет, холодильник, телевизор, роутер. Разумный первый запуск.",
        payload={
            "use_climate_data": True,
            "city": "Минск",
            "month": "Июль",
            "relief_name": "Открытая равнина (1.00)",
            "system_voltage": 24.0,
            "days_autonomy": 2.0,
            "panel_model": "LONGi Hi-MO 6 (450 Вт)",
            "battery_model": "Гелевая Delta GOR 120Ач (24 В)",
            "cable_length": 10.0,
            "ac_cable_length": 5.0,
            "inverter_efficiency": 0.90,
            "pv_system_efficiency": 0.78,
            "electricity_tariff_byn_kwh": 0.30,
            "project_lifetime_years": 15.0,
            "ac_loads": [
                {"name": "Освещение", "power": 100.0, "hours_week": 35.0, "surge_factor": 1.0},
                {"name": "Холодильник", "power": 150.0, "hours_week": 84.0, "surge_factor": 5.0},
                {"name": "Телевизор", "power": 80.0, "hours_week": 20.0, "surge_factor": 1.2},
            ],
            "dc_loads": [
                {"name": "Роутер 12В", "power": 15.0, "hours_week": 168.0, "surge_factor": 1.0},
                {"name": "Аварийный свет", "power": 20.0, "hours_week": 14.0, "surge_factor": 1.0},
            ],
        },
    ),
    ScenarioPreset(
        name="Дом (резерв)",
        description="48В домашний резерв: холодильник, свет, котел/циркуляция, связь.",
        payload={
            "use_climate_data": True,
            "city": "Минск",
            "month": "Июль",
            "relief_name": "Открытая равнина (1.00)",
            "system_voltage": 48.0,
            "days_autonomy": 1.5,
            "panel_model": "Jinko Tiger Neo (570 Вт)",
            "battery_model": "Pylontech US5000 (4.8 кВт·ч / 48 В)",
            "cable_length": 12.0,
            "ac_cable_length": 8.0,
            "inverter_efficiency": 0.92,
            "pv_system_efficiency": 0.78,
            "electricity_tariff_byn_kwh": 0.30,
            "project_lifetime_years": 15.0,
            "ac_loads": [
                {"name": "Холодильник", "power": 150.0, "hours_week": 84.0, "surge_factor": 5.0},
                {"name": "LED-освещение", "power": 180.0, "hours_week": 42.0, "surge_factor": 1.0},
                {"name": "Котел / циркуляция", "power": 120.0, "hours_week": 84.0, "surge_factor": 3.0},
                {"name": "ТВ / роутер AC", "power": 120.0, "hours_week": 35.0, "surge_factor": 1.2},
            ],
            "dc_loads": [
                {"name": "Телеком DC", "power": 30.0, "hours_week": 168.0, "surge_factor": 1.0}
            ],
        },
    ),
    ScenarioPreset(
        name="Телеком",
        description="48В телеком-объект: преимущественно DC-нагрузки, высокая автономия.",
        payload={
            "use_climate_data": True,
            "city": "Гомель",
            "month": "Октябрь",
            "relief_name": "Городская застройка (0.85)",
            "system_voltage": 48.0,
            "days_autonomy": 3.0,
            "panel_model": "Jinko Tiger Neo (570 Вт)",
            "battery_model": "Pylontech US5000 (4.8 кВт·ч / 48 В)",
            "cable_length": 15.0,
            "ac_cable_length": 3.0,
            "inverter_efficiency": 0.92,
            "pv_system_efficiency": 0.76,
            "electricity_tariff_byn_kwh": 0.35,
            "project_lifetime_years": 15.0,
            "ac_loads": [
                {"name": "Ноутбук / зарядка", "power": 65.0, "hours_week": 42.0, "surge_factor": 1.2}
            ],
            "dc_loads": [
                {"name": "Роутер", "power": 20.0, "hours_week": 168.0, "surge_factor": 1.0},
                {"name": "Коммутатор", "power": 35.0, "hours_week": 168.0, "surge_factor": 1.0},
                {"name": "Радиостанция", "power": 50.0, "hours_week": 84.0, "surge_factor": 1.5},
            ],
        },
    ),
    ScenarioPreset(
        name="Насос / скважина",
        description="Мощный пусковой насос + бытовые нагрузки, система 48 В.",
        payload={
            "use_climate_data": True,
            "city": "Минск",
            "month": "Июль",
            "relief_name": "Открытая равнина (1.00)",
            "system_voltage": 48.0,
            "days_autonomy": 1.0,
            "panel_model": "Jinko Tiger Neo (570 Вт)",
            "battery_model": "Pylontech US5000 (4.8 кВт·ч / 48 В)",
            "cable_length": 18.0,
            "ac_cable_length": 12.0,
            "inverter_efficiency": 0.93,
            "pv_system_efficiency": 0.78,
            "electricity_tariff_byn_kwh": 0.30,
            "project_lifetime_years": 15.0,
            "ac_loads": [
                {"name": "Скважинный насос", "power": 750.0, "hours_week": 7.0, "surge_factor": 4.0},
                {"name": "Холодильник", "power": 150.0, "hours_week": 84.0, "surge_factor": 5.0},
                {"name": "Освещение", "power": 120.0, "hours_week": 35.0, "surge_factor": 1.0},
            ],
            "dc_loads": [
                {"name": "Контроллер полива", "power": 15.0, "hours_week": 84.0, "surge_factor": 1.0}
            ],
        },
    ),
)


def preset_names() -> list[str]:
    return [preset.name for preset in PRESETS]


def get_preset(name: str) -> ScenarioPreset:
    for preset in PRESETS:
        if preset.name == name:
            return preset
    available = ", ".join(preset_names())
    raise KeyError(f"Неизвестный сценарий '{name}'. Доступны: {available}")

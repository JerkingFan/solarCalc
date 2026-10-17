"""Core engineering package for PV-Calc Pro."""

from core.cable import CableResult, calculate_cable_section
from core.calculator import SolarSystemCalculator
from core.climate import (
    CITY_CLIMATE,
    MONTHS,
    RELIEF_COEFFICIENTS,
    city_names,
    get_city_climate,
    get_min_design_temperature,
    get_monthly_psh,
    get_relief_coefficient,
    relief_names,
)
from core.database import (
    BATTERIES,
    CHARGE_CONTROLLERS,
    INVERTERS,
    SOLAR_PANELS,
    Battery,
    ChargeController,
    Inverter,
    SolarPanel,
    battery_names,
    controller_names,
    get_battery,
    get_controller,
    get_inverter,
    get_panel,
    inverter_names,
    panel_names,
)
from core.economics import build_bom, economic_summary
from core.presets import PRESETS, ScenarioPreset, get_preset, preset_names
from core.project import load_project, save_project
from core.protection import next_breaker_rating, recommended_protection

__all__ = [
    "BATTERIES",
    "CHARGE_CONTROLLERS",
    "CITY_CLIMATE",
    "INVERTERS",
    "MONTHS",
    "PRESETS",
    "RELIEF_COEFFICIENTS",
    "SOLAR_PANELS",
    "ScenarioPreset",
    "Battery",
    "CableResult",
    "ChargeController",
    "Inverter",
    "SolarPanel",
    "SolarSystemCalculator",
    "battery_names",
    "build_bom",
    "calculate_cable_section",
    "city_names",
    "controller_names",
    "economic_summary",
    "get_battery",
    "get_city_climate",
    "get_controller",
    "get_inverter",
    "get_min_design_temperature",
    "get_monthly_psh",
    "get_panel",
    "get_preset",
    "get_relief_coefficient",
    "inverter_names",
    "preset_names",
    "load_project",
    "next_breaker_rating",
    "panel_names",
    "recommended_protection",
    "relief_names",
    "save_project",
]

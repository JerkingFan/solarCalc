"""Structured equipment database for PV-Calc Pro.

Single source of truth for photovoltaic modules, batteries, charge controllers
and inverters used by the calculator and the UI.

All prices are engineering estimates in Belarusian rubles (BYN), midpoints of
the typical market range for renewable-energy suppliers.
"""

from dataclasses import dataclass
from typing import Literal

BatteryChemistry = Literal["LiFePO4", "GEL", "AGM", "Ni-Cd"]


@dataclass(frozen=True)
class SolarPanel:
    name: str
    power_w: float
    vmp_v: float
    voc_v: float
    imp_a: float
    isc_a: float
    technology: str
    temp_coeff_voc_percent_per_c: float = -0.28
    weight_kg: float = 0.0
    dimensions_mm: str = ""
    price_byn: float = 0.0


@dataclass(frozen=True)
class Battery:
    name: str
    capacity_ah: float
    voltage_v: float
    chemistry: BatteryChemistry
    max_charge_current_a: float
    max_discharge_current_a: float
    weight_kg: float = 0.0
    price_byn: float = 0.0


@dataclass(frozen=True)
class ChargeController:
    name: str
    charge_current_a: float
    max_input_voltage_v: float
    supported_system_voltages: tuple[int, ...]
    controller_type: str = "MPPT"
    efficiency: float = 0.98
    price_byn: float = 0.0


@dataclass(frozen=True)
class Inverter:
    name: str
    rated_power_w: float
    surge_power_w: float
    input_voltage_v: int
    efficiency: float = 0.90
    price_byn: float = 0.0


SOLAR_PANELS: tuple[SolarPanel, ...] = (
    # --- Базовая линейка (оставлена для совместимости со сценариями) ---
    SolarPanel(
        name="LONGi Hi-MO 6 (450 Вт)",
        power_w=450.0, vmp_v=34.5, voc_v=40.8, imp_a=13.05, isc_a=13.8,
        technology="HPBC N-type", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=20.8, dimensions_mm="1722x1134x30", price_byn=470.0,
    ),
    SolarPanel(
        name="Jinko Tiger Neo (570 Вт)",
        power_w=570.0, vmp_v=42.1, voc_v=50.6, imp_a=13.5, isc_a=14.4,
        technology="N-type TOPCon", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=27.5, dimensions_mm="2278x1134x30", price_byn=590.0,
    ),
    SolarPanel(
        name="Trina Vertex S+ (450 Вт)",
        power_w=450.0, vmp_v=34.0, voc_v=40.9, imp_a=13.24, isc_a=14.0,
        technology="N-type Dual Glass", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=21.0, dimensions_mm="1762x1134x30", price_byn=460.0,
    ),
    SolarPanel(
        name="JA Solar DeepBlue 4.0 Pro (450 Вт)",
        power_w=450.0, vmp_v=33.95, voc_v=40.8, imp_a=13.24, isc_a=14.0,
        technology="N-type Bycium+", temp_coeff_voc_percent_per_c=-0.25,
        weight_kg=21.5, dimensions_mm="1722x1134x30", price_byn=450.0,
    ),
    SolarPanel(
        name="МС-50-4 (Базовая)",
        power_w=50.0, vmp_v=17.5, voc_v=21.6, imp_a=2.85, isc_a=3.1,
        technology="Mono-crystalline", temp_coeff_voc_percent_per_c=-0.32,
        weight_kg=4.2, dimensions_mm="670x540x25", price_byn=150.0,
    ),
    # --- Новый каталог Tier 1 ---
    SolarPanel(
        name="LONGi Hi-MO 6 Explorer (430 Вт, HPBC Full Black)",
        power_w=430.0, vmp_v=33.12, voc_v=39.14, imp_a=12.99, isc_a=13.75,
        technology="HPBC Full Black", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=20.5, dimensions_mm="1722x1134x30", price_byn=410.0,
    ),
    SolarPanel(
        name="LONGi Hi-MO 6 Scientist (450 Вт, HPBC)",
        power_w=450.0, vmp_v=34.5, voc_v=40.8, imp_a=13.05, isc_a=13.8,
        technology="HPBC", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=21.0, dimensions_mm="1722x1134x30", price_byn=460.0,
    ),
    SolarPanel(
        name="LONGi Hi-MO 5 (540 Вт, Mono-PERC Half-Cut)",
        power_w=540.0, vmp_v=31.45, voc_v=37.35, imp_a=17.17, isc_a=18.1,
        technology="Mono-PERC Half-Cut", temp_coeff_voc_percent_per_c=-0.28,
        weight_kg=27.0, dimensions_mm="2256x1133x35", price_byn=505.0,
    ),
    SolarPanel(
        name="LONGi Hi-MO 7 (610 Вт, HPDC Bifacial)",
        power_w=610.0, vmp_v=42.10, voc_v=50.5, imp_a=14.49, isc_a=15.3,
        technology="HPDC Bifacial", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=30.0, dimensions_mm="2382x1134x30", price_byn=650.0,
    ),
    SolarPanel(
        name="Jinko Tiger Neo 54HL4V (430 Вт, TOPCon)",
        power_w=430.0, vmp_v=32.79, voc_v=39.34, imp_a=13.11, isc_a=13.85,
        technology="N-type TOPCon", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=21.0, dimensions_mm="1722x1134x30", price_byn=420.0,
    ),
    SolarPanel(
        name="Jinko Tiger Neo 72HL4V (580 Вт, TOPCon)",
        power_w=580.0, vmp_v=42.85, voc_v=51.41, imp_a=13.54, isc_a=14.3,
        technology="N-type TOPCon", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=27.8, dimensions_mm="2278x1134x30", price_byn=570.0,
    ),
    SolarPanel(
        name="Trina Vertex S+ (440 Вт, N-type Dual Glass)",
        power_w=440.0, vmp_v=33.6, voc_v=41.6, imp_a=13.1, isc_a=13.9,
        technology="N-type Dual Glass", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=21.0, dimensions_mm="1762x1134x30", price_byn=435.0,
    ),
    SolarPanel(
        name="Trina Vertex DE21 (650 Вт, Mono-PERC)",
        power_w=650.0, vmp_v=37.6, voc_v=45.0, imp_a=17.3, isc_a=18.2,
        technology="Mono-PERC 210mm", temp_coeff_voc_percent_per_c=-0.28,
        weight_kg=33.5, dimensions_mm="2384x1303x35", price_byn=685.0,
    ),
    SolarPanel(
        name="JA Solar DeepBlue 4.0 Pro (440 Вт, Bycium+)",
        power_w=440.0, vmp_v=33.5, voc_v=39.5, imp_a=13.1, isc_a=13.9,
        technology="N-type Bycium+", temp_coeff_voc_percent_per_c=-0.25,
        weight_kg=21.5, dimensions_mm="1722x1134x30", price_byn=430.0,
    ),
    SolarPanel(
        name="JA Solar DeepBlue 3.0 (545 Вт, PERC)",
        power_w=545.0, vmp_v=41.8, voc_v=49.8, imp_a=13.04, isc_a=13.8,
        technology="PERC Multi-Busbar", temp_coeff_voc_percent_per_c=-0.28,
        weight_kg=28.0, dimensions_mm="2278x1134x30", price_byn=515.0,
    ),
    SolarPanel(
        name="Canadian Solar TopHiKu6 (450 Вт, TOPCon)",
        power_w=450.0, vmp_v=33.4, voc_v=39.6, imp_a=13.47, isc_a=14.2,
        technology="N-type TOPCon", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=21.2, dimensions_mm="1722x1134x30", price_byn=450.0,
    ),
    SolarPanel(
        name="Qcells Q.PEAK DUO ML-G10 (410 Вт)",
        power_w=410.0, vmp_v=31.0, voc_v=37.2, imp_a=13.23, isc_a=14.0,
        technology="Q.ANTUM Half-Cell", temp_coeff_voc_percent_per_c=-0.26,
        weight_kg=20.5, dimensions_mm="1717x1134x32", price_byn=475.0,
    ),
    SolarPanel(
        name="REC Alpha Pure (410 Вт, HJT)",
        power_w=410.0, vmp_v=34.0, voc_v=40.5, imp_a=12.06, isc_a=12.8,
        technology="HJT", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=20.5, dimensions_mm="1730x1118x30", price_byn=615.0,
    ),
    SolarPanel(
        name="Aiko Neostar (450 Вт, ABC Full Black)",
        power_w=450.0, vmp_v=33.8, voc_v=40.2, imp_a=13.31, isc_a=14.0,
        technology="ABC N-type", temp_coeff_voc_percent_per_c=-0.24,
        weight_kg=21.5, dimensions_mm="1722x1134x30", price_byn=555.0,
    ),
)

BATTERIES: tuple[Battery, ...] = (
    # --- Базовая линейка ---
    Battery(
        name="Pylontech US5000 (4.8 кВт·ч / 48 В)",
        capacity_ah=100.0, voltage_v=48.0, chemistry="LiFePO4",
        max_charge_current_a=50.0, max_discharge_current_a=100.0,
        weight_kg=41.0, price_byn=4450.0,
    ),
    Battery(
        name="BYD Battery-Box Premium LVS 4.0 (4.0 кВт·ч / 48 В)",
        capacity_ah=83.0, voltage_v=48.0, chemistry="LiFePO4",
        max_charge_current_a=65.0, max_discharge_current_a=65.0,
        weight_kg=45.0, price_byn=4850.0,
    ),
    Battery(
        name="Гелевая Delta GOR 120Ач (24 В)",
        capacity_ah=120.0, voltage_v=24.0, chemistry="GEL",
        max_charge_current_a=30.0, max_discharge_current_a=120.0,
        weight_kg=38.0, price_byn=1200.0,
    ),
    Battery(
        name="Leoch LDC 200Ач (12 В)",
        capacity_ah=200.0, voltage_v=12.0, chemistry="GEL",
        max_charge_current_a=40.0, max_discharge_current_a=200.0,
        weight_kg=58.0, price_byn=1050.0,
    ),
    Battery(
        name="Ventura GPL 100Ач (12 В) AGM",
        capacity_ah=100.0, voltage_v=12.0, chemistry="AGM",
        max_charge_current_a=30.0, max_discharge_current_a=150.0,
        weight_kg=31.0, price_byn=650.0,
    ),
    # --- Новый каталог АКБ и СНЭ ---
    Battery(
        name="Pylontech US2000C (2.4 кВт·ч / 48 В)",
        capacity_ah=50.0, voltage_v=48.0, chemistry="LiFePO4",
        max_charge_current_a=25.0, max_discharge_current_a=50.0,
        weight_kg=24.0, price_byn=2450.0,
    ),
    Battery(
        name="Dyness Powerbox Pro (5.12 кВт·ч / 48 В)",
        capacity_ah=100.0, voltage_v=48.0, chemistry="LiFePO4",
        max_charge_current_a=50.0, max_discharge_current_a=100.0,
        weight_kg=52.0, price_byn=4700.0,
    ),
    Battery(
        name="Delta GOR 12-100 (GEL, 100 Ач, 12 В)",
        capacity_ah=100.0, voltage_v=12.0, chemistry="GEL",
        max_charge_current_a=25.0, max_discharge_current_a=100.0,
        weight_kg=33.0, price_byn=915.0,
    ),
    Battery(
        name="Delta DNG 12-200 (GEL, 200 Ач, 12 В)",
        capacity_ah=200.0, voltage_v=12.0, chemistry="GEL",
        max_charge_current_a=40.0, max_discharge_current_a=200.0,
        weight_kg=60.0, price_byn=1750.0,
    ),
    Battery(
        name="Leoch LDC 12-150 (GEL Deep Cycle, 150 Ач, 12 В)",
        capacity_ah=150.0, voltage_v=12.0, chemistry="GEL",
        max_charge_current_a=30.0, max_discharge_current_a=150.0,
        weight_kg=45.0, price_byn=1325.0,
    ),
    Battery(
        name="Exide Sonnenschein A500 (AGM/Dryfit, 100 Ач, 12 В)",
        capacity_ah=100.0, voltage_v=12.0, chemistry="AGM",
        max_charge_current_a=30.0, max_discharge_current_a=100.0,
        weight_kg=38.0, price_byn=1550.0,
    ),
    Battery(
        name="Сатурн НК-125 (Ni-Cd комплект, 125 Ач, 12 В)",
        capacity_ah=125.0, voltage_v=12.0, chemistry="Ni-Cd",
        max_charge_current_a=25.0, max_discharge_current_a=125.0,
        weight_kg=65.0, price_byn=3500.0,
    ),
)

CHARGE_CONTROLLERS: tuple[ChargeController, ...] = (
    # --- Базовая линейка ---
    ChargeController(
        name="EPEVER Tracer-AN 30А 100В MPPT",
        charge_current_a=30.0, max_input_voltage_v=100.0,
        supported_system_voltages=(12, 24), efficiency=0.98, price_byn=480.0,
    ),
    ChargeController(
        name="Victron SmartSolar MPPT 100/50",
        charge_current_a=50.0, max_input_voltage_v=100.0,
        supported_system_voltages=(12, 24), efficiency=0.98, price_byn=1100.0,
    ),
    ChargeController(
        name="EPEVER Tracer-AN 50А 150В MPPT",
        charge_current_a=50.0, max_input_voltage_v=150.0,
        supported_system_voltages=(12, 24, 48), efficiency=0.98, price_byn=700.0,
    ),
    ChargeController(
        name="Victron SmartSolar MPPT 150/60",
        charge_current_a=60.0, max_input_voltage_v=150.0,
        supported_system_voltages=(12, 24, 48), efficiency=0.98, price_byn=1500.0,
    ),
    ChargeController(
        name="OutBack FLEXmax FM80 150В MPPT",
        charge_current_a=80.0, max_input_voltage_v=150.0,
        supported_system_voltages=(12, 24, 48), efficiency=0.97, price_byn=2100.0,
    ),
    ChargeController(
        name="Victron SmartSolar MPPT 250/100",
        charge_current_a=100.0, max_input_voltage_v=250.0,
        supported_system_voltages=(24, 48), efficiency=0.98, price_byn=2950.0,
    ),
    # --- Новый каталог MPPT / PWM ---
    ChargeController(
        name="Morningstar SunSaver MPPT 15L (12/24В, 75В)",
        charge_current_a=15.0, max_input_voltage_v=75.0,
        supported_system_voltages=(12, 24), efficiency=0.98, price_byn=800.0,
    ),
    ChargeController(
        name="Morningstar ProStar PS-15M (PWM, 15А)",
        charge_current_a=15.0, max_input_voltage_v=50.0,
        supported_system_voltages=(12, 24), controller_type="PWM",
        efficiency=0.97, price_byn=660.0,
    ),
    ChargeController(
        name="Victron SmartSolar MPPT 75/15",
        charge_current_a=15.0, max_input_voltage_v=75.0,
        supported_system_voltages=(12, 24), efficiency=0.98, price_byn=455.0,
    ),
    ChargeController(
        name="Victron SmartSolar MPPT 150/45",
        charge_current_a=45.0, max_input_voltage_v=150.0,
        supported_system_voltages=(12, 24, 48), efficiency=0.98, price_byn=1435.0,
    ),
    ChargeController(
        name="Epever Tracer 3210AN (30А, 100В)",
        charge_current_a=30.0, max_input_voltage_v=100.0,
        supported_system_voltages=(12, 24, 48), efficiency=0.97, price_byn=380.0,
    ),
    ChargeController(
        name="Epever Tracer 5415AN (50А, 150В)",
        charge_current_a=50.0, max_input_voltage_v=150.0,
        supported_system_voltages=(12, 24, 48), efficiency=0.97, price_byn=805.0,
    ),
)

INVERTERS: tuple[Inverter, ...] = (
    # --- Базовая линейка ---
    Inverter(
        name="EPEVER IPower-Plus 1000Вт 12В",
        rated_power_w=1000.0, surge_power_w=2000.0, input_voltage_v=12,
        efficiency=0.90, price_byn=900.0,
    ),
    Inverter(
        name="Victron Phoenix 24/1200 VE.Direct",
        rated_power_w=1000.0, surge_power_w=2200.0, input_voltage_v=24,
        efficiency=0.92, price_byn=1500.0,
    ),
    Inverter(
        name="EPEVER IPower-Plus 2000Вт 24В",
        rated_power_w=2000.0, surge_power_w=4000.0, input_voltage_v=24,
        efficiency=0.91, price_byn=1300.0,
    ),
    Inverter(
        name="Victron Phoenix 48/3000 VE.Direct",
        rated_power_w=2400.0, surge_power_w=6000.0, input_voltage_v=48,
        efficiency=0.94, price_byn=3400.0,
    ),
    Inverter(
        name="Must PV1800 48В 5000Вт",
        rated_power_w=5000.0, surge_power_w=10000.0, input_voltage_v=48,
        efficiency=0.93, price_byn=2800.0,
    ),
    # --- Новый каталог (однофазные автономные / гибридные) ---
    Inverter(
        name="Victron Phoenix 12/1200 (автономный)",
        rated_power_w=1000.0, surge_power_w=2200.0, input_voltage_v=12,
        efficiency=0.92, price_byn=1400.0,
    ),
    Inverter(
        name="Victron MultiPlus-II 48/3000/35-32 (гибрид)",
        rated_power_w=2400.0, surge_power_w=6000.0, input_voltage_v=48,
        efficiency=0.95, price_byn=4050.0,
    ),
    Inverter(
        name="GoodWe GW5000-ES-20 (гибрид, 5 кВт)",
        rated_power_w=5000.0, surge_power_w=7500.0, input_voltage_v=48,
        efficiency=0.95, price_byn=4450.0,
    ),
    Inverter(
        name="Deye SUN-5K-SG04LP1 (гибрид, 5 кВт)",
        rated_power_w=5000.0, surge_power_w=10000.0, input_voltage_v=48,
        efficiency=0.95, price_byn=4650.0,
    ),
    Inverter(
        name="Solis RHI-5K-48ES-5G (гибрид, 5 кВт)",
        rated_power_w=5000.0, surge_power_w=8000.0, input_voltage_v=48,
        efficiency=0.95, price_byn=4350.0,
    ),
)


def panel_names() -> list[str]:
    return [item.name for item in SOLAR_PANELS]


def battery_names() -> list[str]:
    return [item.name for item in BATTERIES]


def controller_names() -> list[str]:
    return [item.name for item in CHARGE_CONTROLLERS]


def inverter_names() -> list[str]:
    return [item.name for item in INVERTERS]


def _get_by_name(items, name: str, kind: str):
    for item in items:
        if item.name == name:
            return item
    available = ", ".join(item.name for item in items)
    raise KeyError(f"Неизвестный элемент '{name}' ({kind}). Доступны: {available}")


def get_panel(name: str) -> SolarPanel:
    return _get_by_name(SOLAR_PANELS, name, "солнечная панель")


def get_battery(name: str) -> Battery:
    return _get_by_name(BATTERIES, name, "аккумулятор")


def get_controller(name: str) -> ChargeController:
    return _get_by_name(CHARGE_CONTROLLERS, name, "контроллер")


def get_inverter(name: str) -> Inverter:
    return _get_by_name(INVERTERS, name, "инвертор")

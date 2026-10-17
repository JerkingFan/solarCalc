"""BOM and economics for PV-Calc Pro. All prices in Belarusian rubles (BYN)."""

from __future__ import annotations

from typing import Any

from core.database import get_battery, get_controller, get_inverter, get_panel

# Розничные цены на медный кабель в Беларуси, BYN за метр (по сечениям).
CABLE_PRICE_BYN_PER_M: tuple[tuple[float, float], ...] = (
    (1.5, 3.5),
    (2.5, 5.0),
    (4.0, 7.5),
    (6.0, 10.0),
    (10.0, 17.0),
    (16.0, 25.0),
    (25.0, 45.0),
    (35.0, 60.0),
    (50.0, 85.0),
    (70.0, 110.0),
    (95.0, 145.0),
    (120.0, 180.0),
    (150.0, 220.0),
    (185.0, 270.0),
    (240.0, 340.0),
)

# Цены аппаратов защиты, BYN.
PROTECTION_PRICE_BYN = {
    "pv_array_breaker": 60.0,
    "controller_battery_breaker": 70.0,
    "battery_main_breaker": 140.0,
    "ac_output_breaker": 45.0,
    "ac_rcd": 220.0,
}

MISC_INSTALLATION_RATIO = 0.12


def _fmt_money(value: float) -> float:
    return round(float(value), 2)


def _cable_price_per_meter(section_mm2: float) -> float:
    section = float(section_mm2)
    price = CABLE_PRICE_BYN_PER_M[0][1]
    for max_section, section_price in CABLE_PRICE_BYN_PER_M:
        if section <= max_section:
            return section_price
        price = section_price
    return price


def _bom_item(
    element: str,
    model: str,
    quantity: float,
    unit: str,
    unit_price_byn: float,
    note: str = "",
) -> dict[str, Any]:
    quantity = float(quantity)
    unit_price_byn = float(unit_price_byn)
    return {
        "element": element,
        "model": model,
        "quantity": quantity,
        "unit": unit,
        "unit_price_byn": _fmt_money(unit_price_byn),
        "total_byn": _fmt_money(quantity * unit_price_byn),
        "note": note,
    }


def build_bom(input_data: dict[str, Any], results: dict[str, Any]) -> list[dict[str, Any]]:
    panel = get_panel(str(results.get("panel_model")))
    battery = get_battery(str(results.get("battery_model")))
    controller = get_controller(str(results.get("controller_model")))
    inverter = get_inverter(str(results.get("inverter_model")))

    cable = results.get("cable")
    dc_length_m = float(getattr(cable, "length_m", input_data.get("cable_length", 0.0)))
    ac_length_m = float(input_data.get("ac_cable_length", 5.0))
    dc_cable_m = max(0.0, dc_length_m) * 2.0
    ac_cable_m = max(0.0, ac_length_m) * 3.0

    protection = dict(results.get("protection", {}))
    bom = [
        _bom_item(
            "Солнечный модуль",
            panel.name,
            float(results.get("nm_modules", 0)),
            "шт.",
            panel.price_byn,
            f"P={panel.power_w:.0f} Вт; Voc={panel.voc_v:.1f} В",
        ),
        _bom_item(
            "Аккумуляторная батарея",
            battery.name,
            float(results.get("battery_count", 0)),
            "шт.",
            battery.price_byn,
            f"{results.get('battery_series_count', 0)}S×{results.get('battery_parallel_count', 0)}P; {battery.chemistry}",
        ),
        _bom_item(
            "MPPT-контроллер",
            controller.name,
            1.0,
            "шт.",
            controller.price_byn,
            f"I_charge={controller.charge_current_a:.0f} А; Vin,max={controller.max_input_voltage_v:.0f} В",
        ),
        _bom_item(
            "Инвертор DC/AC",
            inverter.name,
            1.0,
            "шт.",
            inverter.price_byn,
            f"Pnom={inverter.rated_power_w:.0f} Вт; Psurge={inverter.surge_power_w:.0f} Вт",
        ),
        _bom_item(
            "Кабель DC",
            f"Cu {float(results.get('cable_section_mm2', 0.0)):g} мм²",
            dc_cable_m,
            "м",
            _cable_price_per_meter(float(results.get("cable_section_mm2", 1.5))),
            f"Трасса {dc_length_m:.1f} м; учтены 2 жилы",
        ),
        _bom_item(
            "Кабель AC",
            f"Cu {float(results.get('ac_cable_section_mm2', 0.0)):g} мм²",
            ac_cable_m,
            "м",
            _cable_price_per_meter(float(results.get("ac_cable_section_mm2", 1.5))),
            f"Трасса {ac_length_m:.1f} м; учтены L/N/PE",
        ),
        _bom_item(
            "Автомат PV-поля",
            f"DC MCB {protection.get('pv_array_breaker_a', '—')} А",
            1.0,
            "шт.",
            PROTECTION_PRICE_BYN["pv_array_breaker"],
            "Защита и коммутация PV-поля",
        ),
        _bom_item(
            "Автомат контроллер-АКБ",
            f"DC MCB {protection.get('controller_battery_breaker_a', '—')} А",
            1.0,
            "шт.",
            PROTECTION_PRICE_BYN["controller_battery_breaker"],
            "Защита цепи заряда",
        ),
        _bom_item(
            "Главный автомат АКБ",
            f"DC MCB {protection.get('battery_main_breaker_a', '—')} А",
            1.0,
            "шт.",
            PROTECTION_PRICE_BYN["battery_main_breaker"],
            "Защита батареи и инвертора",
        ),
        _bom_item(
            "Автомат AC-выхода",
            f"AC MCB {protection.get('ac_output_breaker_a', '—')} А",
            1.0,
            "шт.",
            PROTECTION_PRICE_BYN["ac_output_breaker"],
            "Защита линии 230 В",
        ),
        _bom_item(
            "УЗО AC",
            str(protection.get("ac_rcd", "УЗО 30 мА")),
            1.0,
            "шт.",
            PROTECTION_PRICE_BYN["ac_rcd"],
            "Защита от утечек на AC-выходе",
        ),
    ]

    equipment_subtotal = sum(item["total_byn"] for item in bom)
    misc_price = equipment_subtotal * MISC_INSTALLATION_RATIO
    bom.append(
        _bom_item(
            "Монтаж и материалы",
            "Крепеж, клеммы, шины, корпус, расходники",
            1.0,
            "компл.",
            misc_price,
            f"{MISC_INSTALLATION_RATIO:.0%} от стоимости оборудования",
        )
    )
    return bom


def economic_summary(
    input_data: dict[str, Any],
    results: dict[str, Any],
    bom: list[dict[str, Any]],
) -> dict[str, Any]:
    equipment_subtotal = sum(
        float(item["total_byn"])
        for item in bom
        if item.get("element") != "Монтаж и материалы"
    )
    capex = sum(float(item["total_byn"]) for item in bom)
    annual_energy_kwh = float(results.get("daily_energy_wh", 0.0)) * 365.0 / 1000.0
    lifetime_years = max(1.0, float(input_data.get("project_lifetime_years", 15.0)))
    tariff = max(0.0, float(input_data.get("electricity_tariff_byn_kwh", 0.30)))
    lifetime_energy_kwh = annual_energy_kwh * lifetime_years
    cost_per_kwh = capex / lifetime_energy_kwh if lifetime_energy_kwh > 0 else 0.0
    annual_savings = annual_energy_kwh * tariff
    payback_years = capex / annual_savings if annual_savings > 0 else float("inf")

    return {
        "equipment_subtotal_byn": _fmt_money(equipment_subtotal),
        "capex_byn": _fmt_money(capex),
        "annual_energy_kwh": round(annual_energy_kwh, 2),
        "lifetime_years": lifetime_years,
        "electricity_tariff_byn_kwh": tariff,
        "lifetime_energy_kwh": round(lifetime_energy_kwh, 2),
        "cost_per_kwh_byn": round(cost_per_kwh, 4),
        "annual_savings_byn": _fmt_money(annual_savings),
        "simple_payback_years": round(payback_years, 2) if payback_years != float("inf") else "∞",
    }

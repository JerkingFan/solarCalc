"""Time-domain simulation and chart data for PV-Calc Pro.

Provides simplified hourly and monthly energy-balance models that can be
plotted with implot. The models are intentionally simple (clear-sky PV curve,
average daily load) to keep the UI responsive and dependency-free.
"""

from __future__ import annotations

from math import pi, sin
from typing import Any

from core.climate import MONTHS, get_monthly_psh


def _normalize_loads(loads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert mission/ui load rows to a canonical dict form."""
    out: list[dict[str, Any]] = []
    for item in loads:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            out.append(
                {
                    "name": str(item[0]),
                    "power": float(item[1]),
                    "hours_week": float(item[2]),
                    "surge_factor": float(item[3]) if len(item) > 3 else 1.0,
                }
            )
    return out


def _daily_energy_wh(loads: list[Any]) -> float:
    return sum(
        float(load.get("power", 0.0)) * float(load.get("hours_week", 0.0)) / 7.0
        for load in _normalize_loads(loads)
    )


def simulate_day(
    payload: dict[str, Any],
    results: dict[str, Any],
    daylength_h: float = 12.0,
    initial_soc: float = 0.7,
) -> dict[str, Any]:
    """Simulate one clear day hour-by-hour.

    Returns hours (0..23), pv_power_w, load_power_w, battery_soc (0..1),
    net_power_w and a shortfall flag.
    """
    hours = list(range(24))
    pv_actual_w = float(results.get("pv_actual_w", 0.0))
    psh = float(results.get("psh", payload.get("psh", 1.0)))
    effective_pv_efficiency = float(
        results.get("effective_pv_efficiency", payload.get("pv_system_efficiency", 0.78))
    )

    ac_daily_wh = _daily_energy_wh(payload.get("ac_loads", [])) / max(
        float(payload.get("inverter_efficiency", results.get("inverter_efficiency", 0.88))), 0.01
    )
    dc_daily_wh = _daily_energy_wh(payload.get("dc_loads", []))
    daily_load_wh = ac_daily_wh + dc_daily_wh

    battery_energy_wh = float(results.get("battery_energy_actual_wh", 0.0))
    if battery_energy_wh <= 0:
        battery_energy_wh = daily_load_wh * float(payload.get("days_autonomy", 1.0))

    # Clear-sky sine curve scaled to daily PSH
    sunrise = (24.0 - daylength_h) / 2.0
    sunset = sunrise + daylength_h
    sine_integral = 2.0 * daylength_h / pi
    scale = (pv_actual_w * psh * effective_pv_efficiency) / max(sine_integral, 1e-6)

    pv_power: list[float] = []
    load_power: list[float] = []
    net_power: list[float] = []
    battery_soc: list[float] = []
    soc = max(0.0, min(1.0, initial_soc))
    total_load_wh = 0.0
    total_pv_wh = 0.0
    shortfall_hours = 0

    for h in hours:
        if sunrise <= h <= sunset:
            raw = sin(pi * (h - sunrise) / daylength_h)
        else:
            raw = 0.0
        pv = max(0.0, raw * scale)
        load = daily_load_wh / 24.0  # averaged flat profile
        net = pv - load
        total_pv_wh += pv
        total_load_wh += load
        if battery_energy_wh > 0:
            soc += net / battery_energy_wh
            soc = max(0.0, min(1.0, soc))
        if pv < load:
            shortfall_hours += 1
        pv_power.append(pv)
        load_power.append(load)
        net_power.append(net)
        battery_soc.append(soc)

    return {
        "hours": hours,
        "pv_power_w": pv_power,
        "load_power_w": load_power,
        "net_power_w": net_power,
        "battery_soc": battery_soc,
        "total_pv_wh": total_pv_wh,
        "total_load_wh": total_load_wh,
        "shortfall_hours": shortfall_hours,
        "battery_energy_wh": battery_energy_wh,
    }


def monthly_energy_data(
    payload: dict[str, Any],
    results: dict[str, Any],
) -> dict[str, Any]:
    """Return monthly PV production and consumption for the selected city."""
    city = str(payload.get("city", "Минск"))
    pv_actual_w = float(results.get("pv_actual_w", 0.0))
    effective_pv_efficiency = float(
        results.get("effective_pv_efficiency", payload.get("pv_system_efficiency", 0.78))
    )
    ac_daily_wh = _daily_energy_wh(payload.get("ac_loads", [])) / max(
        float(payload.get("inverter_efficiency", results.get("inverter_efficiency", 0.88))), 0.01
    )
    dc_daily_wh = _daily_energy_wh(payload.get("dc_loads", []))
    daily_load_wh = ac_daily_wh + dc_daily_wh

    months = list(MONTHS)
    production_kwh: list[float] = []
    consumption_kwh: list[float] = []
    for month in months:
        try:
            psh = get_monthly_psh(city, month)
        except KeyError:
            psh = 0.0
        prod = pv_actual_w * psh * effective_pv_efficiency / 1000.0
        production_kwh.append(prod)
        consumption_kwh.append(daily_load_wh / 1000.0)

    return {
        "months": months,
        "production_kwh": production_kwh,
        "consumption_kwh": consumption_kwh,
        "city": city,
    }

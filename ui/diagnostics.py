"""Engineering diagnostics for manually selected components.

Diagnostics analyse the calculated system and the user's manual component choices
(panel, battery, inverter, controller, cable). Each item has a level, a human
readable message, the formula/block it belongs to and a recommendation tooltip.
"""

from __future__ import annotations

from typing import Any

from core.cable import AMPACITY_A


def _fmt(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def compute_diagnostics(state, results: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of diagnostic items for the inspector and the main UI."""
    diagnostics: list[dict[str, Any]] = []
    if not results:
        return diagnostics

    payload = state.calculation_payload() if hasattr(state, "calculation_payload") else {}
    system_voltage = float(results.get("system_voltage", payload.get("system_voltage", 0.0)))

    # --- Energy / battery block ------------------------------------------------
    daily_energy = float(results.get("daily_energy_wh", 0.0))
    dod = float(results.get("battery_dod", 0.5))
    battery_chemistry = str(results.get("battery_chemistry", ""))
    if battery_chemistry == "AGM" and dod > 0.50:
        diagnostics.append(
            {
                "level": "warning",
                "block": "battery",
                "message": "Глубина разряда AGM превышает безопасные 50%.",
                "recommendation": "Для AGM ограничьте DoD 50% или выберите GEL/LiFePO4 с более глубоким разрядом.",
            }
        )
    if daily_energy <= 0:
        diagnostics.append(
            {
                "level": "critical",
                "block": "energy",
                "message": "Суточное энергопотребление равно нулю.",
                "recommendation": "Добавьте хотя бы одну AC или DC нагрузку.",
            }
        )

    # --- PV array / controller block ------------------------------------------
    pv_cold_voc = float(results.get("pv_cold_string_voc", 0.0))
    controller_max_v = float(results.get("controller_max_input_voltage", 0.0))
    controller_current = float(results.get("controller_current", 0.0))
    controller_required = float(results.get("controller_required_current", 0.0))

    if controller_max_v > 0 and pv_cold_voc > controller_max_v:
        diagnostics.append(
            {
                "level": "critical",
                "block": "string",
                "message": f"Voc стринга ({_fmt(pv_cold_voc, 1)} В) превышает максимум MPPT ({_fmt(controller_max_v, 0)} В).",
                "recommendation": "Уменьшите число модулей в стринге, выберите контроллер с более высоким Vin max или повысьте Tmin.",
            }
        )
    elif controller_max_v > 0 and pv_cold_voc > controller_max_v * 0.95:
        diagnostics.append(
            {
                "level": "warning",
                "block": "string",
                "message": f"Voc стринга ({_fmt(pv_cold_voc, 1)} В) близок к пределу MPPT.",
                "recommendation": "Оставьте запас ≥5% по входному напряжению контроллера на случай холодных пиков.",
            }
        )

    if controller_current < controller_required:
        diagnostics.append(
            {
                "level": "critical",
                "block": "controller",
                "message": f"Ток контроллера ({_fmt(controller_current, 0)} А) меньше требуемого ({_fmt(controller_required, 1)} А).",
                "recommendation": "Выберите контроллер большего номинала или уменьшите мощность PV-поля.",
            }
        )

    if not state.auto_controller and payload.get("controller_model"):
        supported = results.get("controller_supported_voltages", [])
        if system_voltage and system_voltage not in supported:
            diagnostics.append(
                {
                    "level": "critical",
                    "block": "controller",
                    "message": f"Контроллер не поддерживает системное напряжение {system_voltage:.0f} В.",
                    "recommendation": "Выберите контроллер из списка с поддержкой данного напряжения или включите автовыбор.",
                }
            )

    # --- Inverter block --------------------------------------------------------
    inverter_rated = float(results.get("inverter_rated_w", 0.0))
    inverter_surge = float(results.get("inverter_surge_w", 0.0))
    req_cont = float(results.get("inverter_required_continuous_w", 0.0))
    req_surge = float(results.get("inverter_required_surge_w", 0.0))
    inverter_input_v = int(results.get("inverter_input_voltage", 0))

    if inverter_rated < req_cont:
        diagnostics.append(
            {
                "level": "critical",
                "block": "inverter",
                "message": f"Номинал инвертора ({_fmt(inverter_rated, 0)} Вт) ниже требуемой непрерывной ({_fmt(req_cont, 0)} Вт).",
                "recommendation": "Выберите инвертор большей мощности или уменьшите суммарную мощность AC-нагрузок.",
            }
        )
    if inverter_surge < req_surge:
        diagnostics.append(
            {
                "level": "critical",
                "block": "inverter",
                "message": f"Пик инвертора ({_fmt(inverter_surge, 0)} Вт) ниже пусковой ({_fmt(req_surge, 0)} Вт).",
                "recommendation": "Увеличьте номинал инвертора либо снизьте пусковые токи нагрузок (например, холодильник/насос).",
            }
        )
    if system_voltage and inverter_input_v != system_voltage:
        diagnostics.append(
            {
                "level": "critical",
                "block": "inverter",
                "message": f"Инвертор рассчитан на {inverter_input_v} В, а система — на {system_voltage:.0f} В.",
                "recommendation": "Выберите инвертор с тем же входным DC-напряжением, что и система.",
            }
        )

    # --- Cable blocks ----------------------------------------------------------
    for prefix, label, block in (
        ("cable", "DC", "cable"),
        ("ac_cable", "AC", "ac_cable"),
    ):
        section = float(results.get(f"{prefix}_section_mm2", 0.0))
        required = float(results.get(f"{prefix}_required_section_mm2", 0.0))
        current = float(results.get("total_panel_current" if prefix == "cable" else "ac_output_current_a", 0.0))
        drop_percent = float(results.get(f"{prefix}_voltage_drop_percent", 0.0))

        if section > 0 and required > 0 and section < required:
            diagnostics.append(
                {
                    "level": "critical",
                    "block": block,
                    "message": f"{label}-кабель {_fmt(section, 1)} мм² меньше требуемого {_fmt(required, 1)} мм².",
                    "recommendation": f"Выберите сечение не менее {_fmt(required, 1)} мм² или увеличьте системное напряжение.",
                }
            )
        if current > 0 and section in AMPACITY_A and current * 1.25 > AMPACITY_A[section]:
            diagnostics.append(
                {
                    "level": "critical",
                    "block": block,
                    "message": f"{label}-кабель {_fmt(section, 1)} мм² недопустим для тока {_fmt(current, 1)} А по нагреву ПУЭ.",
                    "recommendation": f"Увеличьте сечение до значения с длительно допустимым током ≥ {_fmt(current*1.25, 1)} А.",
                }
            )
        if drop_percent > 2.5:
            diagnostics.append(
                {
                    "level": "warning",
                    "block": block,
                    "message": f"Высокое падение напряжения в {label}-кабеле ({_fmt(drop_percent, 2)}%).",
                    "recommendation": "Рекомендуется увеличить сечение на одну ступень или сократить длину трассы.",
                }
            )

    # --- Battery charge current ------------------------------------------------
    pv_charge_current = float(results.get("total_panel_current", 0.0))
    battery_max_charge = float(results.get("battery_max_charge_current", 0.0))
    # Charge current is shared only between PARALLEL strings, not all batteries.
    battery_parallel_count = max(1, int(results.get("battery_parallel_count", 1)))
    if battery_max_charge > 0 and pv_charge_current > battery_max_charge * battery_parallel_count:
        diagnostics.append(
            {
                "level": "warning",
                "block": "battery",
                "message": f"Ток заряда ({_fmt(pv_charge_current, 1)} А) превышает допустимый для АКБ.",
                "recommendation": "Увеличьте число параллельных батарей или ограничьте ток контроллера.",
            }
        )

    # --- Cross-component compatibility -----------------------------------------
    # Battery discharge power vs inverter demand.
    battery_max_discharge = float(results.get("battery_max_discharge_current", 0.0))
    battery_parallel_count = max(1, int(results.get("battery_parallel_count", 1)))
    if battery_max_discharge > 0 and system_voltage > 0:
        battery_discharge_power = battery_max_discharge * battery_parallel_count * system_voltage
        if battery_discharge_power < req_cont:
            diagnostics.append(
                {
                    "level": "critical",
                    "block": "battery",
                    "message": (
                        f"Батарея не вытягивает инвертор: допустимая мощность разряда "
                        f"{_fmt(battery_discharge_power, 0)} Вт < требуемой {_fmt(req_cont, 0)} Вт."
                    ),
                    "recommendation": (
                        "Добавьте параллельные строки АКБ, выберите батарею с большим током разряда "
                        "или инвертор меньшей мощности."
                    ),
                }
            )
        elif battery_discharge_power < req_surge:
            diagnostics.append(
                {
                    "level": "warning",
                    "block": "battery",
                    "message": (
                        f"Мощность разряда АКБ ({_fmt(battery_discharge_power, 0)} Вт) ниже пусковой "
                        f"инвертора ({_fmt(req_surge, 0)} Вт): возможны отключения при старте нагрузок."
                    ),
                    "recommendation": "Увеличьте число параллельных АКБ или снизьте пусковые токи нагрузок.",
                }
            )

    # PV string Vmp must stay comfortably above the battery bus for MPPT buck conversion.
    panel_vmp = float(results.get("panel_vmp", 0.0))
    pv_series = int(results.get("pv_series_count", 1))
    if panel_vmp > 0 and system_voltage > 0:
        string_vmp = panel_vmp * pv_series
        if string_vmp < 1.15 * system_voltage:
            diagnostics.append(
                {
                    "level": "critical",
                    "block": "string",
                    "message": (
                        f"Vmp стринга ({_fmt(string_vmp, 1)} В) ниже рабочего напряжения шины "
                        f"({_fmt(system_voltage, 0)} В): MPPT не сможет заряжать АКБ (buck-понижение)."
                    ),
                    "recommendation": "Увеличьте число модулей в серии или выберите панель с более высоким Vmp.",
                }
            )
        elif string_vmp < 1.3 * system_voltage:
            diagnostics.append(
                {
                    "level": "warning",
                    "block": "string",
                    "message": (
                        f"Vmp стринга ({_fmt(string_vmp, 1)} В) впритык к шине {_fmt(system_voltage, 0)} В: "
                        "в жару точка максимальной мощности просядет и заряд замедлится."
                    ),
                    "recommendation": "Добавьте один модуль в стринг для запаса по напряжению.",
                }
            )

    # --- Capacity / autonomy ---------------------------------------------------
    battery_capacity_actual = float(results.get("battery_capacity_actual", 0.0))
    battery_capacity_required = float(results.get("battery_capacity_total", 0.0))
    if battery_capacity_actual < battery_capacity_required:
        diagnostics.append(
            {
                "level": "warning",
                "block": "battery",
                "message": f"Фактическая емкость АКБ ({_fmt(battery_capacity_actual, 1)} А·ч) ниже требуемой ({_fmt(battery_capacity_required, 1)} А·ч).",
                "recommendation": "Увеличьте число параллельных батарей или снизьте количество дней автономии.",
            }
        )

    return diagnostics


def diagnostics_for_block(diagnostics: list[dict[str, Any]], block: str) -> list[dict[str, Any]]:
    return [d for d in diagnostics if d.get("block") == block]

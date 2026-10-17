"""Engineering core for autonomous photovoltaic and storage systems."""

from __future__ import annotations

from math import ceil
from typing import Any

from core.cable import CableResult, calculate_cable_section
from core.database import (
    Battery,
    ChargeController,
    Inverter,
    SolarPanel,
    CHARGE_CONTROLLERS,
    INVERTERS,
    get_battery,
    get_controller,
    get_inverter,
    get_panel,
)
from core.economics import build_bom, economic_summary
from core.protection import recommended_protection

INVERTER_EFFICIENCY = 0.88
PV_SYSTEM_EFFICIENCY = 0.78
BATTERY_TEMPERATURE_FACTOR = 1.0
CONTROLLER_CURRENT_MARGIN = 1.25
INVERTER_CONTINUOUS_MARGIN = 1.25
INVERTER_SURGE_MARGIN = 1.25
MIN_DESIGN_TEMPERATURE_C = -25.0
MPPT_VOLTAGE_DESIGN_MARGIN = 0.85
AC_VOLTAGE_V = 230.0
AC_DROP_RATIO = 0.03

DOD_BY_CHEMISTRY: dict[str, float] = {
    "LiFePO4": 0.90,
    "GEL": 0.55,
    "AGM": 0.45,
    "Ni-Cd": 0.70,
}


def _positive_float(data: dict[str, Any], key: str, default: float | None = None) -> float:
    if key in data:
        value = float(data[key])
    elif default is not None:
        value = float(default)
    else:
        raise ValueError(f"Отсутствует обязательный параметр '{key}'.")
    if value <= 0:
        raise ValueError(f"Параметр '{key}' должен быть больше нуля.")
    return value


def _loads(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw_loads = data.get(key, [])
    if raw_loads is None:
        return []
    if not isinstance(raw_loads, list):
        raise ValueError(f"Параметр '{key}' должен быть списком нагрузок.")

    loads: list[dict[str, Any]] = []
    for index, item in enumerate(raw_loads, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Нагрузка {key}[{index}] должна быть словарем.")
        name = str(item.get("name", f"Нагрузка {index}")).strip() or f"Нагрузка {index}"
        power = float(item.get("power", item.get("power_w", 0.0)))
        hours = float(item.get("hours_week", item.get("hours", 0.0)))
        surge_factor = float(item.get("surge_factor", 1.0))
        if power < 0:
            raise ValueError(f"Мощность нагрузки '{name}' не может быть отрицательной.")
        if hours < 0:
            raise ValueError(f"Часы работы нагрузки '{name}' не могут быть отрицательными.")
        if surge_factor < 1:
            raise ValueError(f"Пусковая кратность нагрузки '{name}' не может быть меньше 1.")
        loads.append(
            {
                "name": name,
                "power": power,
                "hours_week": hours,
                "surge_factor": surge_factor,
            }
        )
    return loads


def _weekly_energy_wh(loads: list[dict[str, Any]]) -> float:
    return sum(load["power"] * load["hours_week"] for load in loads)


def _cold_voc_factor(panel: SolarPanel, min_temperature_c: float) -> float:
    delta_t = max(0.0, 25.0 - min_temperature_c)
    return 1.0 + abs(panel.temp_coeff_voc_percent_per_c) / 100.0 * delta_t


def _inverter_requirements(ac_loads: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    continuous_power = sum(load["power"] for load in ac_loads)
    surge_power = continuous_power
    for load in ac_loads:
        if load["surge_factor"] > 1.0:
            scenario = continuous_power - load["power"] + load["power"] * load["surge_factor"]
            surge_power = max(surge_power, scenario)
    required_continuous = continuous_power * INVERTER_CONTINUOUS_MARGIN
    required_surge = max(surge_power * INVERTER_SURGE_MARGIN, required_continuous)
    return continuous_power, surge_power, required_continuous, required_surge


def _select_inverter(
    system_voltage: float,
    required_continuous_w: float,
    required_surge_w: float,
    forced_model: str | None = None,
) -> tuple[Inverter, list[str]]:
    warnings: list[str] = []
    voltage = int(round(system_voltage))

    if forced_model:
        inverter = get_inverter(forced_model)
        if inverter.input_voltage_v != voltage:
            warnings.append(
                f"Выбранный инвертор '{inverter.name}' рассчитан на {inverter.input_voltage_v} В, "
                f"а система — на {voltage} В."
            )
        if inverter.rated_power_w < required_continuous_w:
            warnings.append(
                f"Номинальная мощность инвертора ({inverter.rated_power_w:.0f} Вт) ниже "
                f"требуемой непрерывной ({required_continuous_w:.0f} Вт)."
            )
        if inverter.surge_power_w < required_surge_w:
            warnings.append(
                f"Пиковая мощность инвертора ({inverter.surge_power_w:.0f} Вт) ниже "
                f"требуемой пусковой ({required_surge_w:.0f} Вт)."
            )
        return inverter, warnings

    candidates = sorted(
        (
            inverter
            for inverter in INVERTERS
            if inverter.input_voltage_v == voltage
            and inverter.rated_power_w >= required_continuous_w
            and inverter.surge_power_w >= required_surge_w
        ),
        key=lambda item: item.rated_power_w,
    )
    if candidates:
        return candidates[0], warnings

    fallback = max(
        (inverter for inverter in INVERTERS if inverter.input_voltage_v == voltage),
        key=lambda item: item.rated_power_w,
        default=None,
    )
    if fallback is None:
        raise ValueError(f"В базе нет инвертора для системного напряжения {voltage} В.")
    warnings.append(
        "Не найден инвертор с достаточной непрерывной/пиковой мощностью. "
        f"Назначен самый мощный доступный '{fallback.name}', требуется ручная проверка."
    )
    return fallback, warnings


def _select_controller(
    panel: SolarPanel,
    modules_count: int,
    system_voltage: float,
    required_charge_current: float,
    min_temperature_c: float,
    forced_model: str | None = None,
) -> tuple[ChargeController, int, int, float, float, list[str]]:
    warnings: list[str] = []
    voltage = int(round(system_voltage))
    voc_factor = _cold_voc_factor(panel, min_temperature_c)

    if forced_model:
        controller = get_controller(forced_model)
        if voltage not in controller.supported_system_voltages:
            warnings.append(
                f"Выбранный контроллер '{controller.name}' не поддерживает {voltage} В систему."
            )
        max_series_by_voltage = max(
            1,
            int(
                controller.max_input_voltage_v
                * MPPT_VOLTAGE_DESIGN_MARGIN
                // (panel.voc_v * voc_factor)
            ),
        )
        series_count = max(1, min(modules_count, max_series_by_voltage))
        parallel_strings = int(ceil(modules_count / series_count))
        cold_string_voc = panel.voc_v * series_count * voc_factor
        if cold_string_voc > controller.max_input_voltage_v:
            warnings.append(
                f"Холодный Voc стринга ({cold_string_voc:.1f} В) превышает максимальный вход "
                f"контроллера {controller.max_input_voltage_v:.0f} В."
            )
        if controller.charge_current_a < required_charge_current:
            warnings.append(
                f"Ток контроллера ({controller.charge_current_a:.0f} А) ниже требуемого "
                f"({required_charge_current:.1f} А)."
            )
        if modules_count % series_count != 0:
            warnings.append(
                "Количество PV-модулей не кратно числу модулей в стринге; "
                "последний стринг будет неполным."
            )
        return controller, series_count, parallel_strings, cold_string_voc, voc_factor, warnings

    candidates = sorted(
        (
            controller
            for controller in CHARGE_CONTROLLERS
            if voltage in controller.supported_system_voltages
            and controller.charge_current_a >= required_charge_current
        ),
        key=lambda item: item.charge_current_a,
    )

    for controller in candidates:
        max_series_by_voltage = int(
            controller.max_input_voltage_v
            * MPPT_VOLTAGE_DESIGN_MARGIN
            // (panel.voc_v * voc_factor)
        )
        series_count = max(1, min(modules_count, max_series_by_voltage))
        parallel_strings = int(ceil(modules_count / series_count))
        cold_string_voc = panel.voc_v * series_count * voc_factor
        if cold_string_voc <= controller.max_input_voltage_v:
            if modules_count % series_count != 0:
                warnings.append(
                    "Количество PV-модулей не кратно числу модулей в стринге; "
                    "последний стринг будет неполным."
                )
            return controller, series_count, parallel_strings, cold_string_voc, voc_factor, warnings

    fallback = max(
        (controller for controller in CHARGE_CONTROLLERS if voltage in controller.supported_system_voltages),
        key=lambda item: item.charge_current_a,
        default=None,
    )
    if fallback is None:
        raise ValueError(f"В базе нет MPPT-контроллера для системного напряжения {system_voltage:g} В.")

    max_series_by_voltage = max(
        1,
        int(
            fallback.max_input_voltage_v
            * MPPT_VOLTAGE_DESIGN_MARGIN
            // (panel.voc_v * voc_factor)
        ),
    )
    series_count = max(1, min(modules_count, max_series_by_voltage))
    parallel_strings = int(ceil(modules_count / series_count))
    cold_string_voc = panel.voc_v * series_count * voc_factor
    warnings.append(
        "Не найден контроллер с достаточным запасом по току/напряжению. "
        f"Назначен '{fallback.name}', требуется ручная проверка по даташиту."
    )
    return fallback, series_count, parallel_strings, cold_string_voc, voc_factor, warnings


class SolarSystemCalculator:
    """Calculator for off-grid PV systems with battery storage."""

    def __init__(self, data: dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Входные данные калькулятора должны быть словарем.")
        self.data = data

    def calculate(self) -> dict[str, Any]:
        ac_loads = _loads(self.data, "ac_loads")
        dc_loads = _loads(self.data, "dc_loads")
        if not ac_loads and not dc_loads:
            raise ValueError("Добавьте хотя бы одну нагрузку AC или DC.")

        system_voltage = _positive_float(self.data, "system_voltage")
        days_autonomy = _positive_float(self.data, "days_autonomy")
        psh = _positive_float(self.data, "psh", self.data.get("min_insolation_dec", 0.9))
        if psh > 10:
            raise ValueError("Инсоляция PSH выглядит нереалистично большой (>10 ч/сутки).")

        inverter_efficiency = _positive_float(self.data, "inverter_efficiency", INVERTER_EFFICIENCY)
        if inverter_efficiency > 1:
            raise ValueError("КПД инвертора не может быть больше 1.")
        pv_system_efficiency = _positive_float(self.data, "pv_system_efficiency", PV_SYSTEM_EFFICIENCY)
        if pv_system_efficiency > 1:
            raise ValueError("Системный КПД PV не может быть больше 1.")
        relief_coefficient = _positive_float(self.data, "relief_coefficient", 1.0)
        if relief_coefficient > 1.0:
            raise ValueError("Коэффициент рельефа/затенения не может быть больше 1.")
        battery_temperature_factor = _positive_float(
            self.data, "battery_temperature_factor", BATTERY_TEMPERATURE_FACTOR
        )
        min_temperature_c = float(self.data.get("min_temperature_c", MIN_DESIGN_TEMPERATURE_C))
        cable_length = float(self.data.get("cable_length", 10.0))
        ac_cable_length = float(self.data.get("ac_cable_length", 5.0))
        if cable_length < 0 or ac_cable_length < 0:
            raise ValueError("Длина кабельной трассы не может быть отрицательной.")

        panel = get_panel(str(self.data.get("panel_model", "МС-50-4 (Базовая)")))
        battery = get_battery(str(self.data.get("battery_model", "Гелевая Delta GOR 120Ач (24 В)")))

        (
            continuous_ac_power,
            surge_ac_power,
            inverter_required_continuous,
            inverter_required_surge,
        ) = _inverter_requirements(ac_loads)
        inverter, inverter_warnings = _select_inverter(
            system_voltage=system_voltage,
            required_continuous_w=inverter_required_continuous,
            required_surge_w=inverter_required_surge,
            forced_model=self.data.get("inverter_model"),
        )
        if continuous_ac_power == 0:
            inverter_warnings.append(
                "AC-нагрузки отсутствуют; инвертор выбран минимальной мощности для резервной AC-шины."
            )

        total_w_ac_week = _weekly_energy_wh(ac_loads)
        total_w_dc_week = _weekly_energy_wh(dc_loads)
        w1_energy = total_w_ac_week / inverter_efficiency
        daily_energy_wh = (w1_energy + total_w_dc_week) / 7.0
        e_sigma_ah_day = daily_energy_wh / system_voltage

        dod = DOD_BY_CHEMISTRY.get(battery.chemistry, 0.50)
        battery_capacity_required = (
            daily_energy_wh
            * days_autonomy
            / (system_voltage * dod * battery_temperature_factor)
        )

        series_ratio = system_voltage / battery.voltage_v
        series_count = int(round(series_ratio))
        if series_count <= 0 or abs(series_ratio - series_count) > 1e-6:
            raise ValueError(
                "Несовместимое напряжение АКБ и системы: "
                f"U_system={system_voltage:g} В, U_batt={battery.voltage_v:g} В. "
                "Напряжение системы должно делиться на напряжение одной АКБ без остатка."
            )

        parallel_strings = int(ceil(battery_capacity_required / battery.capacity_ah))
        battery_total_count = series_count * parallel_strings
        battery_capacity_actual = parallel_strings * battery.capacity_ah
        battery_energy_actual_wh = battery_capacity_actual * system_voltage

        effective_pv_efficiency = pv_system_efficiency * relief_coefficient
        pv_required_w = daily_energy_wh / (psh * effective_pv_efficiency)
        pv_modules_count = max(1, int(ceil(pv_required_w / panel.power_w)))
        pv_actual_w = pv_modules_count * panel.power_w

        pv_charge_current_a = pv_actual_w / system_voltage
        controller_required_current_a = pv_charge_current_a * CONTROLLER_CURRENT_MARGIN
        (
            controller,
            pv_series_count,
            pv_parallel_strings,
            pv_cold_string_voc,
            pv_cold_voc_factor,
            controller_warnings,
        ) = _select_controller(
            panel=panel,
            modules_count=pv_modules_count,
            system_voltage=system_voltage,
            required_charge_current=controller_required_current_a,
            min_temperature_c=min_temperature_c,
            forced_model=self.data.get("controller_model"),
        )

        pv_array_current_a = max(pv_charge_current_a, panel.imp_a * pv_parallel_strings)
        dc_cable: CableResult = calculate_cable_section(
            current_a=pv_array_current_a,
            length_m=cable_length,
            system_voltage_v=system_voltage,
            forced_section_mm2=self.data.get("cable_section_mm2"),
        )

        ac_output_current_a = continuous_ac_power / AC_VOLTAGE_V
        ac_cable: CableResult = calculate_cable_section(
            current_a=ac_output_current_a,
            length_m=ac_cable_length,
            system_voltage_v=AC_VOLTAGE_V,
            drop_ratio=AC_DROP_RATIO,
            forced_section_mm2=self.data.get("ac_cable_section_mm2"),
        )

        inverter_dc_current_a = inverter.rated_power_w / (system_voltage * inverter.efficiency)
        battery_main_current_a = max(controller.charge_current_a, inverter_dc_current_a)
        pv_array_short_circuit_a = panel.isc_a * pv_parallel_strings
        protection = recommended_protection(
            pv_array_short_circuit_current_a=pv_array_short_circuit_a,
            controller_charge_current_a=controller.charge_current_a,
            battery_main_current_a=battery_main_current_a,
            ac_output_current_a=ac_output_current_a,
        )

        warnings: list[str] = []
        warnings.extend(inverter_warnings)
        warnings.extend(controller_warnings)
        warnings.extend(dc_cable.warnings)
        if continuous_ac_power > 0:
            warnings.extend(ac_cable.warnings)
        warnings.extend(protection.get("warnings", []))
        if battery_capacity_actual * dod * battery_temperature_factor * system_voltage < daily_energy_wh * days_autonomy:
            warnings.append("Установленная полезная емкость АКБ ниже требуемой автономии.")
        if pv_charge_current_a > battery.max_charge_current_a * parallel_strings:
            warnings.append(
                "Ток заряда PV-преобразователя превышает суммарно допустимый ток заряда АКБ; "
                "увеличьте число параллельных строк АКБ или ограничьте ток контроллера."
            )

        steps = [
            "Шаг 1. Энергия AC-нагрузок за неделю: "
            f"W_ac = Σ(P_i·t_i) = {total_w_ac_week:.2f} Вт·ч/нед.",
            "Шаг 2. Энергия с учетом КПД инвертора: "
            f"W1 = W_ac/η_inv = {total_w_ac_week:.2f}/{inverter_efficiency:.2f} = {w1_energy:.2f} Вт·ч/нед.",
            "Шаг 3. Суточное энергопотребление: "
            f"W_day = (W1 + W_dc)/7 = ({w1_energy:.2f} + {total_w_dc_week:.2f})/7 = {daily_energy_wh:.2f} Вт·ч/сутки.",
            "Шаг 4. Суточный зарядный эквивалент: "
            f"E_sigma = W_day/U_sys = {daily_energy_wh:.2f}/{system_voltage:.2f} = {e_sigma_ah_day:.2f} А·ч/сутки.",
            "Шаг 5. Требуемая емкость АКБ: "
            f"C_req = W_day·n/(U_sys·DoD·k_t) = {daily_energy_wh:.2f}·{days_autonomy:.2f}/"
            f"({system_voltage:.2f}·{dod:.2f}·{battery_temperature_factor:.2f}) = {battery_capacity_required:.2f} А·ч.",
            "Шаг 6. Конфигурация АКБ: "
            f"N_series = U_sys/U_batt = {system_voltage:.2f}/{battery.voltage_v:.2f} = {series_count}; "
            f"N_parallel = ceil(C_req/C_batt) = ceil({battery_capacity_required:.2f}/{battery.capacity_ah:.2f}) = {parallel_strings}; "
            f"N_total = {battery_total_count} шт.",
            "Шаг 7. Требуемая мощность PV: "
            f"P_pv_req = W_day/(PSH·η_sys·k_relief) = {daily_energy_wh:.2f}/"
            f"({psh:.2f}·{pv_system_efficiency:.2f}·{relief_coefficient:.2f}) = {pv_required_w:.2f} Вт.",
            "Шаг 8. Количество PV-модулей: "
            f"N_pv = ceil(P_pv_req/P_unit) = ceil({pv_required_w:.2f}/{panel.power_w:.2f}) = {pv_modules_count} шт.; "
            f"P_pv_actual = {pv_actual_w:.2f} Вт.",
            "Шаг 9. PV-стринги по холодному Voc: "
            f"k_cold = {pv_cold_voc_factor:.3f}; конфигурация {pv_series_count}S×{pv_parallel_strings}P; "
            f"Voc(string,Tmin) = {pv_cold_string_voc:.1f} В < V_in,max {controller.max_input_voltage_v:.0f} В.",
            "Шаг 10. Ток заряда и контроллер: "
            f"I_charge = P_pv_actual/U_sys = {pv_actual_w:.2f}/{system_voltage:.2f} = {pv_charge_current_a:.2f} А; "
            f"I_controller ≥ 1.25·I_charge = {controller_required_current_a:.2f} А; выбран {controller.name}.",
            "Шаг 11. Инвертор и пусковые токи: "
            f"P_cont={continuous_ac_power:.2f} Вт; P_surge={surge_ac_power:.2f} Вт; "
            f"требуется ≥{inverter_required_continuous:.2f}/{inverter_required_surge:.2f} Вт; "
            f"выбран {inverter.name}.",
            "Шаг 12. Кабель DC: "
            f"ΔU_max = 0.02·U_sys = {dc_cable.max_drop_v:.3f} В; принято {dc_cable.section_mm2:g} мм², "
            f"ΔU = {dc_cable.actual_drop_v:.3f} В ({dc_cable.actual_drop_percent:.2f}%).",
            "Шаг 13. Кабель AC 230 В: "
            f"I_ac = P_ac/230 = {continuous_ac_power:.2f}/230 = {ac_output_current_a:.2f} А; "
            f"принято {ac_cable.section_mm2:g} мм², ΔU = {ac_cable.actual_drop_v:.3f} В ({ac_cable.actual_drop_percent:.2f}%).",
            "Шаг 14. Защита: "
            f"PV MCB {protection['pv_array_breaker_a']} А; контроллер-АКБ {protection['controller_battery_breaker_a']} А; "
            f"главный АКБ {protection['battery_main_breaker_a']} А; AC MCB {protection['ac_output_breaker_a']} А; {protection['ac_rcd']}.",
        ]

        steps_latex = [
            rf"W_{{ac}}=\sum_i P_i\,t_i={total_w_ac_week:.2f}\ \mathrm{{Wh}}",
            rf"W_1=\frac{{W_{{ac}}}}{{\eta_{{inv}}}}=\frac{{{total_w_ac_week:.2f}}}{{{inverter_efficiency:.2f}}}={w1_energy:.2f}\ \mathrm{{Wh}}",
            rf"W_{{day}}=\frac{{W_1+W_{{dc}}}}{{7}}=\frac{{{w1_energy:.2f}+{total_w_dc_week:.2f}}}{{7}}={daily_energy_wh:.2f}\ \mathrm{{Wh/day}}",
            rf"E_{{\sigma}}=\frac{{W_{{day}}}}{{U_{{sys}}}}=\frac{{{daily_energy_wh:.2f}}}{{{system_voltage:.2f}}}={e_sigma_ah_day:.2f}\ \mathrm{{Ah/day}}",
            rf"C_{{req}}=\frac{{W_{{day}}\,n}}{{U_{{sys}}\,DoD\,k_t}}=\frac{{{daily_energy_wh:.2f}\cdot{days_autonomy:.2f}}}{{{system_voltage:.2f}\cdot{dod:.2f}\cdot{battery_temperature_factor:.2f}}}={battery_capacity_required:.2f}\ \mathrm{{Ah}}",
            rf"N_{{ser}}=\frac{{U_{{sys}}}}{{U_{{batt}}}}=\frac{{{system_voltage:.1f}}}{{{battery.voltage_v:.1f}}}={series_count};\quad N_{{par}}=\left\lceil\frac{{C_{{req}}}}{{C_{{batt}}}}\right\rceil=\left\lceil\frac{{{battery_capacity_required:.2f}}}{{{battery.capacity_ah:.2f}}}\right\rceil={parallel_strings}",
            rf"P_{{pv}}=\frac{{W_{{day}}}}{{PSH\,\eta_{{sys}}\,k_{{relief}}}}=\frac{{{daily_energy_wh:.2f}}}{{{psh:.2f}\cdot{pv_system_efficiency:.2f}\cdot{relief_coefficient:.2f}}}={pv_required_w:.2f}\ \mathrm{{W}}",
            rf"N_{{pv}}=\left\lceil\frac{{P_{{pv}}}}{{P_{{panel}}}}\right\rceil=\left\lceil\frac{{{pv_required_w:.2f}}}{{{panel.power_w:.1f}}}\right\rceil={pv_modules_count}",
            rf"V_{{oc,str}}(T_{{min}})=k_{{cold}}\,V_{{oc}}\,N_s={pv_cold_string_voc:.1f}\ \mathrm{{V}}<V_{{in,max}}={controller.max_input_voltage_v:.0f}\ \mathrm{{V}}",
            rf"I_{{charge}}=\frac{{P_{{pv}}}}{{U_{{sys}}}}=\frac{{{pv_actual_w:.1f}}}{{{system_voltage:.1f}}}={pv_charge_current_a:.2f}\ \mathrm{{A}};\quad I_{{ctrl}}\geq{controller_required_current_a:.2f}\ \mathrm{{A}}",
            rf"P_{{cont}}={continuous_ac_power:.1f}\ \mathrm{{W}};\quad P_{{surge}}={surge_ac_power:.1f}\ \mathrm{{W}}",
            rf"\Delta U_{{max}}=0.02\,U_{{sys}}={dc_cable.max_drop_v:.3f}\ \mathrm{{V}};\quad S={dc_cable.section_mm2:g}\ \mathrm{{mm^2}};\quad \Delta U={dc_cable.actual_drop_v:.3f}\ \mathrm{{V}}",
            rf"I_{{ac}}=\frac{{P_{{ac}}}}{{230}}=\frac{{{continuous_ac_power:.1f}}}{{230}}={ac_output_current_a:.2f}\ \mathrm{{A}};\quad S_{{ac}}={ac_cable.section_mm2:g}\ \mathrm{{mm^2}}",
            rf"I_{{PV}}={protection['pv_array_breaker_a']}\ \mathrm{{A}};\quad I_{{ctrl}}={protection['controller_battery_breaker_a']}\ \mathrm{{A}};\quad I_{{batt}}={protection['battery_main_breaker_a']}\ \mathrm{{A}};\quad I_{{AC}}={protection['ac_output_breaker_a']}\ \mathrm{{A}}",
        ]

        result: dict[str, Any] = {
            "system_voltage": system_voltage,
            "steps_latex": steps_latex,
            "city": self.data.get("city", "—"),
            "month": self.data.get("month", "—"),
            "relief_name": self.data.get("relief_name", "—"),
            "relief_coefficient": relief_coefficient,
            "total_w_ac": total_w_ac_week,
            "w1_energy": w1_energy,
            "total_w_dc": total_w_dc_week,
            "daily_energy_wh": daily_energy_wh,
            "e_sigma": e_sigma_ah_day,
            "inverter_efficiency": inverter_efficiency,
            "pv_system_efficiency": pv_system_efficiency,
            "effective_pv_efficiency": effective_pv_efficiency,
            "psh": psh,
            "battery_dod": dod,
            "battery_capacity_total": battery_capacity_required,
            "battery_capacity_actual": battery_capacity_actual,
            "battery_energy_actual_wh": battery_energy_actual_wh,
            "battery_series_count": series_count,
            "battery_parallel_count": parallel_strings,
            "battery_count": battery_total_count,
            "p_panel_req": pv_required_w,
            "pv_actual_w": pv_actual_w,
            "nm_modules": pv_modules_count,
            "pv_series_count": pv_series_count,
            "pv_parallel_strings": pv_parallel_strings,
            "pv_cold_string_voc": pv_cold_string_voc,
            "pv_cold_voc_factor": pv_cold_voc_factor,
            "panel_model": panel.name,
            "panel_power_unit": panel.power_w,
            "panel_voc": panel.voc_v,
            "panel_vmp": panel.vmp_v,
            "panel_isc": panel.isc_a,
            "panel_temp_coeff_voc": panel.temp_coeff_voc_percent_per_c,
            "battery_model": battery.name,
            "battery_unit_capacity": battery.capacity_ah,
            "battery_unit_voltage": battery.voltage_v,
            "battery_chemistry": battery.chemistry,
            "battery_max_charge_current": battery.max_charge_current_a,
            "battery_max_discharge_current": battery.max_discharge_current_a,
            "controller_model": controller.name,
            "controller_current": controller.charge_current_a,
            "controller_required_current": controller_required_current_a,
            "controller_max_input_voltage": controller.max_input_voltage_v,
            "controller_supported_voltages": controller.supported_system_voltages,
            "controller_warning": "; ".join(controller_warnings),
            "continuous_ac_power_w": continuous_ac_power,
            "surge_ac_power_w": surge_ac_power,
            "inverter_required_continuous_w": inverter_required_continuous,
            "inverter_required_surge_w": inverter_required_surge,
            "inverter_model": inverter.name,
            "inverter_rated_w": inverter.rated_power_w,
            "inverter_surge_w": inverter.surge_power_w,
            "inverter_input_voltage": inverter.input_voltage_v,
            "inverter_selected_efficiency": inverter.efficiency,
            "inverter_warning": "; ".join(inverter_warnings),
            "inverter_dc_current_a": inverter_dc_current_a,
            "total_panel_current": pv_array_current_a,
            "pv_array_short_circuit_a": pv_array_short_circuit_a,
            "ac_output_current_a": ac_output_current_a,
            "cable": dc_cable,
            "cable_section_mm2": dc_cable.section_mm2,
            "cable_required_section_mm2": dc_cable.required_section_mm2,
            "cable_voltage_drop_v": dc_cable.actual_drop_v,
            "cable_voltage_drop_percent": dc_cable.actual_drop_percent,
            "cable_ampacity_a": dc_cable.ampacity_a,
            "cable_warning": "; ".join(dc_cable.warnings),
            "ac_cable": ac_cable,
            "ac_cable_section_mm2": ac_cable.section_mm2,
            "ac_cable_required_section_mm2": ac_cable.required_section_mm2,
            "ac_cable_voltage_drop_v": ac_cable.actual_drop_v,
            "ac_cable_voltage_drop_percent": ac_cable.actual_drop_percent,
            "ac_cable_ampacity_a": ac_cable.ampacity_a,
            "ac_cable_warning": "; ".join(ac_cable.warnings),
            "protection": protection,
            "warnings": warnings,
            "steps": steps,
        }
        result["bom"] = build_bom(self.data, result)
        result["economics"] = economic_summary(self.data, result, result["bom"])
        return result

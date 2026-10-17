"""Reactive application state for the ImGui UI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from core.cable import STANDARD_SECTIONS_MM2
from core.calculator import SolarSystemCalculator
from core.climate import (
    MONTHS,
    city_names,
    get_min_design_temperature,
    get_monthly_psh,
    get_relief_coefficient,
    relief_names,
)
from core.database import (
    battery_names,
    controller_names,
    get_battery,
    get_panel,
    inverter_names,
    panel_names,
)
from core.missions import Mission, evaluate_mission, get_mission_by_title, mission_names
from core.presets import get_preset, preset_names
from ui.diagnostics import compute_diagnostics


@dataclass
class AppState:
    voltage_idx: int = 1
    voltages: list[int] = field(default_factory=lambda: [12, 24, 48])
    days_autonomy: float = 2.0
    use_climate_data: bool = True
    city_idx: int = 0
    month_idx: int = 6
    relief_idx: int = 0
    cities: list[str] = field(default_factory=city_names)
    months: list[str] = field(default_factory=lambda: list(MONTHS))
    reliefs: list[str] = field(default_factory=relief_names)
    preset_idx: int = 0
    presets: list[str] = field(default_factory=preset_names)
    missions: list[str] = field(default_factory=mission_names)
    psh: float = 3.0
    cable_length: float = 10.0
    ac_cable_length: float = 5.0
    inverter_efficiency: float = 0.90
    pv_system_efficiency: float = 0.78
    min_temperature_c: float = -25.0
    electricity_tariff_byn_kwh: float = 0.30
    project_lifetime_years: float = 15.0
    detailed_analysis: bool = False

    panel_model_idx: int = 0
    batt_model_idx: int = 2
    panel_models: list[str] = field(default_factory=panel_names)
    batt_models: list[str] = field(default_factory=battery_names)

    # Manual component overrides (auto = let the calculator pick)
    # По умолчанию ручной выбор: пользователь сам собирает систему и учится.
    auto_inverter: bool = False
    auto_controller: bool = False
    auto_cable: bool = False
    auto_ac_cable: bool = False
    inverter_model_idx: int = 1  # Victron Phoenix 24/1200 — совместим с дефолтной 24 В
    controller_model_idx: int = 1  # Victron SmartSolar 100/50 — запас по току
    cable_section_idx: int = 0
    ac_cable_section_idx: int = 0
    inverter_models: list[str] = field(default_factory=inverter_names)
    controller_models: list[str] = field(default_factory=controller_names)
    cable_section_options: list[str] = field(
        default_factory=lambda: ["Авто"] + [f"{s:g}" for s in STANDARD_SECTIONS_MM2]
    )
    ac_cable_section_options: list[str] = field(
        default_factory=lambda: ["Авто"] + [f"{s:g}" for s in STANDARD_SECTIONS_MM2]
    )

    ac_loads: list[list[Any]] = field(
        default_factory=lambda: [
            ["Освещение", 100.0, 35.0, 1.0],
            ["Холодильник", 150.0, 84.0, 5.0],
            ["Телевизор", 80.0, 20.0, 1.2],
        ]
    )
    dc_loads: list[list[Any]] = field(
        default_factory=lambda: [
            ["Роутер 12В", 15.0, 168.0, 1.0],
            ["Аварийный свет", 20.0, 14.0, 1.0],
        ]
    )

    project_file_name: str = "pv_project.json"
    show_onboarding: bool = True
    show_inspector: bool = False
    results: dict[str, Any] | None = None
    status_message: str = ""
    error_message: str = ""

    # Trainer / mission mode
    mode: str = "design"  # "design" or "trainer"
    trainer_mission_idx: int = 0
    current_mission: dict[str, Any] | None = None
    mission_evaluation: dict[str, Any] | None = None
    auto_recalculate: bool = True
    last_error_text: str = ""
    last_payload_hash: str = ""

    @staticmethod
    def _clamp_index(index: int, values: list[Any]) -> int:
        if not values:
            raise ValueError("Список выбора пуст.")
        return max(0, min(int(index), len(values) - 1))

    @staticmethod
    def _index_of(values: list[str], name: Any, default: int = 0) -> int:
        try:
            return values.index(str(name))
        except ValueError:
            return default

    def system_voltage(self) -> float:
        self.voltage_idx = self._clamp_index(self.voltage_idx, self.voltages)
        return float(self.voltages[self.voltage_idx])

    def selected_panel(self) -> str:
        self.panel_model_idx = self._clamp_index(self.panel_model_idx, self.panel_models)
        return self.panel_models[self.panel_model_idx]

    def selected_battery(self) -> str:
        self.batt_model_idx = self._clamp_index(self.batt_model_idx, self.batt_models)
        return self.batt_models[self.batt_model_idx]

    def selected_inverter(self) -> str:
        self.inverter_model_idx = self._clamp_index(self.inverter_model_idx, self.inverter_models)
        return self.inverter_models[self.inverter_model_idx]

    def selected_controller(self) -> str:
        self.controller_model_idx = self._clamp_index(self.controller_model_idx, self.controller_models)
        return self.controller_models[self.controller_model_idx]

    def selected_cable_section(self) -> float | None:
        self.cable_section_idx = self._clamp_index(self.cable_section_idx, self.cable_section_options)
        text = self.cable_section_options[self.cable_section_idx]
        return float(text) if text != "Авто" else None

    def selected_ac_cable_section(self) -> float | None:
        self.ac_cable_section_idx = self._clamp_index(self.ac_cable_section_idx, self.ac_cable_section_options)
        text = self.ac_cable_section_options[self.ac_cable_section_idx]
        return float(text) if text != "Авто" else None

    def selected_city(self) -> str:
        self.city_idx = self._clamp_index(self.city_idx, self.cities)
        return self.cities[self.city_idx]

    def selected_month(self) -> str:
        self.month_idx = self._clamp_index(self.month_idx, self.months)
        return self.months[self.month_idx]

    def selected_relief(self) -> str:
        self.relief_idx = self._clamp_index(self.relief_idx, self.reliefs)
        return self.reliefs[self.relief_idx]

    def selected_preset(self) -> str:
        self.preset_idx = self._clamp_index(self.preset_idx, self.presets)
        return self.presets[self.preset_idx]

    def reset_sane_defaults(self) -> None:
        self.apply_preset("Дача")
        self.status_message = "Применен разумный preset «Дача». Нажмите «Рассчитать АФС»."

    def apply_preset(self, name: str) -> None:
        preset = get_preset(name)
        self.apply_payload(preset.payload)
        self.results = None
        self.error_message = ""
        self.status_message = f"Применен сценарий «{preset.name}»: {preset.description}"

    @staticmethod
    def _format_loads(loads: list[list[Any]]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        for load in loads:
            if len(load) < 3:
                continue
            formatted.append(
                {
                    "name": str(load[0]),
                    "power": float(load[1]),
                    "hours_week": float(load[2]),
                    "surge_factor": float(load[3]) if len(load) > 3 else 1.0,
                }
            )
        return formatted

    def calculation_payload(self) -> dict[str, Any]:
        if self.use_climate_data:
            city = self.selected_city()
            month = self.selected_month()
            relief_name = self.selected_relief()
            psh = get_monthly_psh(city, month)
            min_temperature = get_min_design_temperature(city)
            relief_coefficient = get_relief_coefficient(relief_name)
        else:
            city = "Ручной режим"
            month = "—"
            relief_name = "Ручной режим"
            psh = float(self.psh)
            min_temperature = float(self.min_temperature_c)
            relief_coefficient = 1.0

        payload: dict[str, Any] = {
            "ac_loads": self._format_loads(self.ac_loads),
            "dc_loads": self._format_loads(self.dc_loads),
            "days_autonomy": float(self.days_autonomy),
            "use_climate_data": bool(self.use_climate_data),
            "city": city,
            "month": month,
            "relief_name": relief_name,
            "relief_coefficient": float(relief_coefficient),
            "psh": float(psh),
            "min_insolation_dec": float(psh),
            "system_voltage": self.system_voltage(),
            "panel_model": self.selected_panel(),
            "battery_model": self.selected_battery(),
            "cable_length": float(self.cable_length),
            "ac_cable_length": float(self.ac_cable_length),
            "inverter_efficiency": float(self.inverter_efficiency),
            "pv_system_efficiency": float(self.pv_system_efficiency),
            "min_temperature_c": float(min_temperature),
            "electricity_tariff_byn_kwh": float(self.electricity_tariff_byn_kwh),
            "project_lifetime_years": float(self.project_lifetime_years),
        }
        if not self.auto_inverter:
            payload["inverter_model"] = self.selected_inverter()
        if not self.auto_controller:
            payload["controller_model"] = self.selected_controller()
        if not self.auto_cable:
            section = self.selected_cable_section()
            if section is not None:
                payload["cable_section_mm2"] = section
        if not self.auto_ac_cable:
            section = self.selected_ac_cable_section()
            if section is not None:
                payload["ac_cable_section_mm2"] = section
        return payload

    def sync_auto_selections(self) -> None:
        """Update auto-selection indices from the latest calculation results."""
        if not self.results:
            return
        if self.auto_inverter:
            self.inverter_model_idx = self._index_of(
                self.inverter_models, self.results.get("inverter_model"), self.inverter_model_idx
            )
        if self.auto_controller:
            self.controller_model_idx = self._index_of(
                self.controller_models, self.results.get("controller_model"), self.controller_model_idx
            )
        if self.auto_cable:
            self.cable_section_idx = self._index_of(
                self.cable_section_options, f"{float(self.results.get('cable_section_mm2', 0.0)):g}", self.cable_section_idx
            )
        if self.auto_ac_cable:
            self.ac_cable_section_idx = self._index_of(
                self.ac_cable_section_options, f"{float(self.results.get('ac_cable_section_mm2', 0.0)):g}", self.ac_cable_section_idx
            )

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        try:
            payload = self.calculation_payload()
        except Exception as exc:  # noqa: BLE001
            return [f"Ошибка подготовки параметров: {exc}"]

        if payload["days_autonomy"] <= 0:
            errors.append("Дней автономии должно быть больше нуля.")
        if not 0.2 <= payload["psh"] <= 8.0:
            errors.append("PSH должен быть в диапазоне 0.2…8.0 ч/сутки.")
        if not 0.5 <= payload["inverter_efficiency"] <= 1.0:
            errors.append("КПД инвертора должен быть в диапазоне 0.5…1.0.")
        if not 0.5 <= payload["pv_system_efficiency"] <= 1.0:
            errors.append("Системный КПД PV должен быть в диапазоне 0.5…1.0.")
        if payload["cable_length"] < 0 or payload["ac_cable_length"] < 0:
            errors.append("Длины кабельных трасс не могут быть отрицательными.")
        if payload["electricity_tariff_byn_kwh"] < 0:
            errors.append("Тариф сети не может быть отрицательным.")
        if payload["project_lifetime_years"] < 1:
            errors.append("Срок службы проекта должен быть не меньше 1 года.")
        if not payload["ac_loads"] and not payload["dc_loads"]:
            errors.append("Добавьте хотя бы одну AC или DC нагрузку.")

        try:
            panel = get_panel(payload["panel_model"])
            battery = get_battery(payload["battery_model"])
            if panel.power_w <= 0:
                errors.append("Мощность выбранной панели должна быть больше нуля.")
            ratio = payload["system_voltage"] / battery.voltage_v
            if abs(ratio - round(ratio)) > 1e-6 or round(ratio) <= 0:
                errors.append(
                    f"Напряжение системы {payload['system_voltage']:g} В несовместимо с АКБ {battery.voltage_v:g} В."
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        for section, loads in (("AC", payload["ac_loads"]), ("DC", payload["dc_loads"])):
            for load in loads:
                if load["power"] < 0:
                    errors.append(f"{section}: мощность '{load['name']}' отрицательная.")
                if load["hours_week"] < 0 or load["hours_week"] > 168:
                    errors.append(f"{section}: часы '{load['name']}' должны быть в диапазоне 0…168.")
                if load["surge_factor"] < 1 or load["surge_factor"] > 10:
                    errors.append(f"{section}: k_пуск '{load['name']}' должен быть в диапазоне 1…10.")
        return errors

    @staticmethod
    def _loads_to_rows(loads: Any) -> list[list[Any]]:
        rows: list[list[Any]] = []
        if not isinstance(loads, list):
            return rows
        for item in loads:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    str(item.get("name", "Нагрузка")),
                    float(item.get("power", 0.0)),
                    float(item.get("hours_week", 0.0)),
                    float(item.get("surge_factor", 1.0)),
                ]
            )
        return rows

    def apply_payload(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Payload проекта должен быть словарем.")
        self.ac_loads = self._loads_to_rows(payload.get("ac_loads", []))
        self.dc_loads = self._loads_to_rows(payload.get("dc_loads", []))
        self.days_autonomy = float(payload.get("days_autonomy", self.days_autonomy))
        self.use_climate_data = bool(payload.get("use_climate_data", False))
        self.psh = float(payload.get("psh", self.psh))
        self.cable_length = float(payload.get("cable_length", self.cable_length))
        self.ac_cable_length = float(payload.get("ac_cable_length", self.ac_cable_length))
        self.inverter_efficiency = float(payload.get("inverter_efficiency", self.inverter_efficiency))
        self.pv_system_efficiency = float(payload.get("pv_system_efficiency", self.pv_system_efficiency))
        self.min_temperature_c = float(payload.get("min_temperature_c", self.min_temperature_c))
        self.electricity_tariff_byn_kwh = float(
            payload.get("electricity_tariff_byn_kwh", self.electricity_tariff_byn_kwh)
        )
        self.project_lifetime_years = float(
            payload.get("project_lifetime_years", self.project_lifetime_years)
        )
        system_voltage = int(round(float(payload.get("system_voltage", self.system_voltage()))))
        self.voltage_idx = self._index_of([str(v) for v in self.voltages], system_voltage, self.voltage_idx)
        self.panel_model_idx = self._index_of(self.panel_models, payload.get("panel_model"), self.panel_model_idx)
        self.batt_model_idx = self._index_of(self.batt_models, payload.get("battery_model"), self.batt_model_idx)

        # Keep manual mode when loading a preset/project: user picks components.
        self.auto_inverter = False
        self.auto_controller = False
        self.auto_cable = False
        self.auto_ac_cable = False

        if self.use_climate_data:
            self.city_idx = self._index_of(self.cities, payload.get("city"), self.city_idx)
            self.month_idx = self._index_of(self.months, payload.get("month"), self.month_idx)
            self.relief_idx = self._index_of(self.reliefs, payload.get("relief_name"), self.relief_idx)
        self.results = None
        self.error_message = ""
        self.mission_evaluation = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if mode == "design":
            self.current_mission = None
            self.mission_evaluation = None
        elif mode == "trainer" and not self.current_mission and self.missions:
            mission = get_mission_by_title(self.missions[self.trainer_mission_idx])
            self.apply_mission(mission)

    def apply_mission(self, mission: Mission) -> None:
        payload = mission.to_dict()
        payload["ac_loads"] = list(mission.required_ac_loads)
        payload["dc_loads"] = list(mission.required_dc_loads)
        payload["days_autonomy"] = float(mission.min_autonomy_days)
        payload["use_climate_data"] = bool(mission.city and mission.month)
        self.apply_payload(payload)
        self.current_mission = mission.to_dict()
        self.mode = "trainer"
        self.mission_evaluation = None
        self.status_message = (
            f"Задание «{mission.title}». Бюджет: {mission.budget_byn:,.0f} BYN. "
            "Подберите оборудование и параметры."
        )
        self.error_message = ""

    def recalculate(self, force: bool = False) -> bool:
        """Run the calculator and update mission evaluation.

        If ``force`` is False the calculation is skipped when the payload hash
        matches the previous one, so this method can be called every frame.
        Returns True if results were updated.
        """
        import hashlib

        errors = self.validation_errors()
        if errors:
            if self.last_error_text != errors[0]:
                self.error_message = "; ".join(errors)
                self.last_error_text = errors[0]
            self.results = None
            self.mission_evaluation = None
            return False

        payload = self.calculation_payload()
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        if not force and payload_hash == self.last_payload_hash:
            return False
        self.last_payload_hash = payload_hash

        try:
            calculator = SolarSystemCalculator(payload)
            self.results = calculator.calculate()
            self.sync_auto_selections()
            diagnostics = compute_diagnostics(self, self.results)
            if self.current_mission:
                mission = Mission(**self.current_mission)
                self.mission_evaluation = evaluate_mission(mission, payload, self.results, diagnostics)
            self.error_message = ""
            self.last_error_text = ""
            if self.mode == "trainer" and self.mission_evaluation:
                score = int(self.mission_evaluation.get("score", 0))
                passed = bool(self.mission_evaluation.get("passed"))
                self.status_message = (
                    f"Оценка: {score}/100 | "
                    f"{'Задание выполнено!' if passed else 'Есть нарушения условий.'}"
                )
            else:
                capex = self.results.get("economics", {}).get("capex_byn", 0.0)
                self.status_message = f"Расчёт выполнен. CAPEX: {float(capex):,.2f} BYN."
                self.show_inspector = True
            return True
        except Exception as exc:  # noqa: BLE001
            self.results = None
            self.mission_evaluation = None
            msg = f"Ошибка расчёта: {exc}"
            if self.last_error_text != msg:
                self.error_message = msg
                self.last_error_text = msg
            return False

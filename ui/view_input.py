"""Main input tab: scenario presets, guided parameters, validation and project IO."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from imgui_bundle import imgui

from core.climate import get_min_design_temperature, get_monthly_psh, get_relief_coefficient
from core.database import (
    get_battery,
    get_controller,
    get_inverter,
    get_panel,
)
from core.missions import get_mission_by_title
from core.project import load_project, save_project
from ui.diagnostics import compute_diagnostics
from ui.dialogs import ask_open_json, ask_save_json
from ui.state import AppState
from ui.view_mission import draw_mission_panel
from ui.widgets import clamp, help_marker, tooltip


def _draw_load_table(title: str, table_id: str, loads: list[list[Any]], add_label: str) -> None:
    imgui.text(title)
    help_marker(
        "k_пуск — кратность пускового тока. Холодильник: 4–6; насос: 3–7; котел/циркуляция: 2–4; "
        "электроника: 1.0–1.3. Инвертор проверяется по сценарию: все нагрузки + пуск самой тяжелой."
    )
    if imgui.begin_table(table_id, 5, 0):
        imgui.table_setup_column("Прибор")
        imgui.table_setup_column("P, Вт")
        imgui.table_setup_column("Часы/нед")
        imgui.table_setup_column("k_пуск")
        imgui.table_setup_column("Действие")
        imgui.table_headers_row()

        to_delete: int | None = None
        for index, load in enumerate(loads):
            if len(load) < 4:
                load.append(1.0)
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            _, load[0] = imgui.input_text(f"##name_{table_id}_{index}", str(load[0]))
            tooltip("Название прибора. Используется в таблицах отчёта и проверке обязательных нагрузок задания.")
            imgui.table_set_column_index(1)
            _, load[1] = imgui.input_float(f"##power_{table_id}_{index}", float(load[1]), format="%.1f")
            load[1] = clamp(load[1], 0.0, 100000.0)
            tooltip("Мощность прибора в ваттах. Увеличение P повышает W_day, емкость АКБ и мощность PV.")
            imgui.table_set_column_index(2)
            _, load[2] = imgui.input_float(f"##hours_{table_id}_{index}", float(load[2]), format="%.1f")
            load[2] = clamp(load[2], 0.0, 168.0)
            tooltip("Часы работы в неделю. 168 ч = работа 24/7. Влияет на недельную энергию P·t.")
            imgui.table_set_column_index(3)
            _, load[3] = imgui.input_float(f"##surge_{table_id}_{index}", float(load[3]), format="%.1f")
            load[3] = clamp(load[3], 1.0, 10.0)
            tooltip("Пусковая кратность. Влияет только на пиковую мощность инвертора, не на энергию.")
            imgui.table_set_column_index(4)
            if imgui.button(f"Удалить##{table_id}_{index}"):
                to_delete = index
        if to_delete is not None:
            loads.pop(to_delete)
        imgui.end_table()

    if imgui.button(add_label):
        loads.append(["Новый прибор", 50.0, 10.0, 1.0])
    tooltip("Добавляет строку нагрузки со стартовыми значениями 50 Вт / 10 ч в неделю.")


def _price_text(price_byn: float) -> str:
    return f"{price_byn:,.0f} BYN"


def _panel_spec_text(name: str) -> str:
    try:
        panel = get_panel(name)
    except Exception:  # noqa: BLE001
        return "Характеристики недоступны."
    return (
        f"{panel.name}\n"
        f"Мощность: {panel.power_w:.0f} Вт\n"
        f"Точка макс. мощности: Vmp {panel.vmp_v:.1f} В, Imp {panel.imp_a:.2f} А\n"
        f"Холостой ход: Voc {panel.voc_v:.1f} В, Isc {panel.isc_a:.2f} А\n"
        f"Технология: {panel.technology}\n"
        f"Темп. коэффициент Voc: {panel.temp_coeff_voc_percent_per_c:.2f} %/°C\n"
        f"Габариты: {panel.dimensions_mm or '—'} мм, вес {panel.weight_kg:g} кг\n"
        f"Цена: {_price_text(panel.price_byn)}\n\n"
        "Как выбирать: чем больше P одного модуля, тем меньше панелей и дешевле монтаж. "
        "Voc важен зимой: N_серии × Voc × k_холода не должен превысить вход MPPT. "
        "Vmp влияет на напряжение стринга: для заряда шины нужен запас Vmp стринга ≥ 1.3 × U системы."
    )


def _battery_spec_text(name: str) -> str:
    try:
        battery = get_battery(name)
    except Exception:  # noqa: BLE001
        return "Характеристики недоступны."
    dod = {"LiFePO4": 0.90, "GEL": 0.55, "AGM": 0.45, "Ni-Cd": 0.70}.get(battery.chemistry, 0.5)
    return (
        f"{battery.name}\n"
        f"Ёмкость: {battery.capacity_ah:.0f} А·ч при {battery.voltage_v:.1f} В "
        f"({battery.capacity_ah * battery.voltage_v / 1000.0:.2f} кВт·ч)\n"
        f"Химия: {battery.chemistry} (DoD {dod:.0%})\n"
        f"Макс. ток заряда: {battery.max_charge_current_a:.0f} А\n"
        f"Макс. ток разряда: {battery.max_discharge_current_a:.0f} А\n"
        f"Вес: {battery.weight_kg:g} кг\n"
        f"Цена: {_price_text(battery.price_byn)}\n\n"
        "Как выбирать: ёмкость в кВт·ч должна покрывать суточное потребление × дни автономии. "
        "LiFePO4: DoD 90 %, ~6000 циклов, дорого, но дешевле на цикл. GEL: DoD 55 %, дешевле сейчас, "
        "быстрее деградирует. AGM: DoD 45 %. Ni-Cd: морозостойкость и 25 лет службы. "
        "Ток заряда PV не должен превышать допустимый для АКБ — иначе батарея кипятится."
    )


def _inverter_spec_text(name: str) -> str:
    try:
        inverter = get_inverter(name)
    except Exception:  # noqa: BLE001
        return "Характеристики недоступны."
    return (
        f"{inverter.name}\n"
        f"Номинальная мощность: {inverter.rated_power_w:.0f} Вт\n"
        f"Пиковая (пусковая) мощность: {inverter.surge_power_w:.0f} Вт\n"
        f"Входное напряжение: {inverter.input_voltage_v} В DC\n"
        f"КПД: {inverter.efficiency:.0%}\n"
        f"Цена: {_price_text(inverter.price_byn)}\n\n"
        "Как выбирать: номинал ≥ 1.25 × суммарная мощность AC-приборов. "
        "Пик ≥ пуск самой тяжёлой нагрузки: холодильник ×4–6, насос ×3–7, компрессор ×4. "
        "Входное напряжение обязано совпадать с напряжением системы. "
        "Избыточная мощность инвертора = лишние деньги и больший ток холостого хода."
    )


def _controller_spec_text(name: str) -> str:
    try:
        controller = get_controller(name)
    except Exception:  # noqa: BLE001
        return "Характеристики недоступны."
    voltages = "/".join(str(v) for v in controller.supported_system_voltages)
    return (
        f"{controller.name}\n"
        f"Тип: {controller.controller_type}\n"
        f"Ток заряда: {controller.charge_current_a:.0f} А\n"
        f"Макс. входное напряжение PV: {controller.max_input_voltage_v:.0f} В\n"
        f"Напряжение системы: {voltages} В\n"
        f"КПД: {controller.efficiency:.0%}\n"
        f"Цена: {_price_text(controller.price_byn)}\n\n"
        "Что это: контроллер заряда «перекачивает» энергию из панелей в АКБ. "
        "MPPT ищет точку максимальной мощности и понижает напряжение (buck), "
        "поэтому Vmp стринга должен быть выше напряжения шины.\n"
        "Как выбирать: ток контроллера ≥ 1.25 × (P_PV / U_системы). "
        "Макс. входное напряжение должно быть выше Voc стринга на морозе — иначе MPPT сгорит."
    )


def _spec_combo(label: str, current_idx: int, items: list[str], spec_fn) -> tuple[bool, int]:
    """Combo box where hovering each item shows its full specification tooltip."""
    imgui.set_next_item_width(-1.0)
    preview = items[current_idx] if 0 <= current_idx < len(items) else "—"
    opened = imgui.begin_combo(label, preview)
    changed = False
    if opened:
        for index, item in enumerate(items):
            selected = index == current_idx
            clicked, _ = imgui.selectable(item, selected)
            if clicked and index != current_idx:
                current_idx = index
                changed = True
            if spec_fn is not None:
                tooltip(spec_fn(item))
            if selected:
                imgui.set_item_default_focus()
        imgui.end_combo()
    return changed, current_idx


def _draw_component_selector(state: AppState) -> None:
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Компоненты системы")

    # Solar panel
    _, state.panel_model_idx = _spec_combo(
        "Солнечная панель", state.panel_model_idx, state.panel_models, _panel_spec_text
    )
    tooltip(_panel_spec_text(state.selected_panel()))
    try:
        panel = get_panel(state.selected_panel())
        imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"   → {panel.power_w:.0f} Вт | Voc {panel.voc_v:.1f} В | {_price_text(panel.price_byn)}")
        tooltip(_panel_spec_text(state.selected_panel()))
    except Exception:  # noqa: BLE001
        pass

    # Battery
    _, state.batt_model_idx = _spec_combo(
        "Аккумулятор / СНЭ", state.batt_model_idx, state.batt_models, _battery_spec_text
    )
    tooltip(_battery_spec_text(state.selected_battery()))
    try:
        battery = get_battery(state.selected_battery())
        imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"   → {battery.voltage_v:.0f} В | {battery.capacity_ah:.0f} А·ч | {_price_text(battery.price_byn)}")
        tooltip(_battery_spec_text(state.selected_battery()))
    except Exception:  # noqa: BLE001
        pass

    imgui.spacing()

    # Inverter
    _, state.auto_inverter = imgui.checkbox("Авто-инвертор", state.auto_inverter)
    tooltip("Автоподбор инвертора по непрерывной и пусковой мощности AC-нагрузок.")
    imgui.same_line()
    if not state.auto_inverter:
        _, state.inverter_model_idx = _spec_combo(
            "Инвертор", state.inverter_model_idx, state.inverter_models, _inverter_spec_text
        )
        tooltip(_inverter_spec_text(state.selected_inverter()))
        try:
            inv = get_inverter(state.selected_inverter())
            imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"   → {inv.rated_power_w:.0f} Вт | {inv.input_voltage_v} В | {_price_text(inv.price_byn)}")
            tooltip(_inverter_spec_text(state.selected_inverter()))
        except Exception:  # noqa: BLE001
            pass
    else:
        selected = state.results.get("inverter_model", "—") if state.results else "—"
        imgui.text(f"Подобран: {selected}")
        if state.results:
            tooltip(_inverter_spec_text(str(state.results.get("inverter_model"))))
            try:
                inv = get_inverter(str(state.results.get("inverter_model")))
                imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"   → {_price_text(inv.price_byn)}")
                tooltip(_inverter_spec_text(str(state.results.get("inverter_model"))))
            except Exception:  # noqa: BLE001
                pass

    # Controller
    _, state.auto_controller = imgui.checkbox("Авто-контроллер", state.auto_controller)
    tooltip("Автоподбор MPPT-контроллера по току заряда и допустимому входному напряжению.")
    imgui.same_line()
    if not state.auto_controller:
        _, state.controller_model_idx = _spec_combo(
            "Контроллер заряда", state.controller_model_idx, state.controller_models, _controller_spec_text
        )
        tooltip(_controller_spec_text(state.selected_controller()))
        try:
            ctrl = get_controller(state.selected_controller())
            imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"   → {ctrl.charge_current_a:.0f} А | {_price_text(ctrl.price_byn)}")
            tooltip(_controller_spec_text(state.selected_controller()))
        except Exception:  # noqa: BLE001
            pass
    else:
        selected = state.results.get("controller_model", "—") if state.results else "—"
        imgui.text(f"Подобран: {selected}")
        if state.results:
            tooltip(_controller_spec_text(str(state.results.get("controller_model"))))
            try:
                ctrl = get_controller(str(state.results.get("controller_model")))
                imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"   → {_price_text(ctrl.price_byn)}")
                tooltip(_controller_spec_text(str(state.results.get("controller_model"))))
            except Exception:  # noqa: BLE001
                pass

    imgui.spacing()

    # DC cable
    _, state.auto_cable = imgui.checkbox("Авто-сечение DC", state.auto_cable)
    tooltip("Автоподбор сечения DC-кабеля по нагреву (ПУЭ) и допустимому падению напряжения 2 %.")
    imgui.same_line()
    if not state.auto_cable:
        _, state.cable_section_idx = imgui.combo("Сечение DC-кабеля", state.cable_section_idx, state.cable_section_options)
        tooltip("Ручной выбор сечения DC-кабеля из ряда ПУЭ. Авто подбирает по нагреву и падению напряжения.")
    else:
        selected = f"{state.results.get('cable_section_mm2', '—'):g} мм²" if state.results else "—"
        imgui.text(f"Подобрано: {selected}")
        tooltip("Сечение, подобранное по току PV-поля, длине трассы и допуску ΔU.")

    # AC cable
    _, state.auto_ac_cable = imgui.checkbox("Авто-сечение AC", state.auto_ac_cable)
    tooltip("Автоподбор сечения AC-кабеля 230 В по току инвертора и допуску ΔU 3 %.")
    imgui.same_line()
    if not state.auto_ac_cable:
        _, state.ac_cable_section_idx = imgui.combo("Сечение AC-кабеля", state.ac_cable_section_idx, state.ac_cable_section_options)
        tooltip("Ручной выбор сечения AC-кабеля 230 В.")
    else:
        selected = f"{state.results.get('ac_cable_section_mm2', '—'):g} мм²" if state.results else "—"
        imgui.text(f"Подобрано: {selected}")
        tooltip("Сечение, подобранное по току AC-выхода, длине трассы и допуску ΔU.")


_IDEAS: tuple[tuple[str, str], ...] = (
    ("Напряжение системы", "Чем мощнее система, тем выше напряжение: до ~1 кВт — 12 В, 1–3 кВт — 24 В, выше — 48 В. "
     "Удвоение напряжения вдвое снижает ток, а сечение кабеля — примерно в 4 раза (потери ~ I²R)."),
    ("Дни автономии", "Каждый день без солнца линейно увеличивает ёмкость АКБ. Для дачи хватает 1–2 дней, "
     "для телекома — 3 и больше. Это самый дорогой параметр: иногда дешевле подрезать нагрузки."),
    ("Холодильник и насосы", "Пусковой ток компрессора в 4–6 раз выше номинала. Инвертор выбирается именно по пуску, "
     "а не по номинальной мощности. k_пуск влияет только на инвертор, не на энергию."),
    ("Энергия важнее мощности", "Счёт идёт за ватт-часы: 100 Вт × 10 ч = 1000 Вт·ч. Часы работы влияют на АКБ и PV "
     "сильнее, чем мощность. Сначала режьте часы — потом мощность."),
    ("DoD и химия АКБ", "LiFePO4 можно разряжать на 90 %, GEL — на 55 %, AGM — на 45 %. "
     "Одна и та же энергия требует вдвое большей свинцовой батареи, чем литиевой."),
    ("PV и климат", "Зимой в Беларуси PSH ~1 ч/сутки, летом ~6. Автономка, рассчитанная на декабрь, "
     "в 5–6 раз мощнее, чем на июль. Реальные системы на зиму делают с генератором или гибридом."),
    ("Контроллер", "MPPT эффективнее PWM на 10–30 %, особенно зимой и при большом разбросе напряжений. "
     "Правило: I_контроллера ≥ 1.25 × P_PV / U_системы; V_in,max > Voc стринга на морозе."),
    ("Стринги панелей", "Модули в серии складывают напряжение, в параллель — ток. "
     "Vmp стринга должен быть выше шины минимум на 15–30 %, иначе MPPT не зарядит АКБ."),
    ("Кабели", "Падение напряжения ~ (2·ρ·L·I)/S. Длинная трасса при 12 В съедает проценты мощности: "
     "поднимайте напряжение или увеличивайте сечение. Допуски: DC 2 %, AC 3 %."),
    ("Экономика", "Самая дорогая часть автономки — АКБ. Если CAPEX не сходится, сначала снижайте дни автономии "
     "и ёмкость, потом мощность PV, и только потом меняйте модели оборудования."),
)


def _draw_ideas() -> None:
    opened = imgui.collapsing_header("💡 Идеи и закономерности (прочитай перед выбором)")
    if not opened:
        return
    imgui.text_colored(
        (0.95, 0.75, 0.2, 1.0),
        "Правила, по которым подбирают систему осмысленно, а не наугад:",
    )
    for title, idea in _IDEAS:
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), f"• {title}")
        tooltip(idea)
        imgui.indent(16.0)
        imgui.text_wrapped(idea)
        imgui.unindent(16.0)
    imgui.separator()


def _draw_diagnostics_summary(state: AppState) -> None:
    if not state.results:
        return
    diagnostics = compute_diagnostics(state, state.results)
    if not diagnostics:
        return

    imgui.separator()
    imgui.text_colored((0.95, 0.65, 0.2, 1.0), "Инженерная диагностика:")
    critical = sum(1 for d in diagnostics if d["level"] == "critical")
    warning = sum(1 for d in diagnostics if d["level"] == "warning")
    if critical:
        imgui.text_colored((0.95, 0.15, 0.15, 1.0), f"Критических сбоев: {critical}")
    if warning:
        imgui.text_colored((0.95, 0.75, 0.15, 1.0), f"Предупреждений: {warning}")
    for item in diagnostics[:5]:
        if item["level"] == "critical":
            imgui.text_colored((0.95, 0.15, 0.15, 1.0), f"• {item['message']}")
        elif item["level"] == "warning":
            imgui.text_colored((0.95, 0.75, 0.15, 1.0), f"• {item['message']}")
        else:
            imgui.text(f"• {item['message']}")
    if len(diagnostics) > 5:
        imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"... и еще {len(diagnostics) - 5} замечаний в инспекторе")


def _draw_project_io(state: AppState) -> None:
    imgui.separator()
    imgui.text("Проект JSON:")
    imgui.text_wrapped(f"Текущий файл: {state.project_file_name}")
    if imgui.button("💾 Сохранить проект как…", size=(250, 34)):
        tooltip("Сохраняет все исходные данные проекта в JSON-файл (нагрузки, климат, оборудование).")
        path = ask_save_json(state.project_file_name)
        if path:
            try:
                saved = save_project(path, state.calculation_payload())
                state.project_file_name = Path(saved).name
                state.status_message = f"Проект сохранен: {saved}"
                state.error_message = ""
            except Exception as exc:  # noqa: BLE001
                state.status_message = ""
                state.error_message = f"Ошибка сохранения проекта: {exc}"
    imgui.same_line()
    if imgui.button("📂 Открыть проект…", size=(220, 34)):
        tooltip("Загружает ранее сохранённый JSON-проект и подставляет все параметры.")
        path = ask_open_json()
        if path:
            try:
                payload = load_project(path)
                state.apply_payload(payload)
                state.project_file_name = Path(path).name
                state.status_message = "Проект загружен. Нажмите «Рассчитать АФС»."
                state.error_message = ""
            except Exception as exc:  # noqa: BLE001
                state.status_message = ""
                state.error_message = f"Ошибка загрузки проекта: {exc}"


def _draw_live_results_summary(state: AppState) -> None:
    if not state.results:
        return
    results = state.results
    economics = results.get("economics", {})
    capex = float(economics.get("capex_byn", 0.0))
    daily_energy = float(results.get("daily_energy_wh", 0.0))
    pv_actual = float(results.get("pv_actual_w", 0.0))
    battery_count = int(results.get("battery_count", 0))
    battery_capacity = float(results.get("battery_capacity_actual", 0.0))
    cost_per_kwh = float(economics.get("cost_per_kwh_byn", 0.0))
    payback = economics.get("simple_payback_years", "—")

    imgui.separator()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Текущий расчёт:")
    imgui.text(f"CAPEX: {capex:,.0f} BYN | Энергия суточная: {daily_energy:.0f} Вт·ч")
    imgui.text(f"Мощность PV: {pv_actual:.0f} Вт | АКБ: {battery_count} шт × {battery_capacity:.0f} А·ч")
    imgui.text(f"Стоимость энергии: {cost_per_kwh:.2f} BYN/кВт·ч | Окупаемость: {payback} лет")


def _draw_climate_summary(state: AppState) -> None:
    """Read-only climate summary used in trainer mode."""
    try:
        if state.use_climate_data:
            psh = get_monthly_psh(state.selected_city(), state.selected_month())
            min_temp = get_min_design_temperature(state.selected_city())
            relief = get_relief_coefficient(state.selected_relief())
            imgui.text_colored(
                (0.4, 0.8, 1.0, 1.0),
                f"Климат задания: {state.selected_city()} / {state.selected_month()} | "
                f"PSH {psh:.2f} ч/сут | Tmin {min_temp:.1f} °C | k рельефа {relief:.2f}",
            )
        else:
            imgui.text_colored(
                (0.4, 0.8, 1.0, 1.0),
                f"Ручной режим: PSH {state.psh:.2f} ч/сут | Tmin {state.min_temperature_c:.1f} °C",
            )
    except Exception as exc:  # noqa: BLE001
        imgui.text_colored((0.95, 0.35, 0.35, 1.0), f"Ошибка климатических данных: {exc}")


def draw(state: AppState) -> None:
    imgui.text_colored((0.9, 0.85, 0.4, 1.0), "Главная страница проектирования АФС")
    imgui.text_wrapped(
        "Изменяйте параметры ниже: каждая цифра сразу влияет на энергобаланс, АКБ, PV-поле, "
        "инвертор, кабели, защиту и экономику. Наведите курсор на поле — будет подсказка."
    )
    imgui.separator()

    # Mode selector
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Режим работы")
    modes = ["design", "trainer"]
    mode_labels = ["Проектирование", "Тренажёр (задания)"]
    current_mode_idx = modes.index(state.mode) if state.mode in modes else 0
    _, current_mode_idx = imgui.combo("Режим", current_mode_idx, mode_labels)
    new_mode = modes[current_mode_idx]
    if new_mode != state.mode:
        state.set_mode(new_mode)
    help_marker(
        "Проектирование — свободный расчёт. "
        "Тренажёр — вам выдаётся задание с бюджетом и ограничениями, нужно подобрать систему."
    )
    imgui.same_line()
    _, state.auto_recalculate = imgui.checkbox("Авто-расчёт", state.auto_recalculate)
    help_marker("Пересчитывать результаты автоматически при изменении параметров.")

    if state.mode == "design":
        _draw_live_results_summary(state)

    _draw_ideas()

    if state.mode == "trainer":
        imgui.spacing()
        imgui.text_colored((0.95, 0.85, 0.35, 1.0), "Выбор задания:")
        _, state.trainer_mission_idx = imgui.combo("Задание", state.trainer_mission_idx, state.missions)
        tooltip(
            "Тренировочное задание: обязательные нагрузки, бюджет и минимальная автономность. "
            "Нужно подобрать систему так, чтобы все критерии были OK."
        )
        imgui.same_line()
        if imgui.button("Применить задание", size=(190, 0)):
            mission = get_mission_by_title(state.missions[state.trainer_mission_idx])
            state.apply_mission(mission)
        tooltip("Загружает нагрузки, климат и автономность из выбранного задания.")
        imgui.same_line()
        if imgui.button("Новое случайное задание", size=(230, 0)):
            import random

            state.trainer_mission_idx = random.randrange(len(state.missions))
            mission = get_mission_by_title(state.missions[state.trainer_mission_idx])
            state.apply_mission(mission)
        tooltip("Выбирает случайное задание и применяет его параметры.")

    if state.mode == "trainer":
        draw_mission_panel(state)

    if state.mode == "design":
        imgui.separator()
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "1. Сценарий и климат")
        _, state.preset_idx = imgui.combo("Сценарий", state.preset_idx, state.presets)
        tooltip("Готовые исходные данные. Применение сценария заменит нагрузки, климат и оборудование.")
        imgui.same_line()
        if imgui.button("Применить сценарий", size=(190, 0)):
            state.apply_preset(state.selected_preset())
        tooltip("Заменяет текущие нагрузки, климат и оборудование значениями сценария.")
        imgui.same_line()
        if imgui.button("⚡ Дача (быстрый старт)", size=(210, 0)):
            state.apply_preset("Дача")
        tooltip("Мгновенно загружает базовый сценарий «Дача» для первого запуска.")

        _, state.use_climate_data = imgui.checkbox("Использовать климатическую модель", state.use_climate_data)
        tooltip("Вкл: PSH и Tmin берутся из города/месяца. Выкл: PSH и Tmin вводятся вручную.")
        if state.use_climate_data:
            _, state.city_idx = imgui.combo("Город", state.city_idx, state.cities)
            tooltip("Город задает месячную инсоляцию PSH и минимальную расчетную температуру.")
            _, state.month_idx = imgui.combo("Расчетный месяц", state.month_idx, state.months)
            tooltip("Для автономной системы критичен худший месяц. Июль дает оптимистичный расчет, декабрь — худший.")
            _, state.relief_idx = imgui.combo("Рельеф/затенение", state.relief_idx, state.reliefs)
            tooltip("Коэффициент уменьшает выработку PV: равнина 1.00, холмы 0.92, город 0.85, лес 0.75.")
            _draw_climate_summary(state)
        else:
            _, state.psh = imgui.input_float("Инсоляция PSH (ч/сутки)", state.psh, format="%.2f")
            state.psh = clamp(state.psh, 0.2, 8.0)
            tooltip("Эквивалентные пиковые солнечные часы. Больше PSH → меньше требуемая мощность PV.")
            _, state.min_temperature_c = imgui.input_float("Мин. температура, °C", state.min_temperature_c, format="%.1f")
            state.min_temperature_c = clamp(state.min_temperature_c, -60.0, 30.0)
            tooltip("Чем холоднее, тем выше Voc PV-стринга. Проверяется, чтобы MPPT не сгорел по входному напряжению.")
    else:
        imgui.separator()
        _draw_climate_summary(state)
        imgui.text_colored((0.6, 0.6, 0.6, 1.0), "В режиме тренажёра климат и нагрузки фиксируются заданием.")

    imgui.separator()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "2. Система и оборудование")
    _, state.voltage_idx = imgui.combo(
        "Напряжение системы (В)", state.voltage_idx, [str(voltage) for voltage in state.voltages]
    )
    tooltip("12 В — малые системы; 24 В — дача/дом; 48 В — дом, насос, телеком. Выше напряжение → меньше ток и сечение.")
    _, state.days_autonomy = imgui.input_float("Дней без солнца (n)", state.days_autonomy, format="%.1f")
    state.days_autonomy = clamp(state.days_autonomy, 0.5, 30.0)
    tooltip("Сильно влияет на емкость АКБ: C треб растет линейно с n. Для старта используйте 1–2 дня.")

    _draw_component_selector(state)

    _, state.inverter_efficiency = imgui.input_float("КПД инвертора", state.inverter_efficiency, format="%.2f")
    state.inverter_efficiency = clamp(state.inverter_efficiency, 0.5, 1.0)
    tooltip("Уменьшает полезную энергию AC. W1 = W_ac/η_inv. Ниже КПД → больше PV и АКБ.")
    _, state.pv_system_efficiency = imgui.input_float("Системный КПД PV", state.pv_system_efficiency, format="%.2f")
    state.pv_system_efficiency = clamp(state.pv_system_efficiency, 0.5, 1.0)
    tooltip("Учитывает температуру, пыль, MPPT и провода. Обычно 0.75–0.82.")
    _, state.cable_length = imgui.input_float("Длина DC-трассы PV/АКБ (м)", state.cable_length, format="%.1f")
    state.cable_length = clamp(state.cable_length, 0.0, 500.0)
    tooltip("Длина в одну сторону. В формуле падения напряжения используется петля 2L.")
    _, state.ac_cable_length = imgui.input_float("Длина AC-трассы 230В (м)", state.ac_cable_length, format="%.1f")
    state.ac_cable_length = clamp(state.ac_cable_length, 0.0, 500.0)
    tooltip("Линия после инвертора. Считается по току P_ac/230 и допуску ΔU 3%.")

    imgui.separator()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "3. Нагрузки")
    _draw_load_table("Нагрузки переменного тока (AC):", "ACTable", state.ac_loads, "➕ Добавить AC нагрузку")
    imgui.spacing()
    _draw_load_table("Нагрузки постоянного тока (DC):", "DCTable", state.dc_loads, "➕ Добавить DC нагрузку")

    imgui.separator()
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "4. Экономика")
    _, state.electricity_tariff_byn_kwh = imgui.input_float(
        "Тариф сети, BYN/кВт·ч", state.electricity_tariff_byn_kwh, format="%.4f"
    )
    state.electricity_tariff_byn_kwh = clamp(state.electricity_tariff_byn_kwh, 0.0, 100.0)
    tooltip("Используется для годовой экономии и простой окупаемости.")
    _, state.project_lifetime_years = imgui.input_float(
        "Срок службы проекта, лет", state.project_lifetime_years, format="%.0f"
    )
    state.project_lifetime_years = clamp(state.project_lifetime_years, 1.0, 40.0)
    tooltip("Используется для удельной стоимости энергии: CAPEX/(годовая энергия × срок службы).")

    errors = state.validation_errors()
    if errors:
        imgui.spacing()
        imgui.text_colored((0.95, 0.35, 0.35, 1.0), "Исправьте поля до расчета:")
        for error in errors:
            imgui.bullet_text(error)

    imgui.spacing()
    if imgui.button("🚀 Рассчитать АФС", size=(300, 42)):
        state.recalculate(force=True)
    tooltip(
        "Запускает полный расчёт: энергобаланс, АКБ, PV-поле, контроллер, "
        "инвертор, кабели, защита, BOM и экономика."
    )

    if state.auto_recalculate:
        state.recalculate(force=False)

    _draw_diagnostics_summary(state)
    _draw_project_io(state)

"""Results tab: engineering specification, protection, economics and exports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from imgui_bundle import imgui

from core.report import export_bom_xlsx, generate_report
from ui.dialogs import ask_save_docx, ask_save_xlsx
from ui.latex import ensure_formula_images, render_dynamic_formula
from ui.state import AppState
from ui.widgets import tooltip


def _value(results: dict[str, Any], key: str, digits: int = 2, suffix: str = "") -> str:
    value = results.get(key)
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _draw_row(name: str, value: str, hint: str = "") -> None:
    imgui.table_next_row()
    imgui.table_set_column_index(0)
    imgui.text(name)
    if hint:
        tooltip(hint)
    imgui.table_set_column_index(1)
    imgui.text(value)
    if hint:
        tooltip(hint)


def _draw_protection(protection: dict[str, Any]) -> None:
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Аппараты защиты:")
    if imgui.begin_table("ProtectionTable", 2, 0):
        imgui.table_setup_column("Цепь")
        imgui.table_setup_column("Рекомендация")
        imgui.table_headers_row()
        rows = (
            ("PV-поле", f"DC MCB {protection.get('pv_array_breaker_a', '—')} А",
             "Автомат отключения солнечного поля. Номинал = 1.25 × ток КЗ стрингов."),
            ("Контроллер → АКБ", f"DC MCB {protection.get('controller_battery_breaker_a', '—')} А",
             "Автомат в цепи заряда АКБ от контроллера. Номинал = 1.25 × ток контроллера."),
            ("Главная цепь АКБ", f"DC MCB {protection.get('battery_main_breaker_a', '—')} А",
             "Главный автомат батареи. Самый большой ток: заряд или разряд на инвертор."),
            ("AC-выход", f"AC MCB {protection.get('ac_output_breaker_a', '—')} А + {protection.get('ac_rcd', '—')}",
             "Автомат линии 230 В и УЗО 30 мА тип A от токов утечки."),
        )
        for name, value, hint in rows:
            _draw_row(name, value, hint)
        imgui.end_table()


def _draw_economics(economics: dict[str, Any]) -> None:
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Экономика:")
    if imgui.begin_table("EconomicsTable", 2, 0):
        imgui.table_setup_column("Показатель")
        imgui.table_setup_column("Значение")
        imgui.table_headers_row()
        rows = (
            ("Оборудование", f"{float(economics.get('equipment_subtotal_byn', 0.0)):,.2f} BYN",
             "Сумма стоимости всех позиций спецификации без монтажа."),
            ("CAPEX с монтажом", f"{float(economics.get('capex_byn', 0.0)):,.2f} BYN",
             "Полные капитальные затраты: оборудование + 12 % на монтаж и материалы."),
            ("Годовая энергия", f"{float(economics.get('annual_energy_kwh', 0.0)):,.2f} кВт·ч",
             "Суточное потребление × 365 дней."),
            ("Стоимость энергии за срок службы", f"{float(economics.get('cost_per_kwh_byn', 0.0)):,.4f} BYN/кВт·ч",
             "CAPEX, делённый на всю энергию за срок службы проекта (аналог LCOE)."),
            ("Годовая экономия", f"{float(economics.get('annual_savings_byn', 0.0)):,.2f} BYN",
             "Годовая энергия × тариф сети. Столько не нужно платить электросети."),
            ("Простая окупаемость", f"{economics.get('simple_payback_years', '—')} лет",
             "CAPEX / годовая экономия. Без учёта деградации и дисконтирования."),
        )
        for name, value, hint in rows:
            _draw_row(name, value, hint)
        imgui.end_table()


def draw(state: AppState) -> None:
    imgui.text("Инженерные результаты, спецификация, защита и экономика:")
    imgui.separator()

    if state.error_message:
        imgui.text_colored((0.95, 0.35, 0.35, 1.0), state.error_message)
        return
    if not state.results:
        imgui.text_colored(
            (0.9, 0.6, 0.2, 1.0),
            "⚠️ Сначала выполните расчет на вкладке «Исходные данные».",
        )
        return

    results = state.results
    if imgui.begin_table("ResTable", 2, 0):
        imgui.table_setup_column("Параметр", imgui.TableColumnFlags_.width_stretch, 2.0)
        imgui.table_setup_column("Значение", imgui.TableColumnFlags_.width_stretch, 1.0)
        imgui.table_headers_row()
        _draw_row("Локация / месяц", f"{results.get('city', '—')} / {results.get('month', '—')}",
                  "Климатические условия расчёта: город и расчётный месяц инсоляции.")
        _draw_row("Суточное энергопотребление", _value(results, "daily_energy_wh", 2, " Вт·ч/сутки"),
                  "Среднесуточная энергия всех нагрузок с учётом КПД инвертора. Определяет ёмкость АКБ и мощность PV.")
        _draw_row(
            "Конфигурация АКБ",
            f"{results.get('battery_series_count', '—')}S × {results.get('battery_parallel_count', '—')}P "
            f"= {results.get('battery_count', '—')} шт.; C={_value(results, 'battery_capacity_actual', 1, ' А·ч')}",
            "S — батарей последовательно (напряжение), P — параллельных строк (ёмкость). "
            "Фактическая ёмкость округляется вверх до кратной ёмкости АКБ.",
        )
        _draw_row("Выбранная АКБ", str(results.get("battery_model", "—")),
                  "Модель аккумулятора из базы. Химия задаёт допустимую глубину разряда DoD.")
        _draw_row("Требуемая мощность PV", _value(results, "p_panel_req", 2, " Вт"),
                  "Минимальная мощность PV-поля для покрытия суточного потребления в расчётном месяце.")
        _draw_row(
            "PV-поле",
            f"{results.get('panel_model', '—')} — {results.get('nm_modules', '—')} шт.; "
            f"{results.get('pv_series_count', '—')}S×{results.get('pv_parallel_strings', '—')}P; "
            f"Voc(cold)={_value(results, 'pv_cold_string_voc', 1, ' В')}",
            "Установленное солнечное поле. Voc(cold) — напряжение стринга на морозе, "
            "оно обязано быть ниже максимального входа контроллера.",
        )
        _draw_row(
            "Контроллер заряда",
            f"{results.get('controller_model', '—')} "
            f"({_value(results, 'controller_current', 0, ' А')}; требуется ≥ {_value(results, 'controller_required_current', 1, ' А')})",
            "MPPT-контроллер. Требуемый ток = ток PV-поля × 1.25 запас.",
        )
        _draw_row(
            "Инвертор",
            f"{results.get('inverter_model', '—')} "
            f"(Pnom={_value(results, 'inverter_rated_w', 0, ' Вт')}; "
            f"Psurge={_value(results, 'inverter_surge_w', 0, ' Вт')}; "
            f"требуется {_value(results, 'inverter_required_continuous_w', 0, '/')}{_value(results, 'inverter_required_surge_w', 0, ' Вт')})",
            "Инвертор выбирается по непрерывной мощности AC-нагрузок и по пусковой мощности "
            "самой тяжёлой нагрузки (обе с запасом 1.25).",
        )
        _draw_row(
            "Кабель DC",
            f"{_value(results, 'cable_section_mm2', 1, ' мм²')}; ΔU={_value(results, 'cable_voltage_drop_v', 3, ' В')} "
            f"({_value(results, 'cable_voltage_drop_percent', 2, ' %')})",
            "Сечение медного DC-кабеля. Проверяется по падению напряжения (допуск 2 %) "
            "и длительно допустимому току с запасом 1.25.",
        )
        _draw_row(
            "Кабель AC",
            f"{_value(results, 'ac_cable_section_mm2', 1, ' мм²')}; ΔU={_value(results, 'ac_cable_voltage_drop_v', 3, ' В')} "
            f"({_value(results, 'ac_cable_voltage_drop_percent', 2, ' %')})",
            "Сечение AC-кабеля 230 В после инвертора. Допуск падения напряжения 3 %.",
        )
        imgui.end_table()

    imgui.spacing()
    _draw_protection(dict(results.get("protection", {})))
    imgui.spacing()
    _draw_economics(dict(results.get("economics", {})))

    warnings = list(results.get("warnings", []))
    if warnings:
        imgui.spacing()
        imgui.text_colored((0.95, 0.65, 0.2, 1.0), "Инженерные предупреждения:")
        for warning in warnings:
            imgui.text_wrapped(f"• {warning}")

    imgui.spacing()
    if imgui.button("💾 Сохранить отчет DOCX как…", size=(320, 36)):
        tooltip("Формирует отчёт по ГОСТ: исходные данные, результаты, BOM, экономика, формулы.")
        path = ask_save_docx(f"PV_Calc_Report_{datetime.now():%Y%m%d_%H%M%S}.docx")
        if path:
            try:
                report_input = state.calculation_payload()
                report_input["panel_power_nominal"] = results.get("panel_power_unit", 0.0)
                report_input["detailed_analysis"] = state.detailed_analysis
                formula_images = ensure_formula_images()
                step_images: dict[int, str] = {}
                for index, latex in enumerate(results.get("steps_latex", [])):
                    asset = render_dynamic_formula(str(latex))
                    if asset:
                        step_images[index] = asset
                saved_path = generate_report(
                    path,
                    report_input,
                    results,
                    formula_images=formula_images,
                    step_images=step_images or None,
                )
                state.status_message = f"Отчет DOCX сохранен: {saved_path}"
                state.error_message = ""
            except Exception as exc:  # noqa: BLE001
                state.status_message = ""
                state.error_message = f"Ошибка генерации DOCX: {exc}"
    if imgui.button("📊 Экспорт BOM в XLSX как…", size=(320, 36)):
        tooltip("Выгружает спецификацию оборудования и экономику в Excel-файл.")
        path = ask_save_xlsx(f"PV_Calc_BOM_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        if path:
            try:
                saved_path = export_bom_xlsx(path, results)
                state.status_message = f"BOM XLSX сохранен: {saved_path}"
                state.error_message = ""
            except Exception as exc:  # noqa: BLE001
                state.status_message = ""
                state.error_message = f"Ошибка экспорта XLSX: {exc}"

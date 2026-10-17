"""Engineering Inspector with LaTeX formulas, variable tooltips and diagnostics.

Provides two presentations:
- draw()          : modal popup (used in design mode)
- draw_side_panel(): regular side window (used in trainer mode)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from imgui_bundle import hello_imgui, imgui

from core.climate import get_monthly_psh
from ui.diagnostics import compute_diagnostics, diagnostics_for_block
from ui.latex import formula_asset
from ui.state import AppState
from ui.widgets import tooltip

_LEVEL_COLORS = {
    "critical": (0.95, 0.15, 0.15, 1.0),
    "warning": (0.95, 0.75, 0.15, 1.0),
    "info": (0.25, 0.65, 0.95, 1.0),
}

_LEVEL_LABELS = {
    "critical": "[КРИТИЧЕСКИЙ СБОЙ]",
    "warning": "[ВНИМАНИЕ]",
    "info": "[ИНФО]",
}


def _fmt(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _var_badge(name: str, value: str, unit: str, description: str, source: str) -> None:
    """Draw a hoverable variable badge with a tooltip."""
    label = f"{name} = {value} {unit}"
    imgui.text_colored((0.1, 0.45, 0.75, 1.0), label)
    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.text_colored((0.9, 0.75, 0.35, 1.0), name)
        imgui.text_wrapped(description)
        imgui.separator()
        imgui.text(f"Значение: {value} {unit}")
        imgui.text_colored((0.6, 0.6, 0.6, 1.0), f"Источник: {source}")
        imgui.end_tooltip()


def _diagnostic_badge(item: dict[str, Any]) -> None:
    level = item.get("level", "info")
    color = _LEVEL_COLORS.get(level, (0.8, 0.8, 0.8, 1.0))
    label = f"{_LEVEL_LABELS.get(level, '[?]')} {item.get('message', '')}"
    imgui.text_colored(color, label)
    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.text_colored((0.9, 0.75, 0.35, 1.0), "Рекомендация")
        imgui.text_wrapped(str(item.get("recommendation", "")))
        imgui.end_tooltip()


def _formula_block(
    title: str,
    formula_key: str,
    variables: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> None:
    imgui.separator()
    imgui.text_colored((0.0, 0.45, 0.75, 1.0), title)

    asset = formula_asset(formula_key)
    if asset:
        max_width = max(80.0, imgui.get_content_region_avail().x - 16.0)
        width, height = _formula_image_size(asset, max_width)
        hello_imgui.image_from_asset(asset, imgui.ImVec2(width, height))
    else:
        imgui.text("[формула недоступна]")

    if variables:
        imgui.text("Переменные:")
        for var in variables:
            imgui.bullet()
            imgui.same_line()
            _var_badge(
                var["name"],
                var["value"],
                var.get("unit", ""),
                var["description"],
                var["source"],
            )

    if diagnostics:
        imgui.text("Диагностика:")
        for item in diagnostics:
            imgui.bullet()
            imgui.same_line()
            _diagnostic_badge(item)


def _energy_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "W AC", "value": _fmt(results.get("total_w_ac")), "unit": "Вт·ч/нед",
         "description": "Энергия AC-нагрузок за неделю. Сумма мощностей, умноженных на часы работы.",
         "source": "Расчет по введенным нагрузкам"},
        {"name": "η инвертора", "value": _fmt(results.get("inverter_efficiency")), "unit": "",
         "description": "КПД инвертора. Доля энергии, которая доходит от АКБ до AC-нагрузок.",
         "source": "Параметр пользователя"},
        {"name": "W DC", "value": _fmt(results.get("total_w_dc")), "unit": "Вт·ч/нед",
         "description": "Энергия DC-нагрузок за неделю.",
         "source": "Расчет по введенным нагрузкам"},
        {"name": "W сут", "value": _fmt(results.get("daily_energy_wh")), "unit": "Вт·ч/сут",
         "description": "Среднесуточное энергопотребление системы.",
         "source": "Расчет"},
    ]
    _formula_block("1. Суточное энергопотребление", "w_day", variables, diagnostics_for_block(diagnostics, "energy"))


def _battery_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "W сут", "value": _fmt(results.get("daily_energy_wh")), "unit": "Вт·ч/сут",
         "description": "Суточное энергопотребление.", "source": "Расчет"},
        {"name": "n", "value": _fmt(results.get("days_autonomy", 2.0), 1), "unit": "дн",
         "description": "Дней автономии без солнца.", "source": "Параметр пользователя"},
        {"name": "U системы", "value": _fmt(results.get("system_voltage")), "unit": "В",
         "description": "Номинальное напряжение системы.", "source": "Параметр пользователя"},
        {"name": "DoD", "value": _fmt(results.get("battery_dod")), "unit": "",
         "description": "Допустимая глубина разряда аккумулятора для выбранной химии.",
         "source": "Справочная константа по химии АКБ"},
        {"name": "k t", "value": "1.00", "unit": "",
         "description": "Температурный коэффициент емкости АКБ.",
         "source": "Справочная константа"},
        {"name": "C треб", "value": _fmt(results.get("battery_capacity_total")), "unit": "А·ч",
         "description": "Требуемая полная емкость аккумуляторной батареи.", "source": "Расчет"},
    ]
    _formula_block("2. Емкость аккумулятора", "c_req", variables, diagnostics_for_block(diagnostics, "battery"))


def _pv_power_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "W сут", "value": _fmt(results.get("daily_energy_wh")), "unit": "Вт·ч/сут",
         "description": "Суточное энергопотребление.", "source": "Расчет"},
        {"name": "PSH", "value": _fmt(results.get("psh")), "unit": "ч/сут",
         "description": "Эквивалентные пиковые солнечные часы в выбранном месяце.",
         "source": "Климатическая модель / параметр пользователя"},
        {"name": "η системы PV", "value": _fmt(results.get("pv_system_efficiency")), "unit": "",
         "description": "Системный КПД PV-цепи (пыль, температуру, провода, MPPT).",
         "source": "Параметр пользователя"},
        {"name": "k рельефа", "value": _fmt(results.get("relief_coefficient")), "unit": "",
         "description": "Коэффициент рельефа и затенения.",
         "source": "Параметр пользователя"},
        {"name": "P PV треб", "value": _fmt(results.get("p_panel_req")), "unit": "Вт",
         "description": "Требуемая мощность PV-поля.", "source": "Расчет"},
    ]
    _formula_block("3. Мощность PV-поля", "p_pv", variables, diagnostics_for_block(diagnostics, "pv"))


def _pv_modules_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "P PV треб", "value": _fmt(results.get("p_panel_req")), "unit": "Вт",
         "description": "Требуемая мощность PV-поля.", "source": "Расчет"},
        {"name": "P панели", "value": _fmt(results.get("panel_power_unit")), "unit": "Вт",
         "description": "Номинальная мощность одного выбранного PV-модуля.",
         "source": "Даташит панели"},
        {"name": "N PV", "value": str(results.get("nm_modules")), "unit": "шт",
         "description": "Количество модулей, округленное вверх.", "source": "Расчет"},
    ]
    _formula_block("4. Количество PV-модулей", "n_pv", variables, diagnostics_for_block(diagnostics, "modules"))


def _string_voc_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "Voc", "value": _fmt(results.get("panel_voc")), "unit": "В",
         "description": "Напряжение холостого хода модуля при STC.",
         "source": "Даташит панели"},
        {"name": "N серии", "value": str(results.get("pv_series_count")), "unit": "шт",
         "description": "Число модулей в серии (в одном стринге).", "source": "Расчет"},
        {"name": "k Voc", "value": _fmt(results.get("panel_temp_coeff_voc")), "unit": "%/°C",
         "description": "Температурный коэффициент напряжения холостого хода.",
         "source": "Даташит панели"},
        {"name": "T min", "value": _fmt(results.get("min_temperature_c", -25.0), 1), "unit": "°C",
         "description": "Минимальная расчетная температура окружающей среды.",
         "source": "Климатическая модель / параметр пользователя"},
        {"name": "Voc холод", "value": _fmt(results.get("pv_cold_string_voc"), 1), "unit": "В",
         "description": "Voc стринга при минимальной температуре.", "source": "Расчет"},
    ]
    _formula_block("5. Проверка холодного Voc", "voc_string", variables, diagnostics_for_block(diagnostics, "string"))


def _inverter_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "P непр", "value": _fmt(results.get("continuous_ac_power_w")), "unit": "Вт",
         "description": "Суммарная номинальная мощность AC-нагрузок.", "source": "Расчет"},
        {"name": "P пуск", "value": _fmt(results.get("surge_ac_power_w")), "unit": "Вт",
         "description": "Пиковая мощность с учетом пускового тока самой тяжелой нагрузки.",
         "source": "Расчет"},
        {"name": "P треб пуск", "value": _fmt(results.get("inverter_required_surge_w")), "unit": "Вт",
         "description": "Требуемая пусковая мощность инвертора с запасом 1.25.", "source": "Расчет"},
        {"name": "Инвертор", "value": str(results.get("inverter_model", "—")), "unit": "",
         "description": "Выбранная модель инвертора.", "source": "Автоподбор / ручной выбор"},
    ]
    _formula_block("6. Инвертор и пусковые токи", "inverter_surge", variables, diagnostics_for_block(diagnostics, "inverter"))


def _cable_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "I", "value": _fmt(results.get("total_panel_current"), 1), "unit": "А",
         "description": "Ток PV-поля / DC-шины.", "source": "Расчет"},
        {"name": "L", "value": _fmt(results.get("cable", {}).length_m, 1), "unit": "м",
         "description": "Длина кабельной трассы в одну сторону.", "source": "Параметр пользователя"},
        {"name": "ΔU доп", "value": _fmt(results.get("cable", {}).max_drop_v, 3), "unit": "В",
         "description": "Допустимое падение напряжения (2% от U_sys).", "source": "Расчет"},
        {"name": "S DC", "value": _fmt(results.get("cable_section_mm2"), 1), "unit": "мм²",
         "description": "Выбранное сечение DC-кабеля.", "source": "Автоподбор / ручной выбор"},
    ]
    _formula_block("7. Кабель DC", "cable", variables, diagnostics_for_block(diagnostics, "cable"))


def _ac_cable_block(results: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    variables = [
        {"name": "I AC", "value": _fmt(results.get("ac_output_current_a"), 2), "unit": "А",
         "description": "Ток на выходе инвертора (AC 230 В).", "source": "Расчет"},
        {"name": "L AC", "value": _fmt(results.get("ac_cable", {}).length_m, 1), "unit": "м",
         "description": "Длина AC-трассы в одну сторону.", "source": "Параметр пользователя"},
        {"name": "ΔU доп", "value": _fmt(results.get("ac_cable", {}).max_drop_v, 3), "unit": "В",
         "description": "Допустимое падение напряжения (3% от 230 В).", "source": "Расчет"},
        {"name": "S AC", "value": _fmt(results.get("ac_cable_section_mm2"), 1), "unit": "мм²",
         "description": "Выбранное сечение AC-кабеля.", "source": "Автоподбор / ручной выбор"},
    ]
    _formula_block("8. Кабель AC 230 В", "cable", variables, diagnostics_for_block(diagnostics, "ac_cable"))


def _protection_block(results: dict[str, Any]) -> None:
    protection = results.get("protection", {})
    imgui.separator()
    imgui.text_colored((0.0, 0.45, 0.75, 1.0), "9. Аппараты защиты")
    imgui.text(f"PV-поле: DC MCB {protection.get('pv_array_breaker_a', '—')} А")
    imgui.text(f"Контроллер → АКБ: DC MCB {protection.get('controller_battery_breaker_a', '—')} А")
    imgui.text(f"Главный АКБ: DC MCB {protection.get('battery_main_breaker_a', '—')} А")
    imgui.text(f"AC-выход: AC MCB {protection.get('ac_output_breaker_a', '—')} А + {protection.get('ac_rcd', '—')}")


def _formula_image_size(asset_path: str, max_width: float) -> tuple[float, float]:
    """Return (width, height) scaled to fit max_width while preserving aspect."""
    try:
        from PIL import Image

        path = Path(__file__).resolve().parent.parent / asset_path
        with Image.open(path) as image:
            width, height = image.size
    except Exception:  # noqa: BLE001
        return max_width, 40.0

    if width <= 0:
        return max_width, 40.0
    if width > max_width:
        scale = max_width / width
        return max_width, height * scale
    return float(width), float(height)


def _formula_text_block(title: str, formula_key: str, description_lines: list[str]) -> None:
    """Draw a compact formula image with a short explanation."""
    imgui.separator()
    imgui.text_colored((0.0, 0.45, 0.75, 1.0), title)
    asset = formula_asset(formula_key)
    if asset:
        max_width = max(80.0, imgui.get_content_region_avail().x - 16.0)
        width, height = _formula_image_size(asset, max_width)
        hello_imgui.image_from_asset(asset, imgui.ImVec2(width, height))
    else:
        imgui.text("[формула недоступна]")
    if description_lines:
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Пояснение:")
        for line in description_lines:
            imgui.text_wrapped(line)


def _diagnostics_summary(diagnostics: list[dict[str, Any]]) -> None:
    if not diagnostics:
        return
    imgui.separator()
    imgui.text_colored((0.95, 0.65, 0.2, 1.0), "Инженерная диагностика:")
    for item in diagnostics:
        level = item.get("level", "info")
        color = _LEVEL_COLORS.get(level, (0.8, 0.8, 0.8, 1.0))
        imgui.text_colored(color, f"• {item.get('message', '')}")
        recommendation = item.get("recommendation")
        if recommendation:
            imgui.text_wrapped(f"   → {recommendation}")


def _v(name: str, value: Any, unit: str, description: str, source: str, digits: int = 2) -> dict[str, Any]:
    """Build a variable badge entry (name, formatted value, hover description)."""
    if isinstance(value, str):
        val_str = value
    else:
        val_str = _fmt(value, digits)
    return {"name": name, "value": val_str, "unit": unit, "description": description, "source": source}


def _academic_calc(state: AppState) -> dict[str, float]:
    """Compute values strictly by the academic (BGUIR methodic) formulas."""
    results = state.results or {}
    u = float(results.get("system_voltage", state.system_voltage()))
    w0 = float(results.get("total_w_ac", 0.0))
    w2 = float(results.get("total_w_dc", 0.0))
    w1 = w0 * 1.2
    e_sut = ((w1 / u) + (w2 / u)) / 7.0 if u > 0 else 0.0
    n = float(state.days_autonomy)
    c = e_sut * n / 0.2
    c_poln = c * 1.2
    c_nom = float(results.get("battery_unit_capacity", 0.0))
    n_akb = c_poln / c_nom if c_nom > 0 else 0.0
    u_akb = float(results.get("battery_unit_voltage", 0.0))
    n_posl = u / u_akb if u_akb > 0 else 0.0
    if state.use_climate_data:
        try:
            e_dek = get_monthly_psh(state.selected_city(), "Декабрь")
        except Exception:  # noqa: BLE001
            e_dek = 0.9
    else:
        e_dek = float(state.psh)
    t_p = e_dek * 0.1 / 31.0
    p = e_sut * 1.2 / t_p if t_p > 0 else 0.0
    p_p = float(results.get("panel_power_unit", 0.0))
    n_m = p / p_p if p_p > 0 else 0.0
    u_m = float(results.get("panel_vmp", 0.0)) or float(results.get("panel_voc", 0.0))
    n_m_ser = u / u_m if u_m > 0 else 0.0
    p_obsh = sum(float(row[1]) for row in state.ac_loads if len(row) > 1) + sum(
        float(row[1]) for row in state.dc_loads if len(row) > 1
    )
    i_load = p_obsh / u if u > 0 else 0.0
    d_u = 0.25
    length = float(state.cable_length)
    r = d_u / (i_load * length) if i_load > 0 and length > 0 else 0.0
    return {
        "u": u, "w0": w0, "w1": w1, "w2": w2, "e_sut": e_sut, "n": n,
        "c": c, "c_poln": c_poln, "c_nom": c_nom, "n_akb": n_akb,
        "u_akb": u_akb, "n_posl": n_posl, "e_dek": e_dek, "t_p": t_p,
        "p": p, "p_p": p_p, "n_m": n_m, "u_m": u_m, "n_m_ser": n_m_ser,
        "p_obsh": p_obsh, "i_load": i_load, "d_u": d_u, "length": length, "r": r,
    }


def _draw_academic_analysis(state: AppState, diagnostics: list[dict[str, Any]]) -> None:
    av = _academic_calc(state)
    imgui.text_colored(
        (0.0, 0.45, 0.75, 1.0),
        "УРОВЕНЬ 1: Академические формулы (Строго по методичке БГУИР, формулы 1.1–1.16)",
    )
    imgui.text_wrapped(
        "Значения считаются по методичке из введённых нагрузок. "
        "Наведите курсор на переменную — покажем её смысл, значение и на что она влияет."
    )

    ac_rows = [row for row in state.ac_loads if len(row) >= 3]
    first = ac_rows[0] if ac_rows else ["—", 0.0, 0.0]
    _formula_block(
        "1. Энергопотребление отдельного прибора (W_i)",
        "wi",
        [
            _v("P_i", float(first[1]), "Вт", f"Мощность прибора «{first[0]}». Чем больше — тем выше недельная энергия, ёмкость АКБ и мощность PV.", "Таблица нагрузок"),
            _v("t", float(first[2]), "ч/нед", "Время работы прибора в неделю. Прямо умножается на мощность.", "Таблица нагрузок"),
            _v("W_i", float(first[1]) * float(first[2]), "Вт·ч/нед", "Недельная энергия этого прибора.", "W_i = P_i · t"),
        ],
        diagnostics_for_block(diagnostics, "energy"),
    )
    _formula_block(
        "2. Суммарная энергия переменного тока (W_0)",
        "w0",
        [
            _v("W_0", av["w0"], "Вт·ч/нед", "Сумма энергий всех AC-приборов. База для учёта потерь инвертора.", "Σ P_i·t (AC)"),
        ],
        diagnostics_for_block(diagnostics, "energy"),
    )
    _formula_block(
        "3. Потери в инверторе (W_1)",
        "w1",
        [
            _v("W_0", av["w0"], "Вт·ч/нед", "Недельная энергия AC.", "Расчёт"),
            _v("1.2", "1.20", "", "Коэффициент потерь (КПД ~80 %). Чем больше потери — тем больше энергии требуется от АКБ.", "Константа методички"),
            _v("W_1", av["w1"], "Вт·ч/нед", "Энергия с учётом потерь в инверторе.", "W_1 = W_0 · 1.2"),
        ],
        diagnostics_for_block(diagnostics, "energy"),
    )
    _formula_block(
        "4. Суточное энергопотребление (E_сут)",
        "e_sut_acad",
        [
            _v("W_1", av["w1"], "Вт·ч/нед", "AC-энергия с потерями.", "Расчёт"),
            _v("W_2", av["w2"], "Вт·ч/нед", "Недельная энергия DC-нагрузок.", "Таблица DC"),
            _v("U", av["u"], "В", "Напряжение системы. Выше U — меньше требуемый ток и ёмкость в А·ч.", "Параметр пользователя"),
            _v("E_сут", av["e_sut"], "А·ч/сут", "Суточное потребление. Ключевой параметр: задаёт ёмкость АКБ и мощность PV.", "((W_1+W_2)/U)/7"),
        ],
        diagnostics_for_block(diagnostics, "energy"),
    )
    _formula_block(
        "5. Расчётная ёмкость АКБ (C)",
        "c_acad",
        [
            _v("E_сут", av["e_sut"], "А·ч/сут", "Суточное потребление.", "Расчёт"),
            _v("n", av["n"], "дн", "Дни автономности. Каждый день линейно увеличивает ёмкость.", "Параметр пользователя"),
            _v("DoD", "0.20", "", "Глубина разряда 20 % (безопасно для свинцовых АКБ).", "Константа методички"),
            _v("C", av["c"], "А·ч", "Расчётная ёмкость батареи.", "C = E_сут·n/0.2"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )
    _formula_block(
        "6. Полная ёмкость АКБ (C_полн)",
        "c_poln_acad",
        [
            _v("C", av["c"], "А·ч", "Расчётная ёмкость.", "Расчёт"),
            _v("k_t", "1.20", "", "Температурный коэффициент: запас ёмкости на холод.", "Константа методички"),
            _v("C_полн", av["c_poln"], "А·ч", "Итоговая требуемая ёмкость.", "C·1.2"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )
    _formula_block(
        "7. Число параллельных АКБ (N_акб)",
        "n_akb_acad",
        [
            _v("C_полн", av["c_poln"], "А·ч", "Требуемая ёмкость.", "Расчёт"),
            _v("C_ном", av["c_nom"], "А·ч", "Ёмкость одного выбранного аккумулятора.", "Даташит АКБ"),
            _v("N_акб", av["n_akb"], "шт", "Сколько батарей нужно в параллель, чтобы покрыть ёмкость.", "C_полн/C_ном"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )
    _formula_block(
        "8. Число последовательных АКБ (N_посл)",
        "n_posl_acad",
        [
            _v("U", av["u"], "В", "Напряжение системы.", "Параметр пользователя"),
            _v("U_акб", av["u_akb"], "В", "Напряжение одной АКБ.", "Даташит АКБ"),
            _v("N_посл", av["n_posl"], "шт", "Сколько батарей последовательно, чтобы набрать U.", "U/U_акб"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )
    _formula_block(
        "9. Пиковые солнечные часы декабря (t_p)",
        "tp_acad",
        [
            _v("E_дек", av["e_dek"], "кВт·ч/м²", "Декабрьская инсоляция. Худший месяц задаёт мощность PV-поля.", "Климатическая модель"),
            _v("t_p", av["t_p"], "ч/сут", "Среднее число пиковых солнечных часов. Меньше — больше панелей.", "E_дек·0.1/31"),
        ],
        diagnostics_for_block(diagnostics, "pv"),
    )
    _formula_block(
        "10. Требуемая мощность солнечной батареи (P)",
        "p_sun_acad",
        [
            _v("E_сут", av["e_sut"], "А·ч/сут", "Суточное потребление.", "Расчёт"),
            _v("t_p", av["t_p"], "ч/сут", "Пиковые часы декабря.", "Расчёт"),
            _v("P", av["p"], "Вт", "Требуемая пиковая мощность PV.", "E_сут·1.2/t_p"),
        ],
        diagnostics_for_block(diagnostics, "pv"),
    )
    _formula_block(
        "11. Общее число модулей (N_m)",
        "nm_acad",
        [
            _v("P", av["p"], "Вт", "Требуемая мощность.", "Расчёт"),
            _v("P_p", av["p_p"], "Вт", "Мощность одного модуля.", "Даташит панели"),
            _v("N_m", av["n_m"], "шт", "Необходимое количество модулей.", "P/P_p"),
        ],
        diagnostics_for_block(diagnostics, "modules"),
    )
    _formula_block(
        "12. Модулей в серии (n_m)",
        "nm_posl_acad",
        [
            _v("U", av["u"], "В", "Напряжение системы.", "Параметр пользователя"),
            _v("U_m", av["u_m"], "В", "Рабочее напряжение модуля (Vmp).", "Даташит панели"),
            _v("n_m", av["n_m_ser"], "шт", "Модулей последовательно для согласования с шиной.", "U/U_m"),
        ],
        diagnostics_for_block(diagnostics, "modules"),
    )
    _formula_block(
        "13. Ток в цепи нагрузки (I)",
        "i_load_acad",
        [
            _v("P_общ", av["p_obsh"], "Вт", "Суммарная установленная мощность всех нагрузок.", "AC + DC таблицы"),
            _v("U", av["u"], "В", "Напряжение системы.", "Параметр пользователя"),
            _v("I", av["i_load"], "А", "Расчётный ток линии.", "P_общ/U"),
        ],
        diagnostics_for_block(diagnostics, "cable"),
    )
    _formula_block(
        "14. Сопротивление кабеля (R)",
        "r_cable_acad",
        [
            _v("ΔU", av["d_u"], "В", "Допустимое падение напряжения (≤0.25 В).", "Константа методички"),
            _v("I", av["i_load"], "А", "Ток линии.", "Расчёт"),
            _v("L", av["length"], "м", "Длина трассы. Длиннее — больше потери.", "Параметр пользователя"),
            _v("R", av["r"], "Ом/м", "Предельное погонное сопротивление провода.", "ΔU/(I·L)"),
        ],
        diagnostics_for_block(diagnostics, "cable"),
    )


def _draw_detailed_analysis(state: AppState, diagnostics: list[dict[str, Any]]) -> None:
    results = state.results or {}
    av = _academic_calc(state)
    imgui.text_colored(
        (0.0, 0.45, 0.75, 1.0),
        "Детальный инженерный анализ (два уровня)",
    )
    imgui.text_wrapped(
        "Уровень 1 — строго по методичке БГУИР. Уровень 2 — профессиональный расчёт: реальный КПД, DoD по химии АКБ, "
        "PSH, пусковые токи и проверка холодного Voc. Наведите курсор на переменную — покажем смысл и влияние."
    )

    yellow = (0.95, 0.85, 0.35, 1.0)

    imgui.text_colored(yellow, "Блок 1. Энергопотребление и суточный баланс")
    _formula_block(
        "Уровень 1. Академический (E_сут)",
        "e_sut_acad",
        [
            _v("W_1", av["w1"], "Вт·ч/нед", "AC-энергия с коэффициентом 1.2.", "Методичка"),
            _v("W_2", av["w2"], "Вт·ч/нед", "Недельная энергия DC.", "Таблица DC"),
            _v("U", av["u"], "В", "Напряжение системы.", "Параметр пользователя"),
            _v("E_сут", av["e_sut"], "А·ч/сут", "Суточное потребление по методичке.", "((W_1+W_2)/U)/7"),
        ],
        diagnostics_for_block(diagnostics, "energy"),
    )
    _formula_block(
        "Уровень 2. Профессиональный (W_сут)",
        "w_sut_prof",
        [
            _v("W_перем", results.get("total_w_ac", 0.0), "Вт·ч/нед", "Недельная энергия AC-нагрузок.", "Таблица AC"),
            _v("η_inv", results.get("inverter_efficiency", 0.0), "", "Реальный КПД инвертора (85–95 %). Ниже КПД — больше потерь, больше АКБ и PV.", "Параметр пользователя", 2),
            _v("W_пост", results.get("total_w_dc", 0.0), "Вт·ч/нед", "Недельная энергия DC-нагрузок.", "Таблица DC"),
            _v("W_сут", results.get("daily_energy_wh", 0.0), "Вт·ч/сут", "Суточный энергобаланс с реальным КПД.", "(W_перем/η_inv + W_пост)/7"),
        ],
        diagnostics_for_block(diagnostics, "energy"),
    )

    imgui.text_colored(yellow, "Блок 2. Ёмкость и конфигурация АКБ")
    _formula_block(
        "Уровень 1. Академический (C_полн)",
        "c_poln_acad",
        [
            _v("E_сут", av["e_sut"], "А·ч/сут", "Суточное потребление.", "Методичка"),
            _v("n", av["n"], "дн", "Дни автономности.", "Параметр пользователя"),
            _v("DoD", "0.20", "", "Фиксированная глубина разряда 20 %.", "Константа методички"),
            _v("C_полн", av["c_poln"], "А·ч", "Ёмкость с запасом 1.2.", "C·1.2"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )
    _formula_block(
        "Уровень 2. Профессиональный (C_треб)",
        "c_req_prof",
        [
            _v("W_сут", results.get("daily_energy_wh", 0.0), "Вт·ч/сут", "Суточное потребление.", "Расчёт"),
            _v("n", float(state.days_autonomy), "дн", "Дни автономности. Линейно увеличивает ёмкость.", "Параметр пользователя"),
            _v("U_сист", results.get("system_voltage", 0.0), "В", "Напряжение системы. Выше — меньше ёмкость в А·ч при той же энергии.", "Параметр пользователя"),
            _v("DoD", results.get("battery_dod", 0.0), "", "Глубина разряда по химии: LiFePO4 0.90 / GEL 0.55 / AGM 0.45. Больше DoD — меньше нужная ёмкость.", "Химия АКБ"),
            _v("k_темп", "1.00", "", "Температурная поправка ёмкости.", "Константа"),
            _v("C_треб", results.get("battery_capacity_total", 0.0), "А·ч", "Требуемая ёмкость с учётом DoD.", "W_сут·n/(U·DoD·k_t)"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )
    _formula_block(
        "Конфигурация АКБ (N_общ)",
        "n_total_prof",
        [
            _v("U_сист", results.get("system_voltage", 0.0), "В", "Напряжение системы.", "Параметр пользователя"),
            _v("U_акб", results.get("battery_unit_voltage", 0.0), "В", "Напряжение одной АКБ.", "Даташит АКБ"),
            _v("C_треб", results.get("battery_capacity_total", 0.0), "А·ч", "Требуемая ёмкость.", "Расчёт"),
            _v("C_акб", results.get("battery_unit_capacity", 0.0), "А·ч", "Ёмкость одной АКБ.", "Даташит АКБ"),
            _v("N_общ", str(results.get("battery_count", "—")), "шт", "Итого батарей (серия × параллель). Определяет цену и надёжность системы.", f"{results.get('battery_series_count', 0)}S × {results.get('battery_parallel_count', 0)}P"),
        ],
        diagnostics_for_block(diagnostics, "battery"),
    )

    imgui.text_colored(yellow, "Блок 3. Фотоэлектрический генератор")
    _formula_block(
        "Уровень 1. Академический (P)",
        "p_sun_acad",
        [
            _v("E_сут", av["e_sut"], "А·ч/сут", "Суточное потребление.", "Методичка"),
            _v("t_p", av["t_p"], "ч/сут", "Пиковые часы декабря.", "E_дек·0.1/31"),
            _v("P", av["p"], "Вт", "Требуемая мощность PV по методичке.", "E_сут·1.2/t_p"),
        ],
        diagnostics_for_block(diagnostics, "pv"),
    )
    _formula_block(
        "Уровень 2. Профессиональный (P_панелей)",
        "p_pv_prof",
        [
            _v("W_сут", results.get("daily_energy_wh", 0.0), "Вт·ч/сут", "Суточное потребление.", "Расчёт"),
            _v("PSH", results.get("psh", 0.0), "ч/сут", "Пиковые солнечные часы месяца. Меньше света — больше панелей.", "Климат / пользователь"),
            _v("η_сист", results.get("pv_system_efficiency", 0.0), "", "Системные потери: пыль, нагрев, MPPT, провода. Ниже — больше требуемая мощность.", "Параметр пользователя", 2),
            _v("k_рельеф", results.get("relief_coefficient", 1.0), "", "Затенение рельефа. Меньше — больше требуемая мощность.", "Параметр пользователя", 2),
            _v("P_панелей", results.get("p_panel_req", 0.0), "Вт", "Требуемая мощность PV-поля.", "W_сут/(PSH·η·k)"),
        ],
        diagnostics_for_block(diagnostics, "pv"),
    )
    _formula_block(
        "Количество модулей (N_панелей)",
        "n_pv_prof",
        [
            _v("P_панелей", results.get("p_panel_req", 0.0), "Вт", "Требуемая мощность.", "Расчёт"),
            _v("P_модуля", results.get("panel_power_unit", 0.0), "Вт", "Мощность одного модуля.", "Даташит панели"),
            _v("N_панелей", str(results.get("nm_modules", "—")), "шт", "Округление вверх. Больше модулей — дороже, но надёжнее зимой.", "ceil(P_панелей/P_модуля)"),
        ],
        diagnostics_for_block(diagnostics, "modules"),
    )

    imgui.text_colored(yellow, "Блок 4. Климатические и пусковые режимы")
    _formula_block(
        "Холодный холостой ход (Voc стринга)",
        "voc_prof",
        [
            _v("U_xx", results.get("panel_voc", 0.0), "В", "Voc модуля при STC.", "Даташит панели"),
            _v("N_посл", str(results.get("pv_series_count", "—")), "шт", "Модулей в стринге.", "Расчёт"),
            _v("α_Uxx", results.get("panel_temp_coeff_voc", 0.0), "%/°C", "Температурный коэффициент Voc.", "Даташит панели"),
            _v("T_min", results.get("min_temperature_c", -25.0), "°C", "Минимальная температура. Холоднее — выше Voc.", "Климат", 1),
            _v("U_mppt,max", results.get("controller_max_input_voltage", 0.0), "В", "Максимум входа контроллера. Превышение выведет MPPT из строя.", "Даташит контроллера", 0),
            _v("U_xx,стр", results.get("pv_cold_string_voc", 0.0), "В", "Voc стринга на морозе. Обязан быть ниже U_mppt,max.", "Расчёт", 1),
        ],
        diagnostics_for_block(diagnostics, "string"),
    )
    _formula_block(
        "Пусковые токи инвертора (P_пуск)",
        "p_pusk_prof",
        [
            _v("P_непр", results.get("continuous_ac_power_w", 0.0), "Вт", "Суммарная номинальная мощность AC-нагрузок.", "Расчёт"),
            _v("P_пуск", results.get("surge_ac_power_w", 0.0), "Вт", "Пик с пуском самой тяжёлой нагрузки (k_пуск). Определяет размер инвертора.", "Расчёт"),
            _v("Инвертор", str(results.get("inverter_model", "—")), "", "Выбранная модель. Psurge должна покрывать пуск, иначе отключение.", "Автоподбор"),
        ],
        diagnostics_for_block(diagnostics, "inverter"),
    )
    _formula_block(
        "Сечение кабеля по ПУЭ (S)",
        "s_cable_prof",
        [
            _v("I", results.get("total_panel_current", 0.0), "А", "Ток линии.", "Расчёт", 1),
            _v("L", float(results.get("cable").length_m) if results.get("cable") else 0.0, "м", "Длина трассы в одну сторону (петля 2L).", "Параметр пользователя", 1),
            _v("ΔU_доп", float(results.get("cable").max_drop_v) if results.get("cable") else 0.0, "В", "Допустимое падение (2 % от U_сист).", "Расчёт", 3),
            _v("S", results.get("cable_section_mm2", 0.0), "мм²", "Выбранное сечение. Больше — дороже, но меньше потери.", "Автоподбор / ручной", 1),
        ],
        diagnostics_for_block(diagnostics, "cable"),
    )


def _draw_inspector_content(state: AppState, diagnostics: list[dict[str, Any]]) -> None:
    """Shared content between modal and side panel."""
    if state.detailed_analysis:
        _draw_detailed_analysis(state, diagnostics)
    else:
        _draw_academic_analysis(state, diagnostics)
    _protection_block(state.results)
    _diagnostics_summary(diagnostics)


def draw(state: AppState) -> None:
    """Modal inspector popup (design mode)."""
    if state.show_inspector:
        imgui.open_popup("Инженерный инспектор расчета")
        state.show_inspector = False

    visible, _ = imgui.begin_popup_modal(
        "Инженерный инспектор расчета",
        None,
        imgui.WindowFlags_.none,
    )
    if not visible:
        return

    if not state.results:
        imgui.text("Нет результатов расчета.")
        if imgui.button("Закрыть", size=(120, 30)):
            imgui.close_current_popup()
        imgui.end_popup()
        return

    diagnostics = compute_diagnostics(state, state.results)

    imgui.begin_child("InspectorScroll", imgui.ImVec2(900, 620), 1)
    _draw_inspector_content(state, diagnostics)
    imgui.separator()
    if imgui.button("Закрыть инспектор", size=(220, 36)):
        imgui.close_current_popup()
    imgui.end_child()
    imgui.end_popup()


def draw_side_panel(state: AppState) -> None:
    """Side-by-side inspector panel (trainer mode)."""
    if not state.results:
        return

    diagnostics = compute_diagnostics(state, state.results)
    imgui.set_next_window_size((320, 420), imgui.Cond_.once)
    imgui.begin(
        "Инженерный инспектор",
        flags=imgui.WindowFlags_.no_collapse,
    )
    _draw_inspector_content(state, diagnostics)
    imgui.end()

"""GOST-style black-on-white structural diagram drawn with ImDrawList."""

from __future__ import annotations

from datetime import datetime

from imgui_bundle import imgui

from ui.dialogs import ask_save_pdf
from ui.scheme_export import export_scheme_pdf
from ui.state import AppState


def _col(r: float, g: float, b: float, a: float = 1.0) -> int:
    return imgui.get_color_u32((r, g, b, a))


def _rect(draw_list, x0: float, y0: float, x1: float, y1: float, fill=None) -> None:
    fill_color = _col(1.0, 1.0, 1.0) if fill is None else fill
    draw_list.add_rect_filled((x0, y0), (x1, y1), fill_color, 0.0)
    draw_list.add_rect((x0, y0), (x1, y1), _col(0.0, 0.0, 0.0), 0.0)
    draw_list.add_rect((x0 + 1.0, y0 + 1.0), (x1 - 1.0, y1 - 1.0), _col(0.0, 0.0, 0.0), 0.0)


def _text(draw_list, x: float, y: float, text: str) -> None:
    draw_list.add_text((x, y), _col(0.0, 0.0, 0.0), text)


def _line(draw_list, x0: float, y0: float, x1: float, y1: float) -> None:
    draw_list.add_line((x0, y0), (x1, y1), _col(0.0, 0.0, 0.0), 2.0)


def _arrow(draw_list, x0: float, y0: float, x1: float, y1: float) -> None:
    _line(draw_list, x0, y0, x1, y1)
    # Simple GOST-like arrow head made from two strokes.
    if abs(x1 - x0) >= abs(y1 - y0):
        sign = 1.0 if x1 >= x0 else -1.0
        _line(draw_list, x1, y1, x1 - sign * 10.0, y1 - 6.0)
        _line(draw_list, x1, y1, x1 - sign * 10.0, y1 + 6.0)
    else:
        sign = 1.0 if y1 >= y0 else -1.0
        _line(draw_list, x1, y1, x1 - 6.0, y1 - sign * 10.0)
        _line(draw_list, x1, y1, x1 + 6.0, y1 - sign * 10.0)


def _block(draw_list, x: float, y: float, w: float, h: float, code: str, title: str, lines: list[str]) -> None:
    _rect(draw_list, x, y, x + w, y + h)
    _text(draw_list, x + 8, y + 6, code)
    _text(draw_list, x + 58, y + 6, title)
    _line(draw_list, x, y + 26, x + w, y + 26)
    for index, line in enumerate(lines):
        _text(draw_list, x + 8, y + 34 + index * 18, line)


def _stamp(draw_list, x: float, y: float) -> None:
    # Simplified main inscription (основная надпись) in GOST style.
    w, h = 700.0, 74.0
    _rect(draw_list, x, y, x + w, y + h)
    for dx in (70.0, 130.0, 250.0, 360.0, 470.0):
        _line(draw_list, x + dx, y, x + dx, y + h)
    for dy in (24.0, 49.0):
        _line(draw_list, x, y + dy, x + w, y + dy)
    _text(draw_list, x + 8, y + 6, "Изм.")
    _text(draw_list, x + 78, y + 6, "Лист")
    _text(draw_list, x + 138, y + 6, "№ докум.")
    _text(draw_list, x + 258, y + 6, "Подп.")
    _text(draw_list, x + 368, y + 6, "Дата")
    _text(draw_list, x + 478, y + 6, "PV-Calc Pro")
    _text(draw_list, x + 8, y + 30, "Разраб.")
    _text(draw_list, x + 8, y + 55, "Пров.")
    _text(draw_list, x + 138, y + 30, "АФС-САПР-001")
    _text(draw_list, x + 478, y + 30, "Автономная фотоэлектрическая система")
    _text(draw_list, x + 478, y + 55, "Лист 1")


def draw(state: AppState) -> None:
    if imgui.button("💾 Сохранить схему в PDF как…", size=(300, 30)):
        path = ask_save_pdf(f"PV_Calc_Scheme_{datetime.now():%Y%m%d_%H%M%S}.pdf")
        if path:
            try:
                saved = export_scheme_pdf(path, state)
                state.status_message = f"Схема сохранена в PDF: {saved}"
                state.error_message = ""
            except Exception as exc:  # noqa: BLE001
                state.status_message = ""
                state.error_message = f"Ошибка экспорта PDF: {exc}"
    imgui.separator()

    results = state.results or {}
    draw_list = imgui.get_window_draw_list()
    pos = imgui.get_cursor_screen_pos()
    x, y = pos.x + 18, pos.y + 24

    # White GOST sheet with black border.
    draw_list.add_rect_filled((x - 12, y - 18), (x + 1068, y + 610), _col(1.0, 1.0, 1.0), 0.0)
    _rect(draw_list, x - 12, y - 18, x + 1068, y + 610)
    _text(draw_list, x + 330, y - 8, "СТРУКТУРНАЯ СХЕМА АВТОНОМНОЙ ФОТОЭЛЕКТРИЧЕСКОЙ СИСТЕМЫ")

    panel_model = str(results.get("panel_model", "PV module"))
    battery_model = str(results.get("battery_model", "Battery"))
    controller_model = str(results.get("controller_model", "MPPT controller"))
    inverter_model = str(results.get("inverter_model", "Inverter"))
    pv_text = f"{results.get('nm_modules', 0)} шт.; {results.get('pv_series_count', 0)}S x {results.get('pv_parallel_strings', 0)}P"
    batt_text = f"{results.get('battery_count', 0)} шт.; {results.get('battery_series_count', 0)}S x {results.get('battery_parallel_count', 0)}P"
    dc_cable = f"Кабель DC Cu {float(results.get('cable_section_mm2', 0.0)):g} мм²"
    ac_cable = f"Кабель AC Cu {float(results.get('ac_cable_section_mm2', 0.0)):g} мм²"

    _block(
        draw_list,
        x + 20,
        y + 70,
        220,
        118,
        "PV1",
        "Солнечная батарея",
        [pv_text, panel_model[:30], f"Voc cold: {float(results.get('pv_cold_string_voc', 0.0)):.1f} В", "Клеммы: PV+ / PV-"],
    )
    _block(
        draw_list,
        x + 330,
        y + 70,
        250,
        150,
        "A1",
        "MPPT-контроллер",
        [controller_model[:34], f"Icharge: {float(results.get('controller_current', 0.0)):.0f} А", "A0: U_batt ADC", "D9/PWM: charge switch", "I2C/SPI/UART: телеметрия", "BAT+ / BAT-"],
    )
    _block(
        draw_list,
        x + 330,
        y + 270,
        250,
        118,
        "GB1",
        "Аккумуляторная батарея",
        [battery_model[:34], batt_text, f"C факт: {float(results.get('battery_capacity_actual', 0.0)):.1f} Ач", "Клеммы: BAT+ / BAT-"],
    )
    _block(
        draw_list,
        x + 680,
        y + 70,
        210,
        118,
        "G1",
        "Инвертор DC/AC",
        [inverter_model[:28], f"Вход: DC {state.system_voltage():.0f} В", "Выход: AC 230 В 50 Гц", dc_cable],
    )
    _block(
        draw_list,
        x + 922,
        y + 70,
        143,
        150,
        "ZL1",
        "Нагрузки",
        [f"AC: {len(state.ac_loads)}", f"DC: {len(state.dc_loads)}", "230 В AC", "Шина DC", ac_cable.replace("Кабель AC", "AC")],
    )

    _arrow(draw_list, x + 240, y + 128, x + 330, y + 128)
    _text(draw_list, x + 252, y + 106, "DC PV")
    _arrow(draw_list, x + 455, y + 220, x + 455, y + 270)
    _text(draw_list, x + 466, y + 240, "Заряд")
    _arrow(draw_list, x + 580, y + 128, x + 680, y + 128)
    _text(draw_list, x + 596, y + 106, "Шина DC")
    _arrow(draw_list, x + 890, y + 128, x + 917, y + 128)
    _text(draw_list, x + 893, y + 106, "230 В")

    _stamp(draw_list, x + 20, y + 500)
    imgui.dummy((1068, 640))

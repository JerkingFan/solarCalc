"""Interactive equipment catalog tab."""

from __future__ import annotations

from imgui_bundle import imgui

from core.database import BATTERIES, CHARGE_CONTROLLERS, INVERTERS, SOLAR_PANELS


def _draw_table(table_id: str, headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    if imgui.begin_table(table_id, len(headers), 0):
        for header in headers:
            imgui.table_setup_column(header)
        imgui.table_headers_row()
        for values in rows:
            imgui.table_next_row()
            for column, value in enumerate(values):
                imgui.table_set_column_index(column)
                imgui.text(value)
        imgui.end_table()


def _draw_panels() -> None:
    rows = [
        (
            panel.name,
            f"{panel.power_w:.0f}",
            f"{panel.vmp_v:.1f}",
            f"{panel.voc_v:.1f}",
            f"{panel.imp_a:.2f}",
            f"{panel.isc_a:.2f}",
            panel.technology,
            f"{panel.temp_coeff_voc_percent_per_c:.2f}",
            f"{panel.price_byn:.0f}",
        )
        for panel in SOLAR_PANELS
    ]
    _draw_table(
        "PanelsCatalog",
        ("Модель", "P, Вт", "Vmp, В", "Voc, В", "Imp, А", "Isc, А", "Технология", "kVoc, %/°C", "Цена, BYN"),
        rows,
    )


def _draw_batteries() -> None:
    rows = [
        (
            battery.name,
            f"{battery.capacity_ah:.0f}",
            f"{battery.voltage_v:.1f}",
            battery.chemistry,
            f"{battery.max_charge_current_a:.0f}",
            f"{battery.max_discharge_current_a:.0f}",
            f"{battery.price_byn:.0f}",
        )
        for battery in BATTERIES
    ]
    _draw_table(
        "BatteriesCatalog",
        ("Модель", "А·ч", "В", "Химия", "I зар. max", "I раз. max", "Цена, BYN"),
        rows,
    )


def _draw_controllers() -> None:
    rows = [
        (
            controller.name,
            f"{controller.charge_current_a:.0f}",
            f"{controller.max_input_voltage_v:.0f}",
            "/".join(str(voltage) for voltage in controller.supported_system_voltages),
            controller.controller_type,
            f"{controller.efficiency:.2f}",
            f"{controller.price_byn:.0f}",
        )
        for controller in CHARGE_CONTROLLERS
    ]
    _draw_table(
        "ControllersCatalog",
        ("Модель", "I заряда, А", "Vin max, В", "U системы", "Тип", "КПД", "Цена, BYN"),
        rows,
    )


def _draw_inverters() -> None:
    rows = [
        (
            inverter.name,
            f"{inverter.rated_power_w:.0f}",
            f"{inverter.surge_power_w:.0f}",
            f"{inverter.input_voltage_v}",
            f"{inverter.efficiency:.2f}",
            f"{inverter.price_byn:.0f}",
        )
        for inverter in INVERTERS
    ]
    _draw_table(
        "InvertersCatalog",
        ("Модель", "P ном, Вт", "P пик, Вт", "U вход, В", "КПД", "Цена, BYN"),
        rows,
    )


def draw() -> None:
    imgui.text("Единая база оборудования, используемая расчетным ядром:")
    imgui.separator()

    if imgui.begin_tab_bar("CatalogSubTabs"):
        tabs = (
            ("☀️ Солнечные панели", "PanelsScrollRegion", _draw_panels),
            ("🔋 АКБ и СНЭ", "BatteriesScrollRegion", _draw_batteries),
            ("🎛️ Контроллеры", "ControllersScrollRegion", _draw_controllers),
            ("🔌 Инверторы", "InvertersScrollRegion", _draw_inverters),
        )
        for label, child_id, callback in tabs:
            opened, _ = imgui.begin_tab_item(label)
            if opened:
                imgui.begin_child(child_id, imgui.ImVec2(0, 500), 1)
                callback()
                imgui.end_child()
                imgui.end_tab_item()
        imgui.end_tab_bar()

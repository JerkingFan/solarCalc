"""Export the GOST-style structural scheme to a vector PDF.

Replicates the ImGui draw-list layout (ui/view_scheme.py) with matplotlib so the
scheme can be saved as a crisp vector document. Requires matplotlib.
"""

from __future__ import annotations

from pathlib import Path

from ui.state import AppState

SHEET_W = 1080.0
SHEET_H = 630.0


def export_scheme_pdf(filename: str | Path, state: AppState) -> Path:
    """Render the structural scheme to PDF and return the saved path."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib.backends.backend_pdf import FigureCanvasPdf
        from matplotlib.figure import Figure
        from matplotlib.patches import Rectangle
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Для экспорта схемы в PDF установите matplotlib: pip install matplotlib"
        ) from exc

    results = state.results or {}

    fig = Figure(figsize=(SHEET_W / 100.0, SHEET_H / 100.0), dpi=200)
    canvas = FigureCanvasPdf(fig)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(-14.0, 1070.0)
    ax.set_ylim(612.0, -22.0)  # inverted Y to match ImGui screen coordinates
    ax.axis("off")

    def rect(x0: float, y0: float, x1: float, y1: float) -> None:
        ax.add_patch(
            Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="white", edgecolor="black", linewidth=1.4)
        )
        ax.add_patch(
            Rectangle(
                (x0 + 1.0, y0 + 1.0),
                x1 - x0 - 2.0,
                y1 - y0 - 2.0,
                facecolor="none",
                edgecolor="black",
                linewidth=0.8,
            )
        )

    def text(x: float, y: float, s: str, size: float = 9.0, bold: bool = False) -> None:
        ax.text(
            x,
            y,
            s,
            fontsize=size,
            family="DejaVu Sans",
            fontweight="bold" if bold else "normal",
            ha="left",
            va="top",
            color="black",
        )

    def line(x0: float, y0: float, x1: float, y1: float, lw: float = 1.4) -> None:
        ax.plot([x0, x1], [y0, y1], color="black", linewidth=lw, solid_capstyle="butt")

    def arrow(x0: float, y0: float, x1: float, y1: float) -> None:
        line(x0, y0, x1, y1)
        if abs(x1 - x0) >= abs(y1 - y0):
            sign = 1.0 if x1 >= x0 else -1.0
            line(x1, y1, x1 - sign * 10.0, y1 - 6.0)
            line(x1, y1, x1 - sign * 10.0, y1 + 6.0)
        else:
            sign = 1.0 if y1 >= y0 else -1.0
            line(x1, y1, x1 - 6.0, y1 - sign * 10.0)
            line(x1, y1, x1 + 6.0, y1 - sign * 10.0)

    def block(x: float, y: float, w: float, h: float, code: str, title: str, lines: list[str]) -> None:
        rect(x, y, x + w, y + h)
        text(x + 8, y + 6, code, size=10.0, bold=True)
        text(x + 58, y + 6, title, size=10.0, bold=True)
        line(x, y + 26, x + w, y + 26)
        for index, s in enumerate(lines):
            text(x + 8, y + 34 + index * 18, s, size=8.5)

    # White GOST sheet with black border.
    ax.add_patch(Rectangle((-12, -18), 1080, 628, facecolor="white", edgecolor="none", zorder=-10))
    rect(-12, -18, 1068, 610)
    text(330, -8, "СТРУКТУРНАЯ СХЕМА АВТОНОМНОЙ ФОТОЭЛЕКТРИЧЕСКОЙ СИСТЕМЫ", size=11.0, bold=True)

    panel_model = str(results.get("panel_model", "PV module"))
    battery_model = str(results.get("battery_model", "Battery"))
    controller_model = str(results.get("controller_model", "MPPT controller"))
    inverter_model = str(results.get("inverter_model", "Inverter"))
    pv_text = f"{results.get('nm_modules', 0)} шт.; {results.get('pv_series_count', 0)}S x {results.get('pv_parallel_strings', 0)}P"
    batt_text = f"{results.get('battery_count', 0)} шт.; {results.get('battery_series_count', 0)}S x {results.get('battery_parallel_count', 0)}P"
    dc_cable = f"Кабель DC Cu {float(results.get('cable_section_mm2', 0.0)):g} мм²"
    ac_cable = f"Кабель AC Cu {float(results.get('ac_cable_section_mm2', 0.0)):g} мм²"

    block(
        20, 70, 220, 118,
        "PV1",
        "Солнечная батарея",
        [pv_text, panel_model[:30], f"Voc cold: {float(results.get('pv_cold_string_voc', 0.0)):.1f} В", "Клеммы: PV+ / PV-"],
    )
    block(
        330, 70, 250, 150,
        "A1",
        "MPPT-контроллер",
        [controller_model[:34], f"Icharge: {float(results.get('controller_current', 0.0)):.0f} А", "A0: U_batt ADC", "D9/PWM: charge switch", "I2C/SPI/UART: телеметрия", "BAT+ / BAT-"],
    )
    block(
        330, 270, 250, 118,
        "GB1",
        "Аккумуляторная батарея",
        [battery_model[:34], batt_text, f"C факт: {float(results.get('battery_capacity_actual', 0.0)):.1f} Ач", "Клеммы: BAT+ / BAT-"],
    )
    block(
        680, 70, 210, 118,
        "G1",
        "Инвертор DC/AC",
        [inverter_model[:28], f"Вход: DC {state.system_voltage():.0f} В", "Выход: AC 230 В 50 Гц", dc_cable],
    )
    block(
        922, 70, 143, 150,
        "ZL1",
        "Нагрузки",
        [f"AC: {len(state.ac_loads)}", f"DC: {len(state.dc_loads)}", "230 В AC", "Шина DC", ac_cable.replace("Кабель AC", "AC")],
    )

    arrow(240, 128, 330, 128)
    text(252, 106, "DC PV", size=8.5)
    arrow(455, 220, 455, 270)
    text(466, 240, "Заряд", size=8.5)
    arrow(580, 128, 680, 128)
    text(596, 106, "Шина DC", size=8.5)
    arrow(890, 128, 917, 128)
    text(893, 106, "230 В", size=8.0)

    # Simplified main inscription (основная надпись) in GOST style.
    sx, sy, sw, sh = 20.0, 500.0, 700.0, 74.0
    rect(sx, sy, sx + sw, sy + sh)
    for dx in (70.0, 130.0, 250.0, 360.0, 470.0):
        line(sx + dx, sy, sx + dx, sy + sh)
    for dy in (24.0, 49.0):
        line(sx, sy + dy, sx + sw, sy + dy)
    text(sx + 8, sy + 6, "Изм.", size=8.0)
    text(sx + 78, sy + 6, "Лист", size=8.0)
    text(sx + 138, sy + 6, "№ докум.", size=8.0)
    text(sx + 258, sy + 6, "Подп.", size=8.0)
    text(sx + 368, sy + 6, "Дата", size=8.0)
    text(sx + 478, sy + 6, "PV-Calc Pro", size=8.0, bold=True)
    text(sx + 8, sy + 30, "Разраб.", size=8.0)
    text(sx + 8, sy + 55, "Пров.", size=8.0)
    text(sx + 138, sy + 30, "АФС-САПР-001", size=8.0)
    text(sx + 478, sy + 30, "Автономная фотоэлектрическая система", size=8.0)
    text(sx + 478, sy + 55, "Лист 1", size=8.0)

    output_path = Path(filename)
    if output_path.suffix.lower() != ".pdf":
        output_path = output_path.with_suffix(".pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.print_pdf(output_path)
    return output_path

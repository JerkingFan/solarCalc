"""Small ImGui helper widgets."""

from __future__ import annotations

from imgui_bundle import imgui


def tooltip(text: str) -> None:
    if imgui.is_item_hovered():
        imgui.set_tooltip(text)


def help_marker(text: str) -> None:
    imgui.same_line()
    imgui.text_colored((0.55, 0.75, 0.95, 1.0), "(?)")
    tooltip(text)


def clamp(value: float, minimum: float, maximum: float | None = None) -> float:
    value = max(float(minimum), float(value))
    if maximum is not None:
        value = min(float(maximum), value)
    return value

"""Native file dialogs used by the ImGui UI.

Implemented through tkinter to avoid adding another GUI dependency. The tkinter
root window is hidden; only the platform file dialog is shown.
"""

from __future__ import annotations

from typing import Any


def _ask(dialog_name: str, **kwargs: Any) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:  # noqa: BLE001
        return None

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:  # noqa: BLE001
        pass
    try:
        dialog = getattr(filedialog, dialog_name)
        path = dialog(parent=root, **kwargs)
        return str(path) if path else None
    finally:
        root.destroy()


def ask_open_json() -> str | None:
    return _ask(
        "askopenfilename",
        title="Открыть проект PV-Calc Pro",
        filetypes=(("PV-Calc project", "*.json"), ("All files", "*.*")),
    )


def ask_save_json(default_name: str = "pv_project.json") -> str | None:
    return _ask(
        "asksaveasfilename",
        title="Сохранить проект PV-Calc Pro",
        defaultextension=".json",
        initialfile=default_name,
        filetypes=(("PV-Calc project", "*.json"), ("All files", "*.*")),
    )


def ask_save_docx(default_name: str = "PV_Calc_Report.docx") -> str | None:
    return _ask(
        "asksaveasfilename",
        title="Сохранить отчет DOCX",
        defaultextension=".docx",
        initialfile=default_name,
        filetypes=(("Word document", "*.docx"), ("All files", "*.*")),
    )


def ask_save_xlsx(default_name: str = "PV_Calc_BOM.xlsx") -> str | None:
    return _ask(
        "asksaveasfilename",
        title="Экспорт BOM в Excel",
        defaultextension=".xlsx",
        initialfile=default_name,
        filetypes=(("Excel workbook", "*.xlsx"), ("All files", "*.*")),
    )


def ask_save_pdf(default_name: str = "PV_Calc_Scheme.pdf") -> str | None:
    return _ask(
        "asksaveasfilename",
        title="Сохранить структурную схему в PDF",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=(("PDF document", "*.pdf"), ("All files", "*.*")),
    )

"""Training missions / scenarios for PV-Calc Pro.

A mission gives the user a realistic brief: location, required loads, constraints
and a budget. The goal is to choose components and parameters so that the
resulting autonomous PV system passes all engineering criteria and stays within
the budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.climate import get_monthly_psh


@dataclass(frozen=True)
class Mission:
    """User-facing engineering task."""

    id: str
    title: str
    description: str
    budget_byn: float
    required_ac_loads: list[dict[str, Any]] = field(default_factory=list)
    required_dc_loads: list[dict[str, Any]] = field(default_factory=list)
    min_autonomy_days: float = 1.0
    city: str | None = None
    month: str | None = None
    relief_name: str | None = None
    fixed_system_voltage: float | None = None
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "budget_byn": self.budget_byn,
            "required_ac_loads": list(self.required_ac_loads),
            "required_dc_loads": list(self.required_dc_loads),
            "min_autonomy_days": self.min_autonomy_days,
            "city": self.city,
            "month": self.month,
            "relief_name": self.relief_name,
            "fixed_system_voltage": self.fixed_system_voltage,
            "hints": list(self.hints),
        }


MISSION_TEMPLATES: tuple[Mission, ...] = (
    Mission(
        id="dacha",
        title="Дача",
        description=(
            "Небольшая дача под Минском: нужно обеспечить свет, холодильник, "
            "телевизор и связь на выходные. Бюджет ограничен, поэтому важно "
            "не перебрать с мощностью панелей и ёмкостью АКБ."
        ),
        budget_byn=15_000.0,
        required_ac_loads=[
            {"name": "Освещение", "power": 80.0, "hours_week": 28.0, "surge_factor": 1.0},
            {"name": "Холодильник", "power": 120.0, "hours_week": 84.0, "surge_factor": 5.0},
            {"name": "Телевизор", "power": 60.0, "hours_week": 18.0, "surge_factor": 1.2},
        ],
        required_dc_loads=[
            {"name": "Роутер 12В", "power": 15.0, "hours_week": 168.0, "surge_factor": 1.0},
        ],
        min_autonomy_days=1.5,
        city="Минск",
        month="Декабрь",
        relief_name="Открытая равнина (1.00)",
        hints=[
            "Для дачи обычно достаточно системы 24 В.",
            "Холодильник — главный потребитель и источник пусковых токов.",
            "Если CAPEX превышает бюджет, снизьте дни автономии или выберите более дешёвую АКБ.",
        ],
    ),
    Mission(
        id="small_factory",
        title="Мелкое производство",
        description=(
            "Цех на окраине Гомеля: питание инструментов, компрессора, освещения "
            "и системы вентиляции. Нужна надёжная 48-вольтовая система и запас по "
            "пусковым токам."
        ),
        budget_byn=30_000.0,
        required_ac_loads=[
            {"name": "Компрессор", "power": 1500.0, "hours_week": 14.0, "surge_factor": 4.0},
            {"name": "Промышленное освещение", "power": 400.0, "hours_week": 50.0, "surge_factor": 1.0},
            {"name": "Вентиляция", "power": 250.0, "hours_week": 40.0, "surge_factor": 2.5},
            {"name": "Зарядка инструмента", "power": 300.0, "hours_week": 15.0, "surge_factor": 1.2},
        ],
        required_dc_loads=[
            {"name": "Сигнализация", "power": 20.0, "hours_week": 168.0, "surge_factor": 1.0},
        ],
        min_autonomy_days=1.0,
        city="Гомель",
        month="Декабрь",
        relief_name="Городская застройка (0.85)",
        fixed_system_voltage=48.0,
        hints=[
            "Компрессор задаёт мощный пусковой ток — инвертор должен держать surge.",
            "Для производства выбирайте 48 В, чтобы снизить токи и сечение кабелей.",
            "Если бюджет уперся — попробуйте сократить часы работы компрессора.",
        ],
    ),
    Mission(
        id="train",
        title="Автономный вагон / поезд",
        description=(
            "Мобильная система для служебного вагона: освещение, ноутбуки, "
            "холодильник-мини и зарядка гаджетов. Пространство и бюджет сильно "
            "ограничены, поэтому важен баланс мощности и габаритов."
        ),
        budget_byn=18_000.0,
        required_ac_loads=[
            {"name": "LED-освещение", "power": 60.0, "hours_week": 56.0, "surge_factor": 1.0},
            {"name": "Ноутбуки / зарядка", "power": 150.0, "hours_week": 42.0, "surge_factor": 1.2},
            {"name": "Холодильник-мини", "power": 80.0, "hours_week": 84.0, "surge_factor": 4.0},
        ],
        required_dc_loads=[
            {"name": "Роутер 12В", "power": 12.0, "hours_week": 168.0, "surge_factor": 1.0},
            {"name": "Система сигнализации", "power": 10.0, "hours_week": 168.0, "surge_factor": 1.0},
        ],
        min_autonomy_days=2.0,
        city="Брест",
        month="Декабрь",
        relief_name="Холмистая местность (0.92)",
        hints=[
            "В мобильном вагоне обычно используют 12 или 24 В.",
            "Мини-холодильник — самая капризная нагрузка: пусковая кратность до 4–6.",
            "Компактные панели 50–100 Вт легче уместить на крыше.",
        ],
    ),
    Mission(
        id="school",
        title="Школа",
        description=(
            "Сельская школа: классы, компьютерный кабинет, освещение коридоров, "
            "холодильник в столовой и насос водоснабжения. Система должна быть "
            "надёжной и покрывать рабочие дни даже в пасмурный период."
        ),
        budget_byn=50_000.0,
        required_ac_loads=[
            {"name": "Освещение классов", "power": 500.0, "hours_week": 60.0, "surge_factor": 1.0},
            {"name": "Компьютерный кабинет", "power": 600.0, "hours_week": 30.0, "surge_factor": 1.2},
            {"name": "Холодильник столовой", "power": 200.0, "hours_week": 84.0, "surge_factor": 5.0},
            {"name": "Водяной насос", "power": 750.0, "hours_week": 14.0, "surge_factor": 4.0},
        ],
        required_dc_loads=[
            {"name": "Коридорное аварийное освещение", "power": 40.0, "hours_week": 168.0, "surge_factor": 1.0},
            {"name": "Роутер / локальная сеть", "power": 25.0, "hours_week": 168.0, "surge_factor": 1.0},
        ],
        min_autonomy_days=2.0,
        city="Витебск",
        month="Декабрь",
        relief_name="Открытая равнина (1.00)",
        fixed_system_voltage=48.0,
        hints=[
            "Школа требует 48-вольтовую систему из-за насоса и компьютеров.",
            "Насос и холодильник — главные пусковые нагрузки.",
            "Для надёжности выбирайте LiFePO4 АКБ с глубоким разрядом.",
        ],
    ),
)


def mission_names() -> list[str]:
    return [m.title for m in MISSION_TEMPLATES]


def get_mission_by_title(title: str) -> Mission:
    for m in MISSION_TEMPLATES:
        if m.title == title:
            return m
    available = ", ".join(mission_names())
    raise KeyError(f"Неизвестное задание '{title}'. Доступны: {available}")


def get_mission_by_id(mission_id: str) -> Mission:
    for m in MISSION_TEMPLATES:
        if m.id == mission_id:
            return m
    raise KeyError(f"Неизвестный id задания '{mission_id}'.")


def _loads_match(required: list[dict[str, Any]], actual: list[Any]) -> bool:
    """Check that every required load is still present by name in actual rows.

    ``actual`` may contain either dicts (payload format) or lists (UI rows).
    """
    actual_names: set[str] = set()
    for row in actual:
        if isinstance(row, dict):
            name = str(row.get("name", "")).strip().lower()
        elif isinstance(row, (list, tuple)) and row:
            name = str(row[0]).strip().lower()
        else:
            continue
        if name:
            actual_names.add(name)
    for req in required:
        name = str(req.get("name", "")).strip().lower()
        if name and name not in actual_names:
            return False
    return True


def evaluate_mission(
    mission: Mission,
    payload: dict[str, Any],
    results: dict[str, Any] | None,
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate how well the current configuration satisfies the mission.

    Returns a dict with human-readable criteria, overall pass flag and score.
    """
    criteria: list[dict[str, Any]] = []
    score = 100
    passed = True

    # 1. Required loads present
    ac_ok = _loads_match(mission.required_ac_loads, payload.get("ac_loads", []))
    dc_ok = _loads_match(mission.required_dc_loads, payload.get("dc_loads", []))
    loads_ok = ac_ok and dc_ok
    criteria.append(
        {
            "name": "Обязательные нагрузки",
            "ok": loads_ok,
            "value": "Все на месте" if loads_ok else "Удалены обязательные приборы",
            "message": "Список нагрузок должен содержать все заданные приборы.",
        }
    )
    if not loads_ok:
        score -= 20
        passed = False

    # 2. Budget
    economics = results.get("economics", {}) if results else {}
    capex = float(economics.get("capex_byn", 0.0))
    budget_ok = capex <= mission.budget_byn
    criteria.append(
        {
            "name": "Бюджет",
            "ok": budget_ok,
            "value": f"{capex:,.0f} / {mission.budget_byn:,.0f} BYN",
            "message": "Стоимость оборудования с монтажом не должна превышать бюджет.",
        }
    )
    if not budget_ok:
        score -= 25
        passed = False

    # 3. Autonomy
    autonomy_days = float(payload.get("days_autonomy", 0.0))
    autonomy_ok = autonomy_days >= mission.min_autonomy_days
    criteria.append(
        {
            "name": "Автономность",
            "ok": autonomy_ok,
            "value": f"{autonomy_days:.1f} дн (нужно ≥ {mission.min_autonomy_days:.1f})",
            "message": "Дней автономности должно хватать на непогоду.",
        }
    )
    if not autonomy_ok:
        score -= 15
        passed = False

    # 4. Energy balance in worst month
    energy_ok = False
    if results:
        daily_energy_wh = float(results.get("daily_energy_wh", 0.0))
        pv_actual_w = float(results.get("pv_actual_w", 0.0))
        psh = float(results.get("psh", payload.get("psh", 0.0)))
        effective_pv_efficiency = float(results.get("effective_pv_efficiency", payload.get("pv_system_efficiency", 0.78)))
        if psh > 0 and effective_pv_efficiency > 0:
            daily_pv_wh = pv_actual_w * psh * effective_pv_efficiency
            energy_ok = daily_pv_wh >= daily_energy_wh
            energy_ratio = daily_pv_wh / daily_energy_wh if daily_energy_wh > 0 else 0.0
        else:
            energy_ratio = 0.0
    else:
        energy_ratio = 0.0
    criteria.append(
        {
            "name": "Энергобаланс в худшем месяце",
            "ok": energy_ok,
            "value": f"PV/нагрузка = {energy_ratio:.2f} (нужно ≥ 1.0)" if results else "Нет расчёта",
            "message": "Выработка PV в расчётном месяце должна покрывать суточное потребление.",
        }
    )
    if not energy_ok:
        score -= 20
        passed = False

    # 5. No critical diagnostics
    critical_count = sum(1 for d in diagnostics if d.get("level") == "critical")
    critical_ok = critical_count == 0
    criteria.append(
        {
            "name": "Инженерные ошибки",
            "ok": critical_ok,
            "value": f"Критических сбоев: {critical_count}",
            "message": "Не должно быть критических инженерных нарушений (ток, напряжение, мощность).",
        }
    )
    if not critical_ok:
        score -= 20
        passed = False

    # 6. Location / climate criteria are intentionally not scored:
    # the mission brief sets the starting climate, but the user may explore
    # other cities/months without being penalized for it.

    # 7. System voltage (if fixed)
    if mission.fixed_system_voltage:
        voltage_ok = float(payload.get("system_voltage", 0.0)) == float(mission.fixed_system_voltage)
        criteria.append(
            {
                "name": "Напряжение системы",
                "ok": voltage_ok,
                "value": f"{payload.get('system_voltage', '—')} В",
                "message": f"Задание требует систему {mission.fixed_system_voltage:g} В.",
            }
        )
        if not voltage_ok:
            score -= 10
            passed = False

    score = max(0, min(100, score))

    # Hints based on current state
    hints: list[str] = []
    if not budget_ok:
        hints.append("Бюджет превышен: попробуйте снизить дни автономии, выбрать более дешёвые панели/АКБ или сократить необязательные нагрузки.")
    if not autonomy_ok:
        hints.append("Недостаточная автономность: увеличьте дни без солнца или добавьте ёмкости АКБ.")
    if not energy_ok:
        hints.append("Энергодефицит: увеличьте мощность PV-поля (больше или более мощные панели) или снизьте потребление.")
    if critical_count:
        hints.append("Есть критические ошибки: проверьте совместимость инвертора/контроллера, сечения кабелей и пусковые токи.")
    if not hints and budget_ok and autonomy_ok and energy_ok and critical_ok:
        hints.append("Отлично! Все критерии выполнены. Можно сохранить проект и сформировать отчёт.")

    return {
        "mission_id": mission.id,
        "title": mission.title,
        "passed": passed,
        "score": score,
        "budget_byn": mission.budget_byn,
        "capex_byn": capex,
        "criteria": criteria,
        "hints": hints,
        "diagnostics": diagnostics,
    }

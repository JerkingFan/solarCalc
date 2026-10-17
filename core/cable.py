"""Cable sizing according to voltage-drop and ampacity constraints.

The method follows the usual low-voltage DC design practice used in ПУЭ-based
calculations: select the standard copper conductor cross-section that satisfies
both the allowed voltage drop and the continuous current-carrying capacity.
"""

from dataclasses import dataclass, field

RHO_COPPER_OHM_MM2_PER_M = 0.0175
DEFAULT_DC_DROP_RATIO = 0.02

STANDARD_SECTIONS_MM2: tuple[float, ...] = (
    0.5,
    0.75,
    1.0,
    1.5,
    2.5,
    4.0,
    6.0,
    10.0,
    16.0,
    25.0,
    35.0,
    50.0,
    70.0,
    95.0,
    120.0,
    150.0,
    185.0,
    240.0,
)

# Conservative continuous ampacity for copper conductors in air/conduit, A.
AMPACITY_A: dict[float, float] = {
    0.5: 11.0,
    0.75: 15.0,
    1.0: 17.0,
    1.5: 23.0,
    2.5: 30.0,
    4.0: 41.0,
    6.0: 50.0,
    10.0: 80.0,
    16.0: 100.0,
    25.0: 140.0,
    35.0: 170.0,
    50.0: 215.0,
    70.0: 265.0,
    95.0: 320.0,
    120.0: 375.0,
    150.0: 430.0,
    185.0: 495.0,
    240.0: 585.0,
}


@dataclass(frozen=True)
class CableResult:
    current_a: float
    length_m: float
    system_voltage_v: float
    max_drop_v: float
    required_section_mm2: float
    section_mm2: float
    actual_drop_v: float
    actual_drop_percent: float
    ampacity_a: float
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _voltage_drop(section_mm2: float, current_a: float, length_m: float) -> float:
    if section_mm2 <= 0:
        return float("inf")
    return 2.0 * RHO_COPPER_OHM_MM2_PER_M * length_m * current_a / section_mm2


def _required_ampacity_section(current_a: float) -> tuple[float, bool]:
    """Return (minimum standard section by ampacity, is_feasible)."""
    required_ampacity = current_a * 1.25
    section_by_ampacity = next(
        (section for section in STANDARD_SECTIONS_MM2 if AMPACITY_A[section] >= required_ampacity),
        None,
    )
    if section_by_ampacity is None:
        return STANDARD_SECTIONS_MM2[-1], False
    return section_by_ampacity, True


def required_cable_section(
    current_a: float,
    length_m: float,
    system_voltage_v: float,
    drop_ratio: float = DEFAULT_DC_DROP_RATIO,
) -> float:
    """Return the theoretical minimum section satisfying drop and ampacity."""
    current_a = max(0.0, float(current_a))
    length_m = max(0.0, float(length_m))
    system_voltage_v = float(system_voltage_v)
    if system_voltage_v <= 0 or current_a == 0 or length_m == 0:
        return 1.5
    max_drop_v = system_voltage_v * drop_ratio
    section_by_drop = (
        2.0 * RHO_COPPER_OHM_MM2_PER_M * length_m * current_a / max_drop_v
    )
    section_by_ampacity, _ = _required_ampacity_section(current_a)
    return max(section_by_drop, section_by_ampacity)


def evaluate_cable_section(
    section_mm2: float,
    current_a: float,
    length_m: float,
    system_voltage_v: float,
    drop_ratio: float = DEFAULT_DC_DROP_RATIO,
) -> CableResult:
    """Evaluate a user-selected cable section and return warnings if it is insufficient."""
    warnings: list[str] = []
    current_a = max(0.0, float(current_a))
    length_m = max(0.0, float(length_m))
    system_voltage_v = float(system_voltage_v)
    section = float(section_mm2)

    if system_voltage_v <= 0:
        raise ValueError("Напряжение системы должно быть больше нуля.")
    if drop_ratio <= 0 or drop_ratio >= 0.2:
        raise ValueError("Относительное падение напряжения должно быть в диапазоне (0; 0.2).")
    if section <= 0:
        raise ValueError("Сечение кабеля должно быть больше нуля.")

    max_drop_v = system_voltage_v * drop_ratio
    required_section = required_cable_section(current_a, length_m, system_voltage_v, drop_ratio)

    actual_drop = _voltage_drop(section, current_a, length_m)
    actual_drop_percent = (actual_drop / system_voltage_v) * 100.0 if system_voltage_v else 0.0

    if section < required_section:
        warnings.append(
            f"Выбранное сечение {section:g} мм² меньше требуемого {required_section:g} мм² "
            "по падению напряжения и/или длительно допустимому току."
        )
    if current_a > 0 and section in AMPACITY_A and current_a * 1.25 > AMPACITY_A[section]:
        warnings.append(
            f"Ток {current_a:.1f} А превышает длительно допустимый для сечения {section:g} мм² "
            "с учетом запаса 1.25 (ПУЭ)."
        )
    if actual_drop > max_drop_v:
        warnings.append(
            f"Падение напряжения {actual_drop_percent:.2f}% превышает допустимое {drop_ratio*100:.1f}%."
        )

    return CableResult(
        current_a=current_a,
        length_m=length_m,
        system_voltage_v=system_voltage_v,
        max_drop_v=max_drop_v,
        required_section_mm2=required_section,
        section_mm2=section,
        actual_drop_v=actual_drop,
        actual_drop_percent=actual_drop_percent,
        ampacity_a=AMPACITY_A.get(section, 0.0),
        warnings=tuple(warnings),
    )


def calculate_cable_section(
    current_a: float,
    length_m: float,
    system_voltage_v: float,
    drop_ratio: float = DEFAULT_DC_DROP_RATIO,
    forced_section_mm2: float | None = None,
) -> CableResult:
    """Select or evaluate a copper cable section.

    Args:
        current_a: Continuous DC current, A.
        length_m: One-way cable route length, m. The loop length is 2*L.
        system_voltage_v: Nominal system voltage, V.
        drop_ratio: Allowed relative voltage drop (0.02 = 2%).
        forced_section_mm2: If provided, evaluate this section instead of auto-selecting.

    Returns:
        CableResult with the selected section and engineering warnings.
    """
    if forced_section_mm2 is not None:
        return evaluate_cable_section(forced_section_mm2, current_a, length_m, system_voltage_v, drop_ratio)

    warnings: list[str] = []
    current_a = max(0.0, float(current_a))
    length_m = max(0.0, float(length_m))
    system_voltage_v = float(system_voltage_v)

    if system_voltage_v <= 0:
        raise ValueError("Напряжение системы должно быть больше нуля.")
    if drop_ratio <= 0 or drop_ratio >= 0.2:
        raise ValueError("Относительное падение напряжения должно быть в диапазоне (0; 0.2).")

    if current_a == 0 or length_m == 0:
        section = 1.5
        return CableResult(
            current_a=current_a,
            length_m=length_m,
            system_voltage_v=system_voltage_v,
            max_drop_v=system_voltage_v * drop_ratio,
            required_section_mm2=section,
            section_mm2=section,
            actual_drop_v=0.0,
            actual_drop_percent=0.0,
            ampacity_a=AMPACITY_A[section],
            warnings=("Ток или длина трассы равны нулю; принято минимальное сечение 1.5 мм².",),
        )

    max_drop_v = system_voltage_v * drop_ratio
    section_by_drop = (
        2.0 * RHO_COPPER_OHM_MM2_PER_M * length_m * current_a / max_drop_v
    )

    section_by_ampacity, ampacity_feasible = _required_ampacity_section(current_a)
    if not ampacity_feasible:
        warnings.append(
            "Расчетный ток превышает длительно допустимый ток кабеля 240 мм²; "
            "требуется повышение системного напряжения или разбиение на параллельные линии."
        )

    required_section = max(section_by_drop, section_by_ampacity)
    selected_section = next(
        (section for section in STANDARD_SECTIONS_MM2 if section >= required_section),
        None,
    )
    if selected_section is None:
        selected_section = STANDARD_SECTIONS_MM2[-1]
        warnings.append(
            "Требуемое сечение превышает 240 мм²; рекомендуется повысить системное напряжение "
            "или разбить PV-поле на несколько контроллеров."
        )

    actual_drop = _voltage_drop(selected_section, current_a, length_m)
    actual_drop_percent = (actual_drop / system_voltage_v) * 100.0
    if actual_drop > max_drop_v:
        warnings.append(
            "Падение напряжения превышает допустимое значение; проверьте длину трассы, "
            "ток и системное напряжение."
        )

    return CableResult(
        current_a=current_a,
        length_m=length_m,
        system_voltage_v=system_voltage_v,
        max_drop_v=max_drop_v,
        required_section_mm2=required_section,
        section_mm2=selected_section,
        actual_drop_v=actual_drop,
        actual_drop_percent=actual_drop_percent,
        ampacity_a=AMPACITY_A[selected_section],
        warnings=tuple(warnings),
    )

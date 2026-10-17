"""Overcurrent protection sizing helpers for PV-Calc Pro."""

from __future__ import annotations

STANDARD_BREAKER_RATINGS_A: tuple[int, ...] = (
    6,
    10,
    16,
    20,
    25,
    32,
    40,
    50,
    63,
    80,
    100,
    125,
    160,
    200,
    250,
    315,
)


def next_breaker_rating(required_current_a: float) -> int:
    required_current_a = max(0.0, float(required_current_a))
    for rating in STANDARD_BREAKER_RATINGS_A:
        if rating >= required_current_a:
            return rating
    return STANDARD_BREAKER_RATINGS_A[-1]


def recommended_protection(
    pv_array_short_circuit_current_a: float,
    controller_charge_current_a: float,
    battery_main_current_a: float,
    ac_output_current_a: float,
) -> dict[str, object]:
    """Return recommended breaker/fuse/RCD ratings with design margins."""
    pv_array_breaker = next_breaker_rating(pv_array_short_circuit_current_a * 1.25)
    controller_battery_breaker = next_breaker_rating(controller_charge_current_a * 1.25)
    battery_main_breaker = next_breaker_rating(battery_main_current_a * 1.25)
    ac_output_breaker = next_breaker_rating(ac_output_current_a * 1.25)

    warnings: list[str] = []
    if battery_main_breaker >= 315:
        warnings.append(
            "Главный автомат АКБ получился очень большим; проверьте системное напряжение, "
            "ток инвертора и сечение кабелей."
        )
    if pv_array_breaker >= 160:
        warnings.append(
            "Автомат PV-поля получился большим; проверьте число параллельных стрингов "
            "и ток короткого замыкания модулей."
        )

    return {
        "pv_array_breaker_a": pv_array_breaker,
        "controller_battery_breaker_a": controller_battery_breaker,
        "battery_main_breaker_a": battery_main_breaker,
        "ac_output_breaker_a": ac_output_breaker,
        "ac_rcd": "УЗО/диффавтомат 30 мА, тип A",
        "warnings": warnings,
    }

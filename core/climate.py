"""Built-in climate and shading data for PV-Calc Pro.

The table is a deterministic offline climate model for Belarus. It is used for
engineering estimates when external NASA POWER/PVGIS/Open-Meteo APIs are not
connected. Values are monthly average daily PSH (peak sun hours).
"""

from __future__ import annotations

from dataclasses import dataclass

MONTHS: tuple[str, ...] = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)


@dataclass(frozen=True)
class CityClimate:
    name: str
    latitude: float
    longitude: float
    monthly_psh: dict[str, float]
    min_design_temperature_c: float


CITY_CLIMATE: dict[str, CityClimate] = {
    "Минск": CityClimate(
        name="Минск",
        latitude=53.90,
        longitude=27.56,
        monthly_psh={
            "Январь": 1.2,
            "Февраль": 2.1,
            "Март": 3.5,
            "Апрель": 4.8,
            "Май": 5.8,
            "Июнь": 6.2,
            "Июль": 5.9,
            "Август": 4.9,
            "Сентябрь": 3.2,
            "Октябрь": 1.9,
            "Ноябрь": 1.1,
            "Декабрь": 0.9,
        },
        min_design_temperature_c=-25.0,
    ),
    "Брест": CityClimate(
        name="Брест",
        latitude=52.09,
        longitude=23.70,
        monthly_psh={
            "Январь": 1.3,
            "Февраль": 2.2,
            "Март": 3.6,
            "Апрель": 4.9,
            "Май": 5.9,
            "Июнь": 6.3,
            "Июль": 6.0,
            "Август": 5.0,
            "Сентябрь": 3.3,
            "Октябрь": 2.0,
            "Ноябрь": 1.2,
            "Декабрь": 1.0,
        },
        min_design_temperature_c=-23.0,
    ),
    "Гомель": CityClimate(
        name="Гомель",
        latitude=52.43,
        longitude=30.98,
        monthly_psh={
            "Январь": 1.3,
            "Февраль": 2.2,
            "Март": 3.7,
            "Апрель": 5.0,
            "Май": 6.0,
            "Июнь": 6.4,
            "Июль": 6.1,
            "Август": 5.1,
            "Сентябрь": 3.4,
            "Октябрь": 2.1,
            "Ноябрь": 1.2,
            "Декабрь": 1.0,
        },
        min_design_temperature_c=-24.0,
    ),
    "Витебск": CityClimate(
        name="Витебск",
        latitude=55.19,
        longitude=30.20,
        monthly_psh={
            "Январь": 1.1,
            "Февраль": 2.0,
            "Март": 3.4,
            "Апрель": 4.7,
            "Май": 5.7,
            "Июнь": 6.1,
            "Июль": 5.8,
            "Август": 4.8,
            "Сентябрь": 3.1,
            "Октябрь": 1.8,
            "Ноябрь": 1.0,
            "Декабрь": 0.8,
        },
        min_design_temperature_c=-26.0,
    ),
    "Гродно": CityClimate(
        name="Гродно",
        latitude=53.68,
        longitude=23.83,
        monthly_psh={
            "Январь": 1.2,
            "Февраль": 2.1,
            "Март": 3.5,
            "Апрель": 4.8,
            "Май": 5.8,
            "Июнь": 6.2,
            "Июль": 5.9,
            "Август": 4.9,
            "Сентябрь": 3.2,
            "Октябрь": 1.9,
            "Ноябрь": 1.1,
            "Декабрь": 0.9,
        },
        min_design_temperature_c=-24.0,
    ),
    "Могилев": CityClimate(
        name="Могилев",
        latitude=53.90,
        longitude=30.33,
        monthly_psh={
            "Январь": 1.2,
            "Февраль": 2.1,
            "Март": 3.6,
            "Апрель": 4.9,
            "Май": 5.9,
            "Июнь": 6.3,
            "Июль": 6.0,
            "Август": 5.0,
            "Сентябрь": 3.3,
            "Октябрь": 2.0,
            "Ноябрь": 1.1,
            "Декабрь": 0.9,
        },
        min_design_temperature_c=-25.0,
    ),
}

RELIEF_COEFFICIENTS: dict[str, float] = {
    "Открытая равнина (1.00)": 1.00,
    "Холмистая местность (0.92)": 0.92,
    "Городская застройка (0.85)": 0.85,
    "Лес / частичное затенение (0.75)": 0.75,
}


def city_names() -> list[str]:
    return list(CITY_CLIMATE.keys())


def relief_names() -> list[str]:
    return list(RELIEF_COEFFICIENTS.keys())


def get_city_climate(city: str) -> CityClimate:
    try:
        return CITY_CLIMATE[city]
    except KeyError as exc:
        available = ", ".join(city_names())
        raise KeyError(f"Неизвестный город '{city}'. Доступны: {available}") from exc


def get_monthly_psh(city: str, month: str) -> float:
    climate = get_city_climate(city)
    try:
        return float(climate.monthly_psh[month])
    except KeyError as exc:
        available = ", ".join(MONTHS)
        raise KeyError(f"Неизвестный месяц '{month}'. Доступны: {available}") from exc


def get_min_design_temperature(city: str) -> float:
    return float(get_city_climate(city).min_design_temperature_c)


def get_relief_coefficient(relief_name: str) -> float:
    try:
        return float(RELIEF_COEFFICIENTS[relief_name])
    except KeyError as exc:
        available = ", ".join(relief_names())
        raise KeyError(f"Неизвестный тип рельефа '{relief_name}'. Доступны: {available}") from exc

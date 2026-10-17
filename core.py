# core.py (обновленный блок расчетов и баз данных)

EQUIPMENT_DATABASE = {
    "solar_panels": {
        "LONGi Hi-MO 6 (450Вт)": {"power": 450, "voltage": 31.5, "current": 14.3, "type": "HPBC N-type"},
        "Jinko Tiger Neo 570Вт": {"power": 570, "voltage": 42.1, "current": 13.5, "type": "TOPCon"},
        "Trina Vertex S+ 450Вт": {"power": 450, "voltage": 38.2, "current": 11.8, "type": "N-type Dual Glass"},
        "МС-50-4 (Базовая)": {"power": 50, "voltage": 17.5, "current": 2.85, "type": "Монокристалл"}
    },
    "batteries": {
        "Pylontech US5000 (4.8 кВт·ч / 48В)": {"capacity": 100, "voltage": 48, "type": "LiFePO4"},
        "BYD Battery-Box Premium (5.1 кВт·ч)": {"capacity": 100, "voltage": 51.2, "type": "LiFePO4"},
        "Гелевая Delta GOR 120Ач (24В)": {"capacity": 120, "voltage": 24, "type": "GEL"},
        "Leoch LDC 200Ач (12В)": {"capacity": 200, "voltage": 12, "type": "GEL Deep Cycle"}
    }
}

CLIMATE_DATA = {
    "Минск": {"Январь": 1.2, "Февраль": 2.1, "Март": 3.5, "Апрель": 4.8, "Май": 5.8, "Июнь": 6.2, "Июль": 5.9, "Август": 4.9, "Сентябрь": 3.2, "Октябрь": 1.9, "Ноябрь": 1.1, "Декабрь": 0.9},
}

def calculate_cable_section(current, length_meters, max_voltage_drop_v=0.25):
    rho = 0.0175  # Удельное сопротивление меди
    standard_sections = [0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0, 16.0]
    if current <= 0:
        return 1.5, 0.0
    calculated_s = (2 * rho * length_meters * current) / max_voltage_drop_v
    selected_s = standard_sections[-1]
    for s in standard_sections:
        if s >= calculated_s:
            selected_s = s
            break
    actual_drop = (2 * rho * length_meters * current) / selected_s
    return selected_s, actual_drop

class SolarSystemCalculator:
    def __init__(self, data):
        self.data = data
        self.results = {}

    def calculate(self):
        total_w_ac = sum(load['power'] * load['hours_week'] for load in self.data.get('ac_loads', []))
        w1_energy = total_w_ac * 1.2
        u_i = self.data['system_voltage']

        total_w_dc = sum(load['power'] * load['hours_week'] for load in self.data.get('dc_loads', []))
        e_sigma = ((w1_energy + total_w_dc) / u_i) / 7.0

        n = self.data['days_autonomy']
        battery_capacity_total = ((e_sigma * n) / 0.2) * 1.2
        
        base_insolation = CLIMATE_DATA.get("Минск", {}).get("Декабрь", 0.9)
        t_n = base_insolation * 0.1 / 31.0
        p_panel_req = (e_sigma * 1.2) / t_n

        # Выбор конкретной модели панели из выпадающего списка
        panel_model_name = self.data.get('panel_model', 'МС-50-4 (Базовая)')
        panel_info = EQUIPMENT_DATABASE['solar_panels'].get(panel_model_name, EQUIPMENT_DATABASE['solar_panels']['МС-50-4 (Базовая)'])
        
        pn = panel_info['power']
        nm_modules = round((p_panel_req / pn) + 0.4)
        if nm_modules < 1: nm_modules = 1

        total_panel_current = nm_modules * panel_info['current']

        # Подбор АКБ под расчетную емкость
        batt_model_name = self.data.get('battery_model', 'Гелевая Delta GOR 120Ач (24В)')
        batt_info = EQUIPMENT_DATABASE['batteries'].get(batt_model_name, EQUIPMENT_DATABASE['batteries']['Гелевая Delta GOR 120Ач (24В)'])
        
        # Количество АКБ для покрытия требуемой емкости
        batt_count = max(1, round(battery_capacity_total / batt_info['capacity']))

        self.results = {
            "total_w_ac": total_w_ac,
            "w1_energy": w1_energy,
            "total_w_dc": total_w_dc,
            "e_sigma": e_sigma,
            "battery_capacity_total": battery_capacity_total,
            "p_panel_req": p_panel_req,
            "nm_modules": nm_modules,
            "panel_model": panel_model_name,
            "panel_power_unit": pn,
            "battery_model": batt_model_name,
            "battery_count": batt_count,
            "total_panel_current": total_panel_current,
        }
        return self.results
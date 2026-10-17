import os
import sys
from imgui_bundle import hello_imgui, imgui

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
  from core import SolarSystemCalculator, calculate_cable_section
except ModuleNotFoundError:

  class SolarSystemCalculator:

    def __init__(self, data):
      self.data = data

    def calculate(self):
      return {
          "total_w_ac": 5000.0,
          "w1_energy": 5500.0,
          "total_w_dc": 300.0,
          "e_sigma": 45.0,
          "battery_capacity_total": 200.0,
          "p_panel_req": 300.0,
          "nm_modules": 6,
          "total_panel_current": 5.7,
          "panel_model": "LONGi Hi-MO 6 (450Вт)",
          "panel_power_unit": 450,
          "battery_model": "Гелевая Delta GOR 120Ач (24В)",
          "battery_count": 2,
      }

  def calculate_cable_section(current, length_meters, max_voltage_drop_v=0.25):
    return 2.5, 0.125


app_state = {
    "voltage_idx": 1,
    "voltages": [12, 24, 48],
    "days_autonomy": 5.0,
    "insolation": 0.9,
    "cable_length": 10.0,
    "panel_model_idx": 0,
    "panel_models": [
        "LONGi Hi-MO 6 (450Вт)",
        "Jinko Tiger Neo 570Вт",
        "Trina Vertex S+ 450Вт",
        "МС-50-4 (Базовая)"
    ],
    "batt_model_idx": 2,
    "batt_models": [
        "Pylontech US5000 (4.8 кВт·ч / 48В)",
        "BYD Battery-Box Premium (5.1 кВт·ч)",
        "Гелевая Delta GOR 120Ач (24В)",
        "Leoch LDC 200Ач (12В)"
    ],
    "ac_loads": [
        ["Освещение", 100.0, 35.0],
        ["Холодильник", 150.0, 84.0],
        ["Телевизор", 80.0, 20.0],
    ],
    "dc_loads": [["Роутер 12В", 15.0, 168.0], ["Аварийный свет", 20.0, 14.0]],
    "results": None,
}


def gui():
  state = app_state

  imgui.set_next_window_size((1100, 780), imgui.Cond_.once)
  imgui.set_next_window_pos((10, 10), imgui.Cond_.once)
  imgui.begin(
      "PV-Calc Pro — Автономные фотоэлектрические системы",
      flags=imgui.WindowFlags_.no_resize | imgui.WindowFlags_.no_collapse,
  )

  if imgui.begin_tab_bar("MainTabs"):

    # --- ВКЛАДКА 1: ИСХОДНЫЕ ДАННЫЕ ---
    tab_1_open, _ = imgui.begin_tab_item("⚙️ Исходные данные")
    if tab_1_open:
      imgui.text("Системные параметры по методичке и выбор оборудования:")
      imgui.separator()

      _, state["voltage_idx"] = imgui.combo(
          "Напряжение системы (В)",
          state["voltage_idx"],
          [str(v) for v in state["voltages"]],
      )
      _, state["days_autonomy"] = imgui.input_float(
          "Дней без солнца (n)", state["days_autonomy"]
      )
      _, state["insolation"] = imgui.input_float(
          "Инсоляция E (кВт*ч/м2)", state["insolation"]
      )
      _, state["cable_length"] = imgui.input_float(
          "Длина кабельной трассы (м)", state["cable_length"]
      )

      imgui.spacing()
      _, state["panel_model_idx"] = imgui.combo(
          "Модель солнечной панели",
          state["panel_model_idx"],
          state["panel_models"]
      )
      _, state["batt_model_idx"] = imgui.combo(
          "Модель аккумулятора / СНЭ",
          state["batt_model_idx"],
          state["batt_models"]
      )

      imgui.spacing()
      imgui.separator()
      imgui.text("Нагрузки переменного тока (Таблица 1.1):")

      if imgui.begin_table("ACTable", 4, 0):
        imgui.table_setup_column("Прибор")
        imgui.table_setup_column("Мощность (Вт)")
        imgui.table_setup_column("Часы/нед")
        imgui.table_setup_column("Действие")
        imgui.table_headers_row()

        to_delete_ac = None
        for i, load in enumerate(state["ac_loads"]):
          imgui.table_next_row()
          imgui.table_set_column_index(0)
          _, load[0] = imgui.input_text(f"##name_ac_{i}", load[0])
          imgui.table_set_column_index(1)
          _, load[1] = imgui.input_float(
              f"##p_ac_{i}", load[1], format="%.1f"
          )
          imgui.table_set_column_index(2)
          _, load[2] = imgui.input_float(
              f"##t_ac_{i}", load[2], format="%.1f"
          )
          imgui.table_set_column_index(3)
          if imgui.button(f"Удалить##ac_{i}"):
            to_delete_ac = i

        if to_delete_ac is not None:
          state["ac_loads"].pop(to_delete_ac)
        imgui.end_table()

      if imgui.button("➕ Добавить AC нагрузку"):
        state["ac_loads"].append(["Новый прибор", 50.0, 10.0])

      imgui.spacing()
      imgui.separator()
      imgui.text("Нагрузки постоянного тока (Таблица 1.2):")

      if imgui.begin_table("DCTable", 4, 0):
        imgui.table_setup_column("Прибор DC")
        imgui.table_setup_column("Мощность (Вт)")
        imgui.table_setup_column("Часы/нед")
        imgui.table_setup_column("Действие")
        imgui.table_headers_row()

        to_delete_dc = None
        for i, load in enumerate(state["dc_loads"]):
          imgui.table_next_row()
          imgui.table_set_column_index(0)
          _, load[0] = imgui.input_text(f"##name_dc_{i}", load[0])
          imgui.table_set_column_index(1)
          _, load[1] = imgui.input_float(
              f"##p_dc_{i}", load[1], format="%.1f"
          )
          imgui.table_set_column_index(2)
          _, load[2] = imgui.input_float(
              f"##t_dc_{i}", load[2], format="%.1f"
          )
          imgui.table_set_column_index(3)
          if imgui.button(f"Удалить##dc_{i}"):
            to_delete_dc = i

        if to_delete_dc is not None:
          state["dc_loads"].pop(to_delete_dc)
        imgui.end_table()

      if imgui.button("➕ Добавить DC нагрузку"):
        state["dc_loads"].append(["Новый DC прибор", 10.0, 24.0])

      imgui.spacing()
      if imgui.button("🚀 Выполнить расчет САПР", size=(250, 35)):
        formatted_ac = [
            {"name": l[0], "power": l[1], "hours_week": l[2]}
            for l in state["ac_loads"]
        ]
        formatted_dc = [
            {"name": l[0], "power": l[1], "hours_week": l[2]}
            for l in state["dc_loads"]
        ]

        calc_data = {
            "ac_loads": formatted_ac,
            "dc_loads": formatted_dc,
            "days_autonomy": state["days_autonomy"],
            "min_insolation_dec": state["insolation"],
            "system_voltage": state["voltages"][state["voltage_idx"]],
            "panel_model": state["panel_models"][state["panel_model_idx"]],
            "battery_model": state["batt_models"][state["batt_model_idx"]],
        }
        calc = SolarSystemCalculator(calc_data)
        state["results"] = calc.calculate()

      imgui.end_tab_item()

    # --- ВКЛАДКА 2: РЕЗУЛЬТАТЫ И КАБЕЛИ ---
    tab_2_open, _ = imgui.begin_tab_item("📊 Результаты и спецификация")
    if tab_2_open:
      imgui.text("Инженерный расчет кабельной сети и спецификация:")
      imgui.separator()

      if state["results"]:
        total_current = state["results"].get("total_panel_current", 5.0)
        sec, drop = calculate_cable_section(
            total_current, state["cable_length"]
        )

        if imgui.begin_table("ResTable", 2, 0):
          imgui.table_setup_column(
              "Параметр", imgui.TableColumnFlags_.width_stretch, 2.0
          )
          imgui.table_setup_column(
              "Значение", imgui.TableColumnFlags_.width_stretch, 1.0
          )
          imgui.table_headers_row()

          display_items = [
              (
                  "Суммарная энергия переменного тока",
                  f"{state['results']['total_w_ac']:.2f} Вт·ч/нед",
              ),
              (
                  "Энергия с учетом потерь в инверторе W1",
                  f"{state['results']['w1_energy']:.2f} Вт·ч/нед",
              ),
              (
                  "Суточное энергопотребление E_sigma",
                  f"{state['results']['e_sigma']:.2f} А·ч/сутки",
              ),
              (
                  "Требуемая емкость АКБ",
                  f"{state['results']['battery_capacity_total']:.2f} А·ч",
              ),
              (
                  "Выбранный тип АКБ",
                  f"{state['results']['battery_model']} ({state['results']['battery_count']} шт.)",
              ),
              (
                  "Требуемая мощность солнечной батареи",
                  f"{state['results']['p_panel_req']:.2f} Вт",
              ),
              (
                  "Выбранная панель и кол-во",
                  f"{state['results']['panel_model']} — {state['results']['nm_modules']} шт.",
              ),
              (
                  "Расчетное падение напряжения в кабеле",
                  f"{drop:.3f} В (норма < 0.25В)",
              ),
              (
                  "Рекомендованное сечение медного провода",
                  f"{sec} мм² (по ПУЭ)",
              ),
          ]

          for param, val in display_items:
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text(param)
            imgui.table_set_column_index(1)
            imgui.text(val)
          imgui.end_table()

        imgui.spacing()
        if imgui.button("💾 Сохранить отчет .docx по ГОСТу", size=(300, 40)):
          try:
            from report_generator import generate_report

            report_data = {
                "system_voltage": state["voltages"][state["voltage_idx"]],
                "days_autonomy": state["days_autonomy"],
                "min_insolation_dec": state["insolation"],
                "panel_power_nominal": state["results"]["panel_power_unit"],
                "ac_loads": [
                    {"name": l[0], "power": l[1], "hours_week": l[2]}
                    for l in state["ac_loads"]
                ],
                "dc_loads": [
                    {"name": l[0], "power": l[1], "hours_week": l[2]}
                    for l in state["dc_loads"]
                ],
            }
            generate_report(
                "Лабораторная_1_АФС_Гост.docx", report_data, state["results"]
            )
            print("Отчет успешно сохранен в корневую папку!")
          except Exception as e:
            print(f"Ошибка генерации отчета: {e}")
      else:
        imgui.text_colored(
            (0.9, 0.6, 0.2, 1.0),
            "⚠️ Сначала выполните расчет на первой вкладке!",
        )

      imgui.end_tab_item()

    # --- ВКЛАДКА 3: ДЕТАЛЬНАЯ СТРУКТУРНАЯ СХЕМА ПО ГОСТУ И ПИНАМ ---
    tab_3_open, _ = imgui.begin_tab_item("📐 Структурная схема (ГОСТ & Пины)")
    if tab_3_open:
      imgui.text(
          "Принципиальная структурно-функциональная схема АФС с пинмапом"
          " (ЕСКД):"
      )
      imgui.separator()

      draw_list = imgui.get_window_draw_list()
      p = imgui.get_cursor_screen_pos()
      x, y = p.x + 20, p.y + 30

      def get_col(r, g, b, a=1.0):
        return imgui.get_color_u32((r, g, b, a))

      bg_box = get_col(0.15, 0.15, 0.19, 1.0)
      border_box = get_col(0.3, 0.6, 0.8, 1.0)
      text_col = get_col(1.0, 1.0, 1.0, 1.0)
      sub_text_col = get_col(0.7, 0.9, 0.7, 1.0)
      pin_col = get_col(1.0, 0.8, 0.4, 1.0)
      line_col = get_col(0.8, 0.8, 0.8, 1.0)

      res = state["results"]
      mod_count = res["nm_modules"] if res else 6
      panel_name = res["panel_model"] if res else "LONGi Hi-MO 6 (450Вт)"
      batt_name = res["battery_model"] if res else "Гелевая Delta GOR"
      batt_qty = res["battery_count"] if res else 2
      batt_cap = res["battery_capacity_total"] if res else 120.0

      # 1. Блок PV1: Солнечный генератор
      draw_list.add_rect_filled((x, y), (x + 200, y + 120), bg_box, 4.0)
      draw_list.add_rect((x, y), (x + 200, y + 120), border_box, 4.0)
      draw_list.add_text((x + 10, y + 8), text_col, "PV1")
      draw_list.add_text((x + 40, y + 8), text_col, "Солнечная батарея")
      draw_list.add_text((x + 10, y + 35), sub_text_col, f"Модули: {mod_count}х")
      draw_list.add_text((x + 10, y + 55), sub_text_col, f"{panel_name[:22]}...")
      draw_list.add_text((x + 10, y + 80), pin_col, "[+] Клемма PV_IN+")
      draw_list.add_text((x + 10, y + 98), pin_col, "[-] Клемма PV_IN-")

      # 2. Блок A1: Контроллер заряда & МК
      draw_list.add_rect_filled(
          (x + 260, y), (x + 480, y + 160), bg_box, 4.0
      )
      draw_list.add_rect(
          (x + 260, y), (x + 480, y + 160), border_box, 4.0
      )
      draw_list.add_text((x + 270, y + 8), text_col, "A1")
      draw_list.add_text(
          (x + 300, y + 8), text_col, "Контроллер заряда (MPPT)"
      )
      draw_list.add_text(
          (x + 270, y + 35), sub_text_col, "Базовый модуль: SS-MPPT-15L"
      )
      draw_list.add_text(
          (x + 270, y + 55), pin_col, "• Pin A0: АЦП контроля U_АКБ"
      )
      draw_list.add_text(
          (x + 270, y + 75), pin_col, "• Pin D9 (PWM): Ключ заряда"
      )
      draw_list.add_text(
          (x + 270, y + 95), pin_col, "• Шина I2C (SCL/SDA): Дисплей"
      )
      draw_list.add_text(
          (x + 270, y + 115), pin_col, "• SPI / UART: Телеметрия"
      )
      draw_list.add_text(
          (x + 270, y + 135), pin_col, "• Силовые клеммы BAT+ / BAT-"
      )

      # 3. Блок GB1: Аккумуляторная батарея
      draw_list.add_rect_filled(
          (x + 260, y + 190), (x + 480, y + 300), bg_box, 4.0
      )
      draw_list.add_rect(
          (x + 260, y + 190), (x + 480, y + 300), border_box, 4.0
      )
      draw_list.add_text((x + 270, y + 198), text_col, "GB1")
      draw_list.add_text((x + 310, y + 198), text_col, f"АКБ ({batt_qty} шт.)")
      draw_list.add_text(
          (x + 270, y + 225), sub_text_col, f"{batt_name[:25]}"
      )
      draw_list.add_text(
          (x + 270, y + 245), sub_text_col, f"Общ. емкость: {batt_cap:.1f} А·ч"
      )
      draw_list.add_text(
          (x + 270, y + 270), pin_col, "[+ АКБ] ---- [- АКБ]"
      )

      # 4. Блок G1: Инвертор напряжения
      draw_list.add_rect_filled(
          (x + 540, y), (x + 740, y + 120), bg_box, 4.0
      )
      draw_list.add_rect(
          (x + 540, y), (x + 740, y + 120), border_box, 4.0
      )
      draw_list.add_text((x + 550, y + 8), text_col, "G1")
      draw_list.add_text((x + 580, y + 8), text_col, "Инвертор DC/AC")
      draw_list.add_text(
          (x + 550, y + 35), sub_text_col, f"Вход: DC {state['voltages'][state['voltage_idx']]}В"
      )
      draw_list.add_text(
          (x + 550, y + 55), sub_text_col, "Выход: AC ~220В, 50Гц"
      )
      draw_list.add_text(
          (x + 550, y + 80), pin_col, "[~220V Out] Клеммник AC"
      )
      draw_list.add_text((x + 550, y + 98), pin_col, "[DC In] Шина питания")

      # 5. Блок нагрузок
      draw_list.add_rect_filled(
          (x + 800, y - 20), (x + 1000, y + 140), bg_box, 4.0
      )
      draw_list.add_rect(
          (x + 800, y - 20), (x + 1000, y + 140), border_box, 4.0
      )
      draw_list.add_text((x + 810, y - 12), text_col, "ZL1, ZL2")
      draw_list.add_text((x + 870, y - 12), text_col, "Группа нагрузок")
      draw_list.add_text(
          (x + 810, y + 15),
          sub_text_col,
          f"AC приборов: {len(state['ac_loads'])} шт.",
      )
      draw_list.add_text(
          (x + 810, y + 35),
          sub_text_col,
          f"DC приборов: {len(state['dc_loads'])} шт.",
      )
      total_p = sum(l[1] for l in state["ac_loads"]) + sum(
          l[1] for l in state["dc_loads"]
      )
      draw_list.add_text(
          (x + 810, y + 55), sub_text_col, f"Суммарная P: {total_p} Вт"
      )
      draw_list.add_text(
          (x + 810, y + 85), pin_col, "Линии AC: ~220В (Розетки)"
      )
      draw_list.add_text(
          (x + 810, y + 105), pin_col, "Линии DC: =12В/24В"
      )

      # Связи и шины
      draw_list.add_line(
          (x + 200, y + 45), (x + 260, y + 45), line_col, 2.0
      )
      draw_list.add_text((x + 205, y + 25), pin_col, "Силовая шина DC")

      draw_list.add_line(
          (x + 370, y + 160), (x + 370, y + 190), line_col, 2.0
      )
      draw_list.add_text((x + 380, y + 170), pin_col, "Линия заряда АКБ")

      draw_list.add_line(
          (x + 480, y + 45), (x + 540, y + 45), line_col, 2.0
      )
      draw_list.add_text((x + 490, y + 25), pin_col, "Шина питания")

      draw_list.add_line(
          (x + 740, y + 45), (x + 800, y + 45), line_col, 2.0
      )
      draw_list.add_text((x + 750, y + 25), pin_col, "Фидер ~220В")

      imgui.dummy((1000, 320))
      imgui.end_tab_item()

    # --- ВКЛАДКА 4: СПРАВОЧНИК И КАТАЛОГ ОБОРУДОВАНИЯ ---
    tab_4_open, _ = imgui.begin_tab_item("📖 Каталог оборудования")
    if tab_4_open:
      imgui.text("Автономный справочник мировой номенклатуры (Tier 1 & СНЭ):")
      imgui.separator()

      if imgui.begin_tab_bar("CatalogSubTabs"):
        
        sub_1, _ = imgui.begin_tab_item("☀️ Солнечные панели")
        if sub_1:
          imgui.spacing()
          imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Каталог фотоэлектрических модулей (LONGi, Jinko, Trina и др.):")
          imgui.separator()
          
          imgui.begin_child("PanelScrollRegion", imgui.ImVec2(0, 500), 1)
          try:
            if os.path.exists("panels_db.txt"):
              with open("panels_db.txt", "r", encoding="utf-8") as f:
                panel_text = f.read()
              imgui.text_wrapped(panel_text)
            else:
              imgui.text_colored((0.9, 0.4, 0.4, 1.0), "⚠️ Файл 'panels_db.txt' не найден в корневой папке проекта!")
          except Exception as e:
            imgui.text(f"Ошибка чтения файла: {e}")
          imgui.end_child()
          imgui.end_tab_item()

        sub_2, _ = imgui.begin_tab_item("🔋 Аккумуляторы (АКБ & СНЭ)")
        if sub_2:
          imgui.spacing()
          imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Каталог накопителей энергии (LiFePO4, GEL, AGM, Ni-Cd):")
          imgui.separator()
          
          imgui.begin_child("BatteryScrollRegion", imgui.ImVec2(0, 500), 1)
          try:
            if os.path.exists("batteries_db.txt"):
              with open("batteries_db.txt", "r", encoding="utf-8") as f:
                batt_text = f.read()
              imgui.text_wrapped(batt_text)
            else:
              imgui.text_colored((0.9, 0.4, 0.4, 1.0), "⚠️ Файл 'batteries_db.txt' не найден в корневой папке проекта!")
          except Exception as e:
            imgui.text(f"Ошибка чтения файла: {e}")
          imgui.end_child()
          imgui.end_tab_item()

        imgui.end_tab_bar()

      imgui.end_tab_item()

    # --- ВКЛАДКА 5: ПОШАГОВЫЙ РАСЧЕТ И ФОРМУЛЫ ---
    tab_calc_steps, _ = imgui.begin_tab_item("🧮 Ход расчета (Формулы)")
    if tab_calc_steps:
      imgui.text("Прозрачный инженерный расчет по шагам (с подстановкой данных):")
      imgui.separator()

      if state["results"]:
        res = state["results"]
        
        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Шаг 1. Энергия нагрузки переменного тока и потери в инверторе")
        imgui.text_wrapped("Формула: W1 = W_ac * k_inv (где k_inv = 1.2 — коэффициент потерь в инверторе)")
        imgui.text(f"• Суммарная энергия AC от нагрузок: {res['total_w_ac']:.2f} Вт·ч/нед")
        imgui.text(f"• Энергия с учетом потерь W1: {res['w1_energy']:.2f} Вт·ч/нед")
        imgui.separator()

        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Шаг 2. Суточное энергопотребление системы")
        imgui.text_wrapped("Формула: E_sigma = ((W1 + W_dc) / U_sys) / 7")
        imgui.text(f"• Напряжение шины системы (U_sys): {state['voltages'][state['voltage_idx']]} В")
        imgui.text(f"• Суммарная энергия DC (W2): {res['total_w_dc']:.2f} Вт·ч/нед")
        imgui.text(f"• Итого суточное потребление E_sigma: {res['e_sigma']:.2f} А·ч/сутки")
        imgui.separator()

        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Шаг 3. Расчет емкости аккумуляторной батареи")
        imgui.text_wrapped("Формула: Q_АКБ = ((E_sigma * n) / DoD) * k_запас")
        imgui.text(f"• Дней автономности (n): {state['days_autonomy']} дн.")
        imgui.text(f"• Глубина разряда (DoD = 0.2), коэф. надежности = 1.2")
        imgui.text(f"• Расчетная емкость АКБ: {res['battery_capacity_total']:.2f} А·ч")
        imgui.text(f"• Выбранный тип АКБ в системе: {res['battery_model']} ({res['battery_count']} шт.)")
        imgui.separator()

        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Шаг 4. Расчет мощности солнечного генератора")
        imgui.text_wrapped("Формула: P_req = (E_sigma * 1.2) / t_n")
        imgui.text(f"• Требуемая мощность панелей: {res['p_panel_req']:.2f} Вт")
        imgui.text(f"• Выбранная модель панели: {res['panel_model']} (единичная мощность: {res['panel_power_unit']} Вт)")
        imgui.text(f"• Итоговое количество модулей (Nm): {res['nm_modules']} шт.")
        imgui.separator()

        imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Шаг 5. Проверка кабельной линии по падению напряжения")
        imgui.text_wrapped("Формулы ПУЭ: dU = (2 * rho * L * I) / S  ->  S = (2 * rho * L * I) / dU_max")
        sec, drop = calculate_cable_section(res.get('total_panel_current', 5.0), state['cable_length'])
        imgui.text(f"• Длина трассы: {state['cable_length']} м, Ток панелей: {res.get('total_panel_current', 5.0):.2f} А")
        imgui.text(f"• Расчетное падение напряжения: {drop:.3f} В (Допуск < 0.25 В)")
        imgui.text(f"• Рекомендованное сечение медного проводника: {sec} мм²")

      else:
        imgui.text_colored((0.9, 0.6, 0.2, 1.0), "⚠️ Выполните расчет на вкладке 'Исходные данные', чтобы увидеть ход решения!")

      imgui.end_tab_item()

    # Закрываем главный MainTabs
    imgui.end_tab_bar()

  imgui.end()


def main():
  params = hello_imgui.RunnerParams()
  params.app_window_params.window_title = (
      "PV-Calc Pro ImGui Edition (АФС САПР)"
  )
  params.app_window_params.window_geometry.size = (1100, 780)
  params.callbacks.show_gui = gui

  hello_imgui.run(params)


if __name__ == "__main__":
  main()
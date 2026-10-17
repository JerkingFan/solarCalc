# report_generator.py
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

def generate_report(filename, input_data, results):
    doc = docx.Document()
    
    # Настройка полей страницы
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.18) # 3 см для левого поля
        section.right_margin = Inches(0.5)  # 1.5 см для правого
        
    # Базовый стиль шрифта
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(14)
    font.color.rgb = RGBColor(0, 0, 0)
    
    # --- ТИТУЛЬНАЯ / ШАПОЧНАЯ ЧАСТЬ ---
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("ЛАБОРАТОРНАЯ РАБОТА №1\nРАСЧЕТ И ФУНКЦИОНАЛЬНЫЙ КОНТРОЛЬ ПАРАМЕТРОВ АВТОНОМНОЙ ФОТОЭЛЕКТРИЧЕСКОЙ СИСТЕМЫ")
    run_title.bold = True
    run_title.font.size = Pt(14)
    
    doc.add_paragraph() # Пустая строка
    
    # --- ЦЕЛЬ РАБОТЫ ---
    p_goal = doc.add_paragraph()
    p_goal.add_run("Цель работы: ").bold = True
    p_goal.add_run("изучить типы и состав применяемых фотоэлектрических систем, устройство и принципы работы основных блоков и узлов фотоэлектрической установки, освоить методологию расчетов фотоэлектрической системы и получить навыки контроля параметров фотоэлектрической системы.")

    # --- ИСХОДНЫЕ ДАННЫЕ ---
    p_h1 = doc.add_paragraph()
    run_h1 = p_h1.add_run("1. ИСХОДНЫЕ ДАННЫЕ И ВАРИАНТ")
    run_h1.bold = True
    
    p_params = doc.add_paragraph()
    p_params.add_run(f"• Напряжение системы: {input_data['system_voltage']} В\n")
    p_params.add_run(f"• Дней автономности (n): {input_data['days_autonomy']}\n")
    p_params.add_run(f"• Минимальная декабрьская инсоляция (Eдек): {input_data['min_insolation_dec']} кВт·ч/м²\n")
    p_params.add_run(f"• Номинальная мощность солнечного модуля (Pн): {input_data['panel_power_nominal']} Вт")

    # Таблица нагрузок AC в отчете
    doc.add_paragraph("Таблица 1.1 — Энергозатраты потребителей переменного тока")
    table_ac = doc.add_table(rows=1, cols=3)
    table_ac.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    hdr_cells = table_ac.rows[0].cells
    hdr_cells[0].text = "Прибор"
    hdr_cells[1].text = "Мощность, Вт"
    hdr_cells[2].text = "Часов в неделю, t"
    
    for load in input_data['ac_loads']:
        row_cells = table_ac.add_row().cells
        row_cells[0].text = load['name']
        row_cells[1].text = str(load['power'])
        row_cells[2].text = str(load['hours_week'])
        
    doc.add_paragraph()

    # Таблица нагрузок DC в отчете
    if input_data.get('dc_loads'):
        doc.add_paragraph("Таблица 1.2 — Энергозатраты потребителей постоянного тока")
        table_dc = doc.add_table(rows=1, cols=3)
        table_dc.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        hdr_cells_dc = table_dc.rows[0].cells
        hdr_cells_dc[0].text = "Прибор DC"
        hdr_cells_dc[1].text = "Мощность, Вт"
        hdr_cells_dc[2].text = "Часов в неделю, t"
        
        for load in input_data['dc_loads']:
            row_cells = table_dc.add_row().cells
            row_cells[0].text = load['name']
            row_cells[1].text = str(load['power'])
            row_cells[2].text = str(load['hours_week'])
            
        doc.add_paragraph()

    # --- РЕЗУЛЬТАТЫ РАСЧЕТА ---
    p_h2 = doc.add_paragraph()
    run_h2 = p_h2.add_run("2. РЕЗУЛЬТАТЫ РАСЧЕТА ПАРАМЕТРОВ АФС")
    run_h2.bold = True
    
    table_res = doc.add_table(rows=1, cols=2)
    table_res.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_res.rows[0].cells[0].text = "Параметр"
    table_res.rows[0].cells[1].text = "Значение"
    
    res_items = [
        ("Суммарная энергия переменного тока", f"{results['total_w_ac']:.2f} Вт·ч/нед"),
        ("Энергия с учетом потерь в инверторе W1", f"{results['w1_energy']:.2f} Вт·ч/нед"),
        ("Энергия потребителей постоянного тока W2", f"{results.get('total_w_dc', 0):.2f} Вт·ч/нед"),
        ("Суточное энергопотребление E_sigma", f"{results['e_sigma']:.2f} А·ч/сутки"),
        ("Полная емкость аккумуляторной батареи (АКБ)", f"{results['battery_capacity_total']:.2f} А·ч"),
        ("Требуемая мощность солнечной батареи", f"{results['p_panel_req']:.2f} Вт"),
        ("Количество солнечных модулей (округлено)", f"{results['nm_modules']} шт.")
    ]
    
    for param, val in res_items:
        row_cells = table_res.add_row().cells
        row_cells[0].text = param
        row_cells[1].text = val

# Добавить в report_generator.py в конец документа:
    p_h3 = doc.add_paragraph()
    run_h3 = p_h3.add_run("3. СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ (BOM) И АНАЛИЗ НАДЕЖНОСТИ")
    run_h3.bold = True

    table_bom = doc.add_table(rows=1, cols=4)
    table_bom.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table_bom.rows[0].cells
    hdr[0].text = "Наименование элемента"
    hdr[1].text = "Модель / Тип"
    hdr[2].text = "Кол-во"
    hdr[3].text = "Параметры / Примечание"

    bom_items = [
        ("Солнечная батарея", results['panel_model'], f"{results['nm_modules']} шт.", f"Пиковая мощность: {results['p_panel_req']:.1f} Вт"),
        ("Аккумуляторная батарея", "Гелиевая тяговая 120Ач", "1 упр.", f"Емкость: {results['battery_capacity_total']:.1f} А·ч"),
        ("Контроллер заряда", results['controller_model'], "1 шт.", f"Макс. ток: {results.get('total_panel_current', 0):.1f} А"),
        ("Инвертор напряжения", f"Автономный {input_data['system_voltage']}В", "1 шт.", "КПД = 80%")
    ]

    for item in bom_items:
        row = table_bom.add_row().cells
        row[0].text = item[0]
        row[1].text = item[1]
        row[2].text = item[2]
        row[3].text = item[3]

    # Сохранение файла
    doc.save(filename)
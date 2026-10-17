# ui.py
import sys
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from core import CLIMATE_DATA, SolarSystemCalculator
from report_generator import generate_report


class MapBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

    @pyqtSlot(float, float)
    def receive_coords(self, lat, lon):
        # Координаты городов Беларуси для привязки клика
        cities_coords = {
            "Минск": (53.9, 27.56),
            "Брест": (52.09, 23.7),
            "Гомель": (52.43, 30.98),
            "Витебск": (55.19, 30.2),
            "Гродно": (53.68, 23.83),
            "Могилев": (53.9, 30.33)
        }
        
        # Находим ближайший город к точке клика на карте
        nearest_city = min(cities_coords, key=lambda c: (cities_coords[c][0] - lat)**2 + (cities_coords[c][1] - lon)**2)
        
        # Передаем данные в главное окно интерфейса
        if self.parent_window:
            self.parent_window.combo_city.setCurrentText(nearest_city)
            print(f"Клик на карте: Широта {lat:.2f}, Долгота {lon:.2f} -> Выбран город: {nearest_city}")


class SolarAppWindow(QMainWindow):

  def __init__(self):
    super().__init__()
    self.setWindowTitle(
        "PV-Calc Pro v2.0 — Геоинформационный расчетный модуль АФС"
    )
    self.resize(1200, 850)
    self.init_styles()
    self.init_ui()

  def init_styles(self):
    self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            QTabWidget::pane {
                border: 1px solid #333333;
                background: #252526;
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #858585;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                color: #ffffff;
                border-bottom: 2px solid #007acc;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
            QPushButton.danger {
                background-color: #a22d2d;
            }
            QPushButton.danger:hover {
                background-color: #c53b3b;
            }
            QLineEdit, QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #515151;
                padding: 6px;
                border-radius: 3px;
                color: white;
            }
            QTableWidget {
                background-color: #252526;
                gridline-color: #3f3f46;
                border: 1px solid #333333;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 5px;
                border: 1px solid #3f3f46;
            }
        """)

  def init_ui(self):
    central_widget = QWidget()
    self.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)

    # Заголовок
    header_label = QLabel(
        "ГИС-Модуль проектирования автономных фотоэлектрических систем"
    )
    header_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    header_label.setStyleSheet("color: #4ec9b0; margin-bottom: 5px;")
    main_layout.addWidget(header_label)

    # Табы (Вкладки)
    self.tabs = QTabWidget()
    main_layout.addWidget(self.tabs)

    self.create_input_tab()
    self.create_map_tab()
    self.create_results_tab()

  def create_input_tab(self):
    tab = QWidget()
    layout = QHBoxLayout(tab)

    # Левая колонка: Параметры системы и ГИС-модуль
    left_layout = QVBoxLayout()

    params_group = QGroupBox("ГИС-параметры и климат местности")
    params_layout = QFormLayout(params_group)

    self.combo_voltage = QComboBox()
    self.combo_voltage.addItems(["12", "24", "48"])
    self.combo_voltage.setCurrentText("24")

    # Селекторы гео-точки и календаря
    self.combo_city = QComboBox()
    self.combo_city.addItems([
        "Минск",
        "Брест",
        "Гомель",
        "Витебск",
        "Гродно",
        "Могилев",
    ])
    self.combo_city.currentIndexChanged.connect(self.update_insolation_auto)

    self.combo_month = QComboBox()
    self.combo_month.addItems([
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ])
    self.combo_month.setCurrentText("Декабрь")
    self.combo_month.currentIndexChanged.connect(self.update_insolation_auto)

    # Тип рельефа и затененности
    self.combo_relief = QComboBox()
    self.combo_relief.addItems([
        "Открытая равнина (коэф. 1.0)",
        "Холмистая местность (затенение, коэф. 0.92)",
        "Плотная городская застройка / промзона (коэф. 0.85)",
    ])

    self.input_autonomy = QLineEdit("5")  # дни автономности (n)
    self.input_insolation = QLineEdit("0.9")  # автоподставляемое E
    self.input_panel_power = QLineEdit("50")  # Pн (мощность модуля)

    params_layout.addRow("Регион / Город:", self.combo_city)
    params_layout.addRow("Расчетный месяц:", self.combo_month)
    params_layout.addRow("Тип рельефа / Окружение:", self.combo_relief)
    params_layout.addRow("Напряжение системы (В):", self.combo_voltage)
    params_layout.addRow("Дней без солнца (n):", self.input_autonomy)
    params_layout.addRow("Инсоляция E (кВт·ч/м²):", self.input_insolation)
    params_layout.addRow("Мощность модуля Pн (Вт):", self.input_panel_power)

    left_layout.addWidget(params_group)
    left_layout.addStretch()

    # Кнопка расчета
    calc_btn = QPushButton("Выполнить ГИС-расчет САПР")
    calc_btn.clicked.connect(self.run_calculation)
    left_layout.addWidget(calc_btn)

    layout.addLayout(left_layout, 1)

    # Правая колонка: Таблицы нагрузок (AC и DC) с кнопками управления
    right_layout = QVBoxLayout()

    # 1. Таблица переменного тока (AC)
    loads_ac_group = QGroupBox("Нагрузки переменного тока (Таблица 1.1)")
    loads_ac_layout = QVBoxLayout(loads_ac_group)

    self.table_ac = QTableWidget(0, 3)
    self.table_ac.setHorizontalHeaderLabels(
        ["Прибор", "Мощность (Вт)", "Часов в неделю (t)"]
    )
    self.table_ac.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch
    )

    default_ac = [
        ("Освещение", "100", "35"),
        ("Холодильник", "150", "84"),
        ("Телевизор", "80", "20"),
    ]
    for row_data in default_ac:
      self.add_row_to_table(self.table_ac, row_data)

    ac_btn_layout = QHBoxLayout()
    add_ac_btn = QPushButton("➕ Добавить прибор (AC)")
    add_ac_btn.clicked.connect(lambda: self.add_row_to_table(self.table_ac))
    del_ac_btn = QPushButton("➖ Удалить строку")
    del_ac_btn.setProperty("class", "danger")
    del_ac_btn.clicked.connect(lambda: self.delete_row_from_table(self.table_ac))
    ac_btn_layout.addWidget(add_ac_btn)
    ac_btn_layout.addWidget(del_ac_btn)

    loads_ac_layout.addWidget(self.table_ac)
    loads_ac_layout.addLayout(ac_btn_layout)
    right_layout.addWidget(loads_ac_group)

    # 2. Таблица постоянного тока (DC)
    loads_dc_group = QGroupBox("Нагрузки постоянного тока (Таблица 1.2)")
    loads_dc_layout = QVBoxLayout(loads_dc_group)

    self.table_dc = QTableWidget(0, 3)
    self.table_dc.setHorizontalHeaderLabels(
        ["Прибор DC", "Мощность (Вт)", "Часов в неделю (t)"]
    )
    self.table_dc.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch
    )

    default_dc = [("Роутер 12В", "15", "168"), ("Аварийный свет", "20", "14")]
    for row_data in default_dc:
      self.add_row_to_table(self.table_dc, row_data)

    dc_btn_layout = QHBoxLayout()
    add_dc_btn = QPushButton("➕ Добавить прибор (DC)")
    add_dc_btn.clicked.connect(lambda: self.add_row_to_table(self.table_dc))
    del_dc_btn = QPushButton("➖ Удалить строку")
    del_dc_btn.setProperty("class", "danger")
    del_dc_btn.clicked.connect(lambda: self.delete_row_from_table(self.table_dc))
    dc_btn_layout.addWidget(add_dc_btn)
    dc_btn_layout.addWidget(del_dc_btn)

    loads_dc_layout.addWidget(self.table_dc)
    loads_dc_layout.addLayout(dc_btn_layout)
    right_layout.addWidget(loads_dc_group)

    layout.addLayout(right_layout, 2)
    self.tabs.addTab(tab, "⚙️ ГИС-данные и нагрузки")

  def create_map_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)

    self.map_view = QWebEngineView()
    
    # Настраиваем канал связи Python <-> JS (мост для кликов)
    self.bridge = MapBridge(self)
    self.channel = QWebChannel()
    self.channel.registerObject('bridge', self.bridge)
    self.map_view.page().setWebChannel(self.channel)

    html_map = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style> body, html { height: 100%; margin: 0; background: #1e1e1e; } #map { height: 100%; width: 100%; }</style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([53.9, 27.56], 7);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 18,
                }).addTo(map);
                
                var marker = L.marker([53.9, 27.56], {draggable: true}).addTo(map);

                var bridge;
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    bridge = channel.objects.bridge;
                });
                
                map.on('click', function(e) {
                    marker.setLatLng(e.latlng);
                    if (bridge) {
                        bridge.receive_coords(e.latlng.lat, e.latlng.lng);
                    }
                });
                
                marker.on('dragend', function(e) {
                    var pos = marker.getLatLng();
                    if (bridge) {
                        bridge.receive_coords(pos.lat, pos.lng);
                    }
                });
            </script>
        </body>
        </html>
        """
    self.map_view.setHtml(html_map)
    layout.addWidget(self.map_view)
    self.tabs.addTab(tab, "🗺️ ГИС Карта")

  def update_insolation_auto(self):
    city = self.combo_city.currentText()
    month = self.combo_month.currentText()
    val = CLIMATE_DATA.get(city, {}).get(month, 0.9)
    self.input_insolation.setText(str(val))

  def add_row_to_table(self, table, data=None):
    row_position = table.rowCount()
    table.insertRow(row_position)
    for col in range(3):
      val = data[col] if data and col < len(data) else ""
      table.setItem(row_position, col, QTableWidgetItem(val))

  def delete_row_from_table(self, table):
    selected_rows = set(item.row() for item in table.selectedItems())
    for row in sorted(selected_rows, reverse=True):
      table.removeRow(row)

  def gather_loads(self):
    ac_loads = []
    for row in range(self.table_ac.rowCount()):
      name_item = self.table_ac.item(row, 0)
      power_item = self.table_ac.item(row, 1)
      hours_item = self.table_ac.item(row, 2)
      if name_item and power_item and hours_item and name_item.text().strip():
        ac_loads.append({
            "name": name_item.text(),
            "power": float(power_item.text()),
            "hours_week": float(hours_item.text()),
        })

    dc_loads = []
    for row in range(self.table_dc.rowCount()):
      name_item = self.table_dc.item(row, 0)
      power_item = self.table_dc.item(row, 1)
      hours_item = self.table_dc.item(row, 2)
      if name_item and power_item and hours_item and name_item.text().strip():
        dc_loads.append({
            "name": name_item.text(),
            "power": float(power_item.text()),
            "hours_week": float(hours_item.text()),
        })
    return ac_loads, dc_loads

  def create_results_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)

    self.results_table = QTableWidget(9, 2)
    self.results_table.setHorizontalHeaderLabels(
        ["Параметр расчета", "Значение"]
    )
    self.results_table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch
    )
    layout.addWidget(self.results_table)

    # Кнопка генерации Word отчета
    self.export_btn = QPushButton("💾 Сгенерировать ГИС-отчет .docx по ГОСТу")
    self.export_btn.setStyleSheet(
        "background-color: #28a745; font-size: 11pt; padding: 10px;"
    )
    self.export_btn.clicked.connect(self.export_to_docx)
    layout.addWidget(self.export_btn)

    self.tabs.addTab(tab, "📊 Результаты расчетов и ГИС-анализ")

  def run_calculation(self):
    try:
      ac_loads, dc_loads = self.gather_loads()
      relief_idx = self.combo_relief.currentIndex()
      relief_coeffs = [1.0, 0.92, 0.85]
      r_coeff = relief_coeffs[relief_idx]

      data = {
          "ac_loads": ac_loads,
          "dc_loads": dc_loads,
          "days_autonomy": float(self.input_autonomy.text()),
          "city": self.combo_city.currentText(),
          "month": self.combo_month.currentText(),
          "relief_coefficient": r_coeff,
          "min_insolation_dec": float(self.input_insolation.text()),
          "panel_power_nominal": float(self.input_panel_power.text()),
          "system_voltage": float(self.combo_voltage.currentText()),
      }

      calc = SolarSystemCalculator(data)
      res = calc.calculate()

      display_data = [
          ("Выбранный регион / Город", f"{data['city']} ({data['month']})"),
          ("Коэффициент рельефа и затенения", f"{r_coeff}"),
          ("Суммарная энергия переменного тока (Вт·ч/нед)", f"{res['total_w_ac']:.2f}"),
          (
              "Энергия с учетом потерь в инверторе W1 (Вт·ч/нед)",
              f"{res['w1_energy']:.2f}",
          ),
          (
              "Энергия потребителей постоянного тока W2 (Вт·ч/нед)",
              f"{res.get('total_w_dc', 0):.2f}",
          ),
          ("Суточное энергопотребление E_sigma (А·ч/сутки)", f"{res['e_sigma']:.2f}"),
          (
              "Полная емкость аккумуляторной батареи (А·ч)",
              f"{res['battery_capacity_total']:.2f}",
          ),
          ("Требуемая мощность солнечной батареи (Вт)", f"{res['p_panel_req']:.2f}"),
          (
              "Количество солнечных модулей (шт)",
              f"{res['nm_modules']} (с учетом рельефа)",
          ),
      ]

      self.results_table.setRowCount(len(display_data))
      for row, (param, val) in enumerate(display_data):
        self.results_table.setItem(row, 0, QTableWidgetItem(param))
        self.results_table.setItem(row, 1, QTableWidgetItem(val))

      self.tabs.setCurrentIndex(2)

    except Exception as e:
      print(f"Ошибка расчета: {e}")

  def export_to_docx(self):
    try:
      ac_loads, dc_loads = self.gather_loads()
      relief_idx = self.combo_relief.currentIndex()
      relief_coeffs = [1.0, 0.92, 0.85]

      data = {
          "ac_loads": ac_loads,
          "dc_loads": dc_loads,
          "days_autonomy": float(self.input_autonomy.text()),
          "city": self.combo_city.currentText(),
          "month": self.combo_month.currentText(),
          "relief_coefficient": relief_coeffs[relief_idx],
          "min_insolation_dec": float(self.input_insolation.text()),
          "panel_power_nominal": float(self.input_panel_power.text()),
          "system_voltage": float(self.combo_voltage.currentText()),
      }

      calc = SolarSystemCalculator(data)
      res = calc.calculate()

      file_path, _ = QFileDialog.getSaveFileName(
          self,
          "Сохранить ГИС-отчет лабораторной",
          "Лабораторная_1_АФС_ГИС.docx",
          "Word Documents (*.docx)",
      )
      if file_path:
        generate_report(file_path, data, res)
        QMessageBox.information(
            self,
            "Успех!",
            f"ГИС-отчет успешно сгенерирован и сохранен:\n{file_path}",
        )
    except Exception as e:
      QMessageBox.critical(self, "Ошибка", f"Не удалось создать отчет: {e}")


if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = SolarAppWindow()
  window.show()
  sys.exit(app.exec())
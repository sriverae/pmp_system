"""
Modulo Costos - Analisis de costos de mantenimiento.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont
from app.services.ot_service import OTService
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER
)
from datetime import datetime


class CostosWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self.calcular()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16,12,16,12); lay.setSpacing(12)

        enc = QHBoxLayout()
        lbl = QLabel("Analisis de Costos de Mantenimiento")
        lbl.setStyleSheet(f"font-size:18px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        enc.addWidget(lbl); enc.addStretch()
        lay.addLayout(enc)

        # Filtros
        fil = QHBoxLayout(); fil.setSpacing(8)
        self.fecha_desde = QDateEdit(); self.fecha_desde.setDate(QDate.currentDate().addDays(-90)); self.fecha_desde.setCalendarPopup(True)
        self.fecha_hasta = QDateEdit(); self.fecha_hasta.setDate(QDate.currentDate()); self.fecha_hasta.setCalendarPopup(True)
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Todos los tipos","Preventivo","Correctivo","Inspección","Predictivo","Emergencia"])
        self.combo_tipo.setFixedWidth(150)
        btn_calc = QPushButton("Calcular")
        btn_calc.setStyleSheet(f"background-color:{COLOR_ACCENT_BLUE}; color:white; font-weight:600; border-radius:4px; border:none; padding:6px 16px;")
        btn_calc.clicked.connect(self.calcular)
        btn_exp = QPushButton("Exportar Excel")
        btn_exp.clicked.connect(self._exportar)
        fil.addWidget(QLabel("Desde:")); fil.addWidget(self.fecha_desde)
        fil.addWidget(QLabel("Hasta:")); fil.addWidget(self.fecha_hasta)
        fil.addWidget(QLabel("Tipo:")); fil.addWidget(self.combo_tipo)
        fil.addWidget(btn_calc); fil.addWidget(btn_exp); fil.addStretch()
        lay.addLayout(fil)

        # Cards resumen
        self._grid_cards = QGridLayout(); self._grid_cards.setSpacing(12)
        lay.addLayout(self._grid_cards)

        # Tabla detalle
        lbl_det = QLabel("Detalle de OTs por Costo")
        lbl_det.setStyleSheet(f"font-weight:700; color:{COLOR_TEXT_PRIMARY}; font-size:13px;")
        lay.addWidget(lbl_det)

        self.tabla = QTableWidget(0, 8)
        self.tabla.setHorizontalHeaderLabels(["Numero","Equipo","Tipo","Estado","Fecha Cierre","Costo MO","Costo Mat.","Costo Total"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSortingEnabled(True)
        for i, w in enumerate([110,160,100,90,100,90,90]):
            self.tabla.setColumnWidth(i, w)
        lay.addWidget(self.tabla)

    def _card(self, titulo, valor, color):
        f = QFrame()
        f.setMinimumSize(160, 90)
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        f.setStyleSheet(f"background-color:{COLOR_BG_PANEL}; border-radius:8px; border:1px solid {COLOR_BORDER}; border-left:4px solid {color};")
        lay = QVBoxLayout(f); lay.setContentsMargins(14,10,14,10); lay.setSpacing(2)
        lt = QLabel(titulo.upper())
        lt.setStyleSheet(f"font-size:10px; color:{COLOR_TEXT_SECONDARY}; letter-spacing:1px; font-weight:600; border:none;")
        lt.setWordWrap(True)
        lv = QLabel(valor)
        lv.setStyleSheet(f"font-size:22px; font-weight:700; color:{color}; border:none;")
        lay.addWidget(lt); lay.addWidget(lv)
        return f

    def calcular(self):
        fd = self.fecha_desde.date(); fh = self.fecha_hasta.date()
        desde = datetime(fd.year(), fd.month(), fd.day())
        hasta = datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59)
        tipo = self.combo_tipo.currentText()

        filtros = {"fecha_desde": desde, "fecha_hasta": hasta, "estado": "Cerrada"}
        if tipo != "Todos los tipos":
            filtros["tipo_ot"] = tipo

        try:
            ots = OTService.listar_ots(filtros)
        except Exception as e:
            print(f"[Costos] Error: {e}"); ots = []

        # Calcular totales
        costo_total = sum(o.costo_total or 0 for o in ots)
        costo_mo    = sum(o.costo_mano_obra or 0 for o in ots)
        costo_mat   = sum(o.costo_materiales or 0 for o in ots)
        costo_ext   = sum(o.costo_externo or 0 for o in ots)
        n_ots       = len(ots)
        promedio    = costo_total / n_ots if n_ots else 0

        # Cards
        while self._grid_cards.count():
            item = self._grid_cards.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        cards = [
            ("Costo Total Periodo",    f"{costo_total:,.2f}",  COLOR_ACCENT_BLUE),
            ("Costo Mano de Obra",     f"{costo_mo:,.2f}",     "#7B1FA2"),
            ("Costo Materiales",       f"{costo_mat:,.2f}",    "#1565C0"),
            ("Costo Externo/Servicio", f"{costo_ext:,.2f}",    "#E65100"),
            ("OTs Cerradas",           str(n_ots),             COLOR_SUCCESS),
            ("Costo Promedio / OT",    f"{promedio:,.2f}",     COLOR_WARNING),
        ]
        for i, (t, v, c) in enumerate(cards):
            self._grid_cards.addWidget(self._card(t, v, c), i//3, i%3)

        # Tabla
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        for ot in ots:
            r = self.tabla.rowCount(); self.tabla.insertRow(r)
            try: eq = ot.equipo.nombre if ot.equipo else "-"
            except: eq = "-"
            fecha_c = ot.fecha_cierre.strftime("%d/%m/%Y") if ot.fecha_cierre else "-"
            vals = [ot.numero, eq, ot.tipo_ot, ot.estado, fecha_c,
                    f"{ot.costo_mano_obra or 0:,.2f}",
                    f"{ot.costo_materiales or 0:,.2f}",
                    f"{ot.costo_total or 0:,.2f}"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 7:  # Costo total
                    ct = ot.costo_total or 0
                    if ct > promedio * 1.5:
                        item.setForeground(QColor(COLOR_DANGER))
                    elif ct > promedio:
                        item.setForeground(QColor(COLOR_WARNING))
                self.tabla.setItem(r, c, item)
        self.tabla.setSortingEnabled(True)

    def _exportar(self):
        ruta, _ = QFileDialog.getSaveFileName(self,"Exportar Costos","costos_mantenimiento.xlsx","Excel (*.xlsx)")
        if not ruta: return
        try:
            import pandas as pd
            fd = self.fecha_desde.date(); fh = self.fecha_hasta.date()
            ots = OTService.listar_ots({
                "fecha_desde": datetime(fd.year(),fd.month(),fd.day()),
                "fecha_hasta": datetime(fh.year(),fh.month(),fh.day(),23,59,59),
                "estado": "Cerrada"
            })
            datos = [{
                "Numero": o.numero,
                "Equipo": o.equipo.nombre if o.equipo else "-",
                "Tipo": o.tipo_ot, "Estado": o.estado,
                "Fecha Cierre": o.fecha_cierre.strftime("%d/%m/%Y") if o.fecha_cierre else "-",
                "Costo MO": o.costo_mano_obra or 0,
                "Costo Materiales": o.costo_materiales or 0,
                "Costo Externo": o.costo_externo or 0,
                "Costo Total": o.costo_total or 0,
            } for o in ots]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self,"Exportado", ruta)
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

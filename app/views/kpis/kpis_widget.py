"""
Módulo KPIs — Indicadores clave de mantenimiento con gráficos.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout, QSizePolicy, QTabWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

from app.services.kpi_service import KPIService, KPIResultado
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_BORDER,
    COLOR_BG_PANEL, COLOR_BG_MEDIUM
)
from datetime import datetime


class KpisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._kpi: KPIResultado = None
        self._construir_ui()
        self.calcular()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Encabezado
        enc = QHBoxLayout()
        lbl = QLabel("[KPI]  KPIs de Mantenimiento")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")

        # Filtro período
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(
            ["Últimos 30 días", "Últimos 90 días", "Últimos 6 meses",
             "Último año", "Personalizado"])
        self.combo_periodo.setFixedWidth(160)
        self.combo_periodo.currentIndexChanged.connect(
            self._on_cambio_periodo)

        lbl_desde = QLabel("Desde:")
        lbl_desde.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addDays(-90))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setFixedWidth(110)

        lbl_hasta = QLabel("Hasta:")
        lbl_hasta.setStyleSheet(lbl_desde.styleSheet())
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setFixedWidth(110)

        btn_calc = QPushButton("Calcular KPIs")
        btn_calc.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"font-weight: 600; border-radius: 4px; border: none; "
            f"padding: 6px 16px;")
        btn_calc.clicked.connect(self.calcular)

        btn_exp = QPushButton("[Exp] Exportar")
        btn_exp.setFixedHeight(30)
        btn_exp.clicked.connect(self._exportar)

        enc.addWidget(lbl)
        enc.addStretch()
        enc.addWidget(self.combo_periodo)
        enc.addWidget(lbl_desde)
        enc.addWidget(self.fecha_desde)
        enc.addWidget(lbl_hasta)
        enc.addWidget(self.fecha_hasta)
        enc.addWidget(btn_calc)
        enc.addWidget(btn_exp)
        layout.addLayout(enc)

        tabs = QTabWidget()

        # -- Tab 1: Resumen general -------------------------------------
        tab1 = QScrollArea()
        tab1.setWidgetResizable(True)
        tab1.setFrameShape(QFrame.Shape.NoFrame)
        cont1 = QWidget()
        tab1.setWidget(cont1)
        self._lay_resumen = QVBoxLayout(cont1)
        self._lay_resumen.setContentsMargins(8, 8, 8, 8)
        self._lay_resumen.setSpacing(16)

        # Grid de tarjetas KPI
        self._grid_kpis = QGridLayout()
        self._grid_kpis.setSpacing(12)
        self._lay_resumen.addLayout(self._grid_kpis)

        # Panel gráficos
        self._lay_graficos = QHBoxLayout()
        self._lay_graficos.setSpacing(16)
        self._lay_resumen.addLayout(self._lay_graficos)
        self._lay_resumen.addStretch()

        tabs.addTab(tab1, "Resumen General")

        # -- Tab 2: Desglose por equipo ---------------------------------
        tab2 = QWidget()
        lay2 = QVBoxLayout(tab2)
        lay2.setSpacing(8)

        self.tabla_equipos = QTableWidget(0, 9)
        self.tabla_equipos.setHorizontalHeaderLabels([
            "Código", "Nombre", "Área", "Criticidad",
            "MTTR (h)", "MTBF (h)", "Disponib. %",
            "Fallas", "Costo"])
        self.tabla_equipos.horizontalHeader().setStretchLastSection(True)
        self.tabla_equipos.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_equipos.setAlternatingRowColors(True)
        self.tabla_equipos.verticalHeader().setVisible(False)
        self.tabla_equipos.setSortingEnabled(True)

        btn_act_eq = QPushButton("[Act] Actualizar desglose")
        btn_act_eq.clicked.connect(self._cargar_tabla_equipos)
        lay2.addWidget(self.tabla_equipos)
        lay2.addWidget(btn_act_eq)
        tabs.addTab(tab2, "Por Equipo")

        # -- Tab 3: Top fallas ------------------------------------------
        tab3 = QWidget()
        lay3 = QVBoxLayout(tab3)
        self.tabla_fallas = QTableWidget(0, 5)
        self.tabla_fallas.setHorizontalHeaderLabels([
            "Equipo", "Área", "Fallas", "Tiempo Muerto (h)", "Costo"])
        self.tabla_fallas.horizontalHeader().setStretchLastSection(True)
        self.tabla_fallas.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_fallas.setAlternatingRowColors(True)
        self.tabla_fallas.verticalHeader().setVisible(False)
        lay3.addWidget(QLabel(
            "Equipos con mayor número de fallas en el período:"))
        lay3.addWidget(self.tabla_fallas)
        tabs.addTab(tab3, "Top Fallas")

        layout.addWidget(tabs)

    def _on_cambio_periodo(self):
        hoy = QDate.currentDate()
        opt = self.combo_periodo.currentText()
        periodos = {
            "Últimos 30 días": -30,
            "Últimos 90 días": -90,
            "Últimos 6 meses": -180,
            "Último año": -365,
        }
        if opt in periodos:
            self.fecha_desde.setDate(hoy.addDays(periodos[opt]))
            self.fecha_hasta.setDate(hoy)
            self.calcular()

    def calcular(self):
        fd = self.fecha_desde.date()
        fh = self.fecha_hasta.date()
        desde = datetime(fd.year(), fd.month(), fd.day())
        hasta = datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59)

        self._kpi = KPIService.calcular_kpis(desde, hasta)
        self._renderizar_tarjetas()
        self._renderizar_graficos()
        self._cargar_top_fallas()

    def _tipo_card(self, valor: float, umbral_ok: float,
                    umbral_warn: float, inverso: bool = False) -> str:
        """Determina el tipo de tarjeta según umbrales."""
        if inverso:
            if valor <= umbral_ok:
                return "success"
            if valor <= umbral_warn:
                return "warning"
            return "danger"
        else:
            if valor >= umbral_ok:
                return "success"
            if valor >= umbral_warn:
                return "warning"
            return "danger"

    def _renderizar_tarjetas(self):
        # Limpiar
        while self._grid_kpis.count():
            item = self._grid_kpis.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        kpi = self._kpi
        colores = {
            "info":    COLOR_ACCENT_BLUE,
            "success": COLOR_SUCCESS,
            "warning": COLOR_WARNING,
            "danger":  COLOR_DANGER,
        }

        datos_tarjetas = [
            # (título, valor_str, unidad, tipo_color)
            ("MTTR", f"{kpi.mttr:.2f}", "horas",
             self._tipo_card(kpi.mttr, 4, 8, inverso=True)),
            ("MTBF", f"{kpi.mtbf:.2f}", "horas",
             self._tipo_card(kpi.mtbf, 500, 100)),
            ("Disponibilidad", f"{kpi.disponibilidad:.1f}", "%",
             self._tipo_card(kpi.disponibilidad, 95, 80)),
            ("% Preventivo", f"{kpi.pct_preventivo:.1f}", "%",
             self._tipo_card(kpi.pct_preventivo, 70, 50)),
            ("% Correctivo", f"{kpi.pct_correctivo:.1f}", "%",
             self._tipo_card(kpi.pct_correctivo, 20, 40, inverso=True)),
            ("Cumplimiento Plan", f"{kpi.cumplimiento_plan:.1f}", "%",
             self._tipo_card(kpi.cumplimiento_plan, 90, 70)),
            ("Total Fallas", str(kpi.total_fallas), "",
             "warning" if kpi.total_fallas > 0 else "success"),
            ("OTs Vencidas", str(kpi.ots_vencidas), "",
             "danger" if kpi.ots_vencidas > 0 else "success"),
            ("Tiempo Muerto Total", f"{kpi.tiempo_muerto_total:.1f}", "horas",
             self._tipo_card(kpi.tiempo_muerto_total, 0, 50, inverso=True)),
            ("OTs Cerradas", str(kpi.ots_cerradas), "", "success"),
            ("OTs En Proceso", str(kpi.ots_proceso), "", "info"),
            ("Costo Período",
             f"{kpi.costo_periodo:,.0f}", "", "info"),
        ]

        cols = 4
        for idx, (tit, val, uni, tipo) in enumerate(datos_tarjetas):
            card = self._crear_card(tit, val, uni, colores[tipo], tipo)
            self._grid_kpis.addWidget(card, idx // cols, idx % cols)

    def _crear_card(self, titulo, valor, unidad, color, tipo) -> QFrame:
        card = QFrame()
        card.setObjectName(f"card_kpi_{tipo}")
        card.setMinimumSize(180, 110)
        card.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)

        lbl_t = QLabel(titulo.upper())
        lbl_t.setStyleSheet(
            f"font-size: 10px; color: {COLOR_TEXT_SECONDARY}; "
            f"letter-spacing: 1px; font-weight: 600; border: none;")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet(
            f"font-size: 30px; font-weight: 700; color: {color}; "
            f"border: none;")
        lbl_u = QLabel(unidad)
        lbl_u.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; border: none;")

        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        if unidad:
            lay.addWidget(lbl_u)
        return card

    def _renderizar_graficos(self):
        """Limpia y renderiza gráficos de tendencia."""
        # Limpiar gráficos anteriores
        while self._lay_graficos.count():
            item = self._lay_graficos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

            kpi = self._kpi

            # Gráfico 1: Preventivo vs Correctivo
            fig1, ax1 = plt.subplots(figsize=(4, 3), facecolor="#1e2d3d")
            ax1.set_facecolor("#1e2d3d")
            cats = ["Preventivo", "Correctivo", "Otro"]
            total = kpi.ots_cerradas or 1
            vals = [
                kpi.pct_preventivo / 100 * total,
                kpi.pct_correctivo / 100 * total,
                max(0, total - (kpi.pct_preventivo + kpi.pct_correctivo)
                    / 100 * total)
            ]
            vals = [max(0, v) for v in vals]
            if sum(vals) > 0:
                ax1.pie(vals, labels=cats, autopct="%1.0f%%",
                        colors=["#4CAF50", "#F44336", "#2196F3"],
                        textprops={"color": "white", "fontsize": 9})
            ax1.set_title("Dist. OTs Cerradas", color="white",
                          fontsize=10)
            fig1.tight_layout(pad=0.3)
            c1 = FigureCanvasQTAgg(fig1)
            c1.setMaximumSize(360, 260)
            self._lay_graficos.addWidget(c1)
            plt.close(fig1)

            # Gráfico 2: Barras de KPIs clave
            fig2, ax2 = plt.subplots(figsize=(4, 3), facecolor="#1e2d3d")
            ax2.set_facecolor("#1e2d3d")
            kpis_bar = ["Disponib.", "% Prev.", "Cumpl."]
            vals_bar = [kpi.disponibilidad,
                        kpi.pct_preventivo,
                        kpi.cumplimiento_plan]
            colores_bar = [
                "#4CAF50" if v >= 90 else "#FF9800" if v >= 70 else "#F44336"
                for v in vals_bar
            ]
            bars = ax2.bar(kpis_bar, vals_bar, color=colores_bar)
            ax2.set_ylim(0, 110)
            ax2.axhline(90, color="#4CAF50", linestyle="--",
                        linewidth=0.8, alpha=0.7)
            ax2.axhline(70, color="#FF9800", linestyle="--",
                        linewidth=0.8, alpha=0.7)
            ax2.tick_params(colors="white", labelsize=9)
            ax2.set_ylabel("%", color="white", fontsize=9)
            ax2.set_title("KPIs clave (%)", color="white", fontsize=10)
            for s in ["top", "right"]:
                ax2.spines[s].set_visible(False)
            for s in ["bottom", "left"]:
                ax2.spines[s].set_color("#344d63")
            for bar in bars:
                h = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2, h + 1,
                         f"{h:.0f}%", ha="center", color="white",
                         fontsize=8)
            fig2.tight_layout(pad=0.3)
            c2 = FigureCanvasQTAgg(fig2)
            c2.setMaximumSize(360, 260)
            self._lay_graficos.addWidget(c2)
            plt.close(fig2)

            self._lay_graficos.addStretch()

        except ImportError:
            lbl = QLabel("Instale matplotlib para ver gráficos: pip install matplotlib")
            lbl.setStyleSheet(
                f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            self._lay_graficos.addWidget(lbl)

    def _cargar_tabla_equipos(self):
        fd = self.fecha_desde.date()
        fh = self.fecha_hasta.date()
        desde = datetime(fd.year(), fd.month(), fd.day())
        hasta = datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59)

        equipos = KPIService.kpis_por_equipo(desde, hasta)
        self.tabla_equipos.setRowCount(0)
        colores = {
            "Crítica": COLOR_DANGER, "Alta": COLOR_WARNING,
            "Media": COLOR_ACCENT_BLUE, "Baja": COLOR_SUCCESS,
        }
        for eq in equipos:
            r = self.tabla_equipos.rowCount()
            self.tabla_equipos.insertRow(r)
            for c, v in enumerate([
                eq["codigo"], eq["nombre"], eq["area"] or "-",
                eq["criticidad"],
                f"{eq['mttr']:.2f}", f"{eq['mtbf']:.2f}",
                f"{eq['disponibilidad']:.1f}",
                str(eq["fallas"]),
                f"{eq['costo']:,.2f}",
            ]):
                item = QTableWidgetItem(v)
                if c == 3:  # Criticidad
                    item.setForeground(
                        QColor(colores.get(eq["criticidad"], "#FFFFFF")))
                    f = QFont()
                    f.setBold(True)
                    item.setFont(f)
                elif c == 6:  # Disponibilidad
                    disp = eq["disponibilidad"]
                    color = ("#4CAF50" if disp >= 95 else
                             "#FF9800" if disp >= 80 else "#F44336")
                    item.setForeground(QColor(color))
                self.tabla_equipos.setItem(r, c, item)

    def _cargar_top_fallas(self):
        if not self._kpi:
            return
        self.tabla_fallas.setRowCount(0)
        for t in self._kpi.top_equipos_fallas:
            r = self.tabla_fallas.rowCount()
            self.tabla_fallas.insertRow(r)
            for c, v in enumerate([
                t["nombre"], "-",
                str(t["fallas"]),
                f"{t['tiempo_muerto']:.1f}",
                f"{t['costo']:,.2f}",
            ]):
                self.tabla_fallas.setItem(r, c, QTableWidgetItem(v))

    def _exportar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar KPIs", "kpis_mantenimiento.xlsx",
            "Excel (*.xlsx)")
        if not ruta or not self._kpi:
            return
        try:
            import pandas as pd
            kpi = self._kpi
            df = pd.DataFrame([{
                "Indicador": "MTTR (h)", "Valor": kpi.mttr},
                {"Indicador": "MTBF (h)", "Valor": kpi.mtbf},
                {"Indicador": "Disponibilidad %",
                 "Valor": kpi.disponibilidad},
                {"Indicador": "% Preventivo", "Valor": kpi.pct_preventivo},
                {"Indicador": "% Correctivo", "Valor": kpi.pct_correctivo},
                {"Indicador": "Cumplimiento Plan %",
                 "Valor": kpi.cumplimiento_plan},
                {"Indicador": "Total Fallas", "Valor": kpi.total_fallas},
                {"Indicador": "OTs Vencidas", "Valor": kpi.ots_vencidas},
                {"Indicador": "OTs Cerradas", "Valor": kpi.ots_cerradas},
                {"Indicador": "Costo Período",
                 "Valor": kpi.costo_periodo},
            ])
            df.to_excel(ruta, index=False)
            QMessageBox.information(self, "Exportado", ruta)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", str(e))

"""
Dashboard PMP - Vista principal con KPIs, alertas y OTs recientes.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QSizePolicy,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from app.services.kpi_service import KPIService, KPIResultado
from app.services.material_service import MaterialService
from app.services.ot_service import OTService
from app.views.shared.styles import (
    COLOR_BG_PANEL, COLOR_ACCENT_BLUE, COLOR_SUCCESS,
    COLOR_WARNING, COLOR_DANGER, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_BORDER
)
from datetime import datetime, timedelta


class DashboardWidget(QWidget):
    ir_a_ots     = Signal()
    ir_a_planes  = Signal()
    ir_a_equipos = Signal()
    ir_a_costos  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._kpi = None
        self._construir_ui()
        QTimer.singleShot(200, self.actualizar)

    def _construir_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenedor = QWidget()
        scroll.setWidget(contenedor)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.addWidget(scroll)
        lay = QVBoxLayout(contenedor)
        lay.setContentsMargins(24,16,24,24)
        lay.setSpacing(16)

        # Encabezado
        enc = QHBoxLayout()
        lbl = QLabel("Dashboard PMP")
        lbl.setStyleSheet(f"font-size: 22px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        self.lbl_per = QLabel()
        self.lbl_per.setStyleSheet(f"font-size:12px; color:{COLOR_TEXT_SECONDARY};")
        self._upd_periodo()
        btn = QPushButton("Actualizar")
        btn.setFixedHeight(34)
        btn.setStyleSheet(f"background-color:{COLOR_ACCENT_BLUE}; color:white; font-weight:600; border-radius:4px; border:none; padding:0 16px;")
        btn.clicked.connect(self.actualizar)
        enc.addWidget(lbl); enc.addWidget(self.lbl_per); enc.addStretch(); enc.addWidget(btn)
        lay.addLayout(enc)

        # Navegacion rapida
        nav = QHBoxLayout()
        for txt, cb, col in [
            ("Ordenes de Trabajo", self.ir_a_ots.emit,    COLOR_ACCENT_BLUE),
            ("Planes",             self.ir_a_planes.emit, "#7B1FA2"),
            ("Equipos",            self.ir_a_equipos.emit,"#1565C0"),
            ("Costos",             self.ir_a_costos.emit, "#2E7D32"),
        ]:
            b = QPushButton(txt)
            b.setFixedHeight(36)
            b.setStyleSheet(f"background-color:{col}; color:white; font-weight:600; border-radius:6px; border:none; padding:0 16px;")
            b.clicked.connect(cb); nav.addWidget(b)
        nav.addStretch()
        lay.addLayout(nav)

        # Grid KPIs
        self._grid = QGridLayout()
        self._grid.setSpacing(12)
        lay.addLayout(self._grid)

        # Tablas OTs + Alertas
        fi = QHBoxLayout(); fi.setSpacing(16)
        fp = self._panel("Ordenes de Trabajo Recientes")
        self.t_ots = self._mk_tabla(["Numero","Equipo","Tipo","Estado","Fecha"],[110,160,100,90,90])
        fp.layout().addWidget(self.t_ots)
        fa = self._panel("Alertas")
        self.t_alt = self._mk_tabla(["Tipo","Descripcion","Nivel"],[70,230,80])
        fa.layout().addWidget(self.t_alt)
        fi.addWidget(fp, 3); fi.addWidget(fa, 2)
        lay.addLayout(fi)

        # Graficos
        self._fg = QFrame()
        self._fg.setMinimumHeight(240)
        self._fg.setStyleSheet(f"background-color:{COLOR_BG_PANEL}; border-radius:8px; border:1px solid {COLOR_BORDER};")
        self._lg = QHBoxLayout(self._fg)
        self._lg.setContentsMargins(12,12,12,12)
        lw = QLabel("Los graficos apareceran al actualizar...")
        lw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lw.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; border:none;")
        self._lg.addWidget(lw)
        lay.addWidget(self._fg)

    def _panel(self, titulo):
        f = QFrame()
        f.setStyleSheet(f"background-color:{COLOR_BG_PANEL}; border-radius:8px; border:1px solid {COLOR_BORDER};")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14,10,14,10); lay.setSpacing(8)
        lbl = QLabel(titulo)
        lbl.setStyleSheet(f"font-weight:700; font-size:13px; color:{COLOR_TEXT_PRIMARY}; border:none;")
        lay.addWidget(lbl)
        return f

    def _mk_tabla(self, headers, widths):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setStretchLastSection(True)
        t.setMaximumHeight(200)
        for i, w in enumerate(widths[:-1]):
            t.setColumnWidth(i, w)
        return t

    def _card(self, titulo, valor, unidad, color):
        card = QFrame()
        card.setMinimumSize(155,95)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet(f"background-color:{COLOR_BG_PANEL}; border-radius:8px; border:1px solid {COLOR_BORDER}; border-left:4px solid {color};")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14,10,14,10); lay.setSpacing(2)
        lt = QLabel(titulo.upper())
        lt.setStyleSheet(f"font-size:10px; color:{COLOR_TEXT_SECONDARY}; letter-spacing:1px; font-weight:600; border:none;")
        lt.setWordWrap(True)
        lv = QLabel(valor)
        lv.setStyleSheet(f"font-size:26px; font-weight:700; color:{color}; border:none;")
        lay.addWidget(lt); lay.addWidget(lv)
        if unidad:
            lu = QLabel(unidad)
            lu.setStyleSheet(f"font-size:11px; color:{COLOR_TEXT_SECONDARY}; border:none;")
            lay.addWidget(lu)
        return card

    def _upd_periodo(self):
        hasta = datetime.now()
        desde = hasta - timedelta(days=90)
        self.lbl_per.setText(f"  Periodo: {desde.strftime('%d/%m/%Y')} - {hasta.strftime('%d/%m/%Y')}  (90 dias)")

    def actualizar(self):
        try:
            self._kpi = KPIService.calcular_kpis()
        except Exception as e:
            print(f"[Dashboard] KPI error: {e}")
            self._kpi = KPIResultado()
        self._render_kpis()
        self._render_ots()
        self._render_alertas()
        self._render_graficos()

    def _color(self, v, ok, warn, inv=False):
        if inv:
            return COLOR_SUCCESS if v<=ok else COLOR_WARNING if v<=warn else COLOR_DANGER
        return COLOR_SUCCESS if v>=ok else COLOR_WARNING if v>=warn else COLOR_DANGER

    def _render_kpis(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        k = self._kpi
        tarjetas = [
            ("MTTR",              f"{k.mttr:.1f}",              "horas", self._color(k.mttr,4,8,True)),
            ("MTBF",              f"{k.mtbf:.1f}",              "horas", self._color(k.mtbf,500,100)),
            ("Disponibilidad",    f"{k.disponibilidad:.1f}",    "%",     self._color(k.disponibilidad,95,80)),
            ("Prev./Corr.",       f"{k.pct_preventivo:.0f}% / {k.pct_correctivo:.0f}%",
                                                                 "",     self._color(k.pct_preventivo,70,50)),
            ("Cumplimiento Plan", f"{k.cumplimiento_plan:.1f}", "%",     self._color(k.cumplimiento_plan,90,70)),
            ("OTs Abiertas",      str(k.ots_abiertas),          "",     COLOR_ACCENT_BLUE),
            ("OTs En Proceso",    str(k.ots_proceso),           "",     COLOR_ACCENT_BLUE),
            ("OTs Vencidas",      str(k.ots_vencidas),          "",     COLOR_DANGER if k.ots_vencidas>0 else COLOR_SUCCESS),
            ("OTs Cerradas",      str(k.ots_cerradas),          "",     COLOR_SUCCESS),
            ("Total Fallas",      str(k.total_fallas),          "",     COLOR_WARNING if k.total_fallas>0 else COLOR_SUCCESS),
            ("Tiempo Muerto",     f"{k.tiempo_muerto_total:.1f}","horas",COLOR_WARNING),
            ("Costo Periodo",     f"{k.costo_periodo:,.0f}",    "",     COLOR_ACCENT_BLUE),
        ]
        for idx, (t,v,u,c) in enumerate(tarjetas):
            self._grid.addWidget(self._card(t,v,u,c), idx//6, idx%6)

    def _render_ots(self):
        try:
            ots = OTService.listar_ots()[:10]
        except Exception:
            ots = []
        self.t_ots.setRowCount(0)
        ce = {"Cerrada":"#4CAF50","En proceso":"#2196F3","Liberada":"#2196F3",
              "Anulada":"#9E9E9E","Programada":"#FF9800","Vencida":"#F44336"}
        for ot in ots:
            r = self.t_ots.rowCount(); self.t_ots.insertRow(r)
            try: eq = ot.equipo.nombre if ot.equipo else "-"
            except: eq = "-"
            fecha = ot.fecha_programada.strftime("%d/%m/%Y") if ot.fecha_programada else "-"
            for c, v in enumerate([ot.numero, eq, ot.tipo_ot, ot.estado, fecha]):
                item = QTableWidgetItem(str(v))
                if c == 3:
                    item.setForeground(QColor(ce.get(ot.estado,"#FFF")))
                    f = QFont(); f.setBold(True); item.setFont(f)
                self.t_ots.setItem(r, c, item)

    def _render_alertas(self):
        self.t_alt.setRowCount(0)
        alertas = []
        try:
            for m in MaterialService.obtener_alertas_stock()[:5]:
                niv = "CRITICO" if m.alerta_stock=="critico" else "STOCK BAJO"
                alertas.append(("Stock", f"{m.descripcion} (stock:{m.stock_actual:.0f})", niv))
        except: pass
        if self._kpi and self._kpi.ots_vencidas > 0:
            alertas.append(("OTs", f"{self._kpi.ots_vencidas} OT(s) vencidas", "CRITICO"))
        try:
            prox = OTService.listar_ots({"estado":"Liberada",
                "fecha_desde": datetime.now(),
                "fecha_hasta": datetime.now()+timedelta(days=7)})
            if prox:
                alertas.append(("OTs", f"{len(prox)} OT(s) proximos 7 dias", "PROXIMO"))
        except: pass
        cn = {"CRITICO":"#F44336","STOCK BAJO":"#FF9800","PROXIMO":"#FF9800"}
        if not alertas:
            self.t_alt.insertRow(0)
            item = QTableWidgetItem("Sin alertas activas")
            item.setForeground(QColor(COLOR_SUCCESS))
            self.t_alt.setItem(0,1,item)
            return
        for tipo, desc, niv in alertas:
            r = self.t_alt.rowCount(); self.t_alt.insertRow(r)
            for c, v in enumerate([tipo, desc, niv]):
                item = QTableWidgetItem(v)
                if c == 2:
                    item.setForeground(QColor(cn.get(niv,"#FFF")))
                    f = QFont(); f.setBold(True); item.setFont(f)
                self.t_alt.setItem(r, c, item)

    def _render_graficos(self):
        while self._lg.count():
            item = self._lg.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            k = self._kpi or KPIResultado()

            # Torta OTs
            fig1, ax1 = plt.subplots(figsize=(3.5,2.8), facecolor="#2a3f55")
            ax1.set_facecolor("#2a3f55")
            total = k.ots_cerradas or 1
            vals = [max(0, k.pct_preventivo/100*total),
                    max(0, k.pct_correctivo/100*total),
                    max(0, total-(k.pct_preventivo+k.pct_correctivo)/100*total)]
            if sum(vals)>0:
                ax1.pie(vals, labels=["Preventivo","Correctivo","Otro"],
                        autopct="%1.0f%%", colors=["#4CAF50","#F44336","#2196F3"],
                        textprops={"color":"white","fontsize":8})
            else:
                ax1.text(0.5,0.5,"Sin datos",ha="center",va="center",color="white",transform=ax1.transAxes)
            ax1.set_title("Dist. OTs Cerradas",color="white",fontsize=9,pad=6)
            fig1.tight_layout(pad=0.3)
            c1 = FigureCanvasQTAgg(fig1); c1.setMaximumSize(380,240)
            self._lg.addWidget(c1); plt.close(fig1)

            # Barras KPIs
            fig2, ax2 = plt.subplots(figsize=(3.5,2.8), facecolor="#2a3f55")
            ax2.set_facecolor("#2a3f55")
            nms = ["Disponib.","% Prev.","Cumpl."]
            vs  = [k.disponibilidad, k.pct_preventivo, k.cumplimiento_plan]
            cs  = ["#4CAF50" if v>=90 else "#FF9800" if v>=70 else "#F44336" for v in vs]
            ax2.bar(nms, vs, color=cs, width=0.5)
            ax2.set_ylim(0,120)
            ax2.axhline(90,color="#4CAF50",linestyle="--",linewidth=0.8,alpha=0.6)
            ax2.tick_params(colors="white",labelsize=8)
            ax2.set_ylabel("%",color="white",fontsize=8)
            ax2.set_title("KPIs Clave (%)",color="white",fontsize=9,pad=6)
            for s in ["top","right"]: ax2.spines[s].set_visible(False)
            for s in ["bottom","left"]: ax2.spines[s].set_color("#344d63")
            for i,v in enumerate(vs): ax2.text(i,v+2,f"{v:.0f}%",ha="center",color="white",fontsize=8)
            fig2.tight_layout(pad=0.3)
            c2 = FigureCanvasQTAgg(fig2); c2.setMaximumSize(380,240)
            self._lg.addWidget(c2); plt.close(fig2)
            self._lg.addStretch()

        except ImportError:
            lbl = QLabel("Instale matplotlib:  py -3.11 -m pip install matplotlib")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; border:none;")
            self._lg.addWidget(lbl)
        except Exception as e:
            lbl = QLabel(f"Error en graficos: {e}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{COLOR_WARNING}; border:none;")
            self._lg.addWidget(lbl)

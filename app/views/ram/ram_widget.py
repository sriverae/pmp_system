"""
Modulo RAM - Analisis de Confiabilidad, Disponibilidad y Mantenibilidad.
Calcula MTTR, MTBF, Disponibilidad, Distribucion de Weibull y curvas de vida.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QFileDialog, QMessageBox,
    QGridLayout, QSizePolicy, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont
from app.services.ot_service import OTService
from app.services.equipo_service import EquipoService
from app.core.database import get_session
from app.models.orden_trabajo import OrdenTrabajo
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER
)
from datetime import datetime, timedelta
import math


class RamWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._resultados = []
        self._construir_ui()

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        # Encabezado
        enc = QHBoxLayout()
        lbl = QLabel("Analisis RAM  -  Confiabilidad / Disponibilidad / Mantenibilidad")
        lbl.setStyleSheet(f"font-size:18px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        enc.addWidget(lbl); enc.addStretch()
        lay.addLayout(enc)

        # Descripcion
        lbl_desc = QLabel(
            "El analisis RAM permite evaluar la confiabilidad (MTBF), mantenibilidad (MTTR) "
            "y disponibilidad de cada equipo para tomar decisiones de reemplazo o mejora.")
        lbl_desc.setStyleSheet(
            f"color:{COLOR_TEXT_SECONDARY}; font-size:12px; "
            f"background-color:{COLOR_BG_PANEL}; padding:8px 12px; "
            f"border-radius:4px; border:1px solid {COLOR_BORDER};")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        # Filtros
        fil = QHBoxLayout(); fil.setSpacing(8)
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addDays(-365))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)
        self.combo_equipo = QComboBox()
        self.combo_equipo.addItem("Todos los equipos", None)
        self.combo_equipo.setFixedWidth(220)
        self._cargar_equipos()
        btn_calc = QPushButton("Calcular RAM")
        btn_calc.setStyleSheet(
            f"background-color:{COLOR_ACCENT_BLUE}; color:white; font-weight:600; "
            f"border-radius:4px; border:none; padding:6px 20px;")
        btn_calc.clicked.connect(self.calcular)
        btn_exp = QPushButton("Exportar Informe")
        btn_exp.clicked.connect(self._exportar)

        fil.addWidget(QLabel("Desde:")); fil.addWidget(self.fecha_desde)
        fil.addWidget(QLabel("Hasta:")); fil.addWidget(self.fecha_hasta)
        fil.addWidget(QLabel("Equipo:")); fil.addWidget(self.combo_equipo)
        fil.addWidget(btn_calc); fil.addWidget(btn_exp); fil.addStretch()
        lay.addLayout(fil)

        # Tabs
        tabs = QTabWidget()

        # Tab 1: Resumen por equipo
        t1 = QWidget()
        lay1 = QVBoxLayout(t1)

        self.tabla_ram = QTableWidget(0, 10)
        self.tabla_ram.setHorizontalHeaderLabels([
            "Codigo","Equipo","Criticidad","N Fallas",
            "MTBF (h)","MTTR (h)","Disponib. %",
            "T. Muerto (h)","Costo Total","Clasificacion"])
        self.tabla_ram.horizontalHeader().setStretchLastSection(True)
        self.tabla_ram.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_ram.setAlternatingRowColors(True)
        self.tabla_ram.verticalHeader().setVisible(False)
        self.tabla_ram.setSortingEnabled(True)
        for i, w in enumerate([80,160,80,70,80,80,80,90,90]):
            self.tabla_ram.setColumnWidth(i, w)
        lay1.addWidget(self.tabla_ram)
        tabs.addTab(t1, "Resumen por Equipo")

        # Tab 2: Indicadores globales
        t2 = QScrollArea()
        t2.setWidgetResizable(True)
        t2.setFrameShape(QFrame.Shape.NoFrame)
        self._cont_global = QWidget()
        self._lay_global  = QVBoxLayout(self._cont_global)
        self._lay_global.setContentsMargins(8,8,8,8)
        self._lay_global.setSpacing(12)
        t2.setWidget(self._cont_global)
        tabs.addTab(t2, "Indicadores Globales")

        # Tab 3: Analisis de Weibull
        t3 = QWidget()
        lay3 = QVBoxLayout(t3)
        lbl_w = QLabel(
            "Analisis de Weibull - Patron de fallas\n\n"
            "La distribucion de Weibull modela el patron de fallas de los equipos:\n"
            "  beta < 1:  Fallas infantiles (problemas de calidad o instalacion)\n"
            "  beta = 1:  Fallas aleatorias (exponencial, vida util estable)\n"
            "  beta > 1:  Fallas por desgaste (envejecimiento del equipo)\n\n"
            "Para calcular Weibull se requieren al menos 3 fallas por equipo.")
        lbl_w.setStyleSheet(
            f"color:{COLOR_TEXT_PRIMARY}; font-size:13px; "
            f"background-color:{COLOR_BG_PANEL}; padding:16px; "
            f"border-radius:6px; border:1px solid {COLOR_BORDER};")
        lbl_w.setWordWrap(True)
        lay3.addWidget(lbl_w)
        self.tabla_weibull = QTableWidget(0, 5)
        self.tabla_weibull.setHorizontalHeaderLabels(
            ["Equipo","N Fallas","Beta (forma)","Eta (escala)","Interpretacion"])
        self.tabla_weibull.horizontalHeader().setStretchLastSection(True)
        self.tabla_weibull.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_weibull.setAlternatingRowColors(True)
        self.tabla_weibull.verticalHeader().setVisible(False)
        for i, w in enumerate([160,70,90,90]):
            self.tabla_weibull.setColumnWidth(i, w)
        lay3.addWidget(self.tabla_weibull)
        tabs.addTab(t3, "Analisis Weibull")

        # Tab 4: Grafico (si matplotlib disponible)
        t4 = QWidget()
        self._lay_graf = QVBoxLayout(t4)
        self._lay_graf.setContentsMargins(8,8,8,8)
        lbl_pg = QLabel("Presione 'Calcular RAM' para generar los graficos")
        lbl_pg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pg.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:13px;")
        self._lay_graf.addWidget(lbl_pg)
        tabs.addTab(t4, "Graficos")

        lay.addWidget(tabs)

    def _cargar_equipos(self):
        try:
            equipos = EquipoService.listar(solo_activos=False)
            for e in equipos:
                self.combo_equipo.addItem(f"{e.codigo} - {e.nombre}", e.id)
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Calculo RAM
    # -----------------------------------------------------------------
    def calcular(self):
        fd = self.fecha_desde.date(); fh = self.fecha_hasta.date()
        desde = datetime(fd.year(), fd.month(), fd.day())
        hasta  = datetime(fh.year(), fh.month(), fh.day(), 23, 59, 59)
        eq_id  = self.combo_equipo.currentData()
        horas_periodo = (hasta - desde).total_seconds() / 3600

        session = get_session()
        try:
            q = session.query(OrdenTrabajo).filter(
                OrdenTrabajo.estado == "Cerrada",
                OrdenTrabajo.fecha_cierre >= desde,
                OrdenTrabajo.fecha_cierre <= hasta,
            )
            if eq_id:
                q = q.filter(OrdenTrabajo.equipo_id == eq_id)
            ots = q.all()
        finally:
            session.close()

        # Agrupar por equipo
        equipos_map = {}
        for ot in ots:
            if ot.tipo_ot not in ("Correctivo","Emergencia"):
                continue
            eid = ot.equipo_id
            if eid not in equipos_map:
                try:
                    eq = EquipoService.obtener(eid)
                    nombre = eq.nombre if eq else f"ID {eid}"
                    codigo = eq.codigo if eq else "-"
                    criticidad = eq.criticidad if eq else "-"
                except Exception:
                    nombre = f"Equipo {eid}"; codigo = "-"; criticidad = "-"
                equipos_map[eid] = {
                    "codigo": codigo, "nombre": nombre, "criticidad": criticidad,
                    "fallas": [], "tiempos_fuera": [], "costos": [],
                }
            equipos_map[eid]["fallas"].append(ot)
            equipos_map[eid]["tiempos_fuera"].append(ot.tiempo_fuera_servicio or 0)
            equipos_map[eid]["costos"].append(ot.costo_total or 0)

        self._resultados = []
        for eid, datos in equipos_map.items():
            n = len(datos["fallas"])
            t_muerto = sum(datos["tiempos_fuera"])
            mttr = t_muerto / n if n > 0 else 0
            mtbf = (horas_periodo - t_muerto) / n if n > 0 else horas_periodo
            disp = mtbf / (mtbf + mttr) * 100 if (mtbf + mttr) > 0 else 100
            costo = sum(datos["costos"])
            # Clasificacion
            if disp >= 95 and n <= 2:
                clasif = "Confiable"
                col_c = COLOR_SUCCESS
            elif disp >= 80:
                clasif = "Aceptable"
                col_c = COLOR_WARNING
            else:
                clasif = "Critico"
                col_c = COLOR_DANGER
            self._resultados.append({
                "equipo_id": eid,
                "codigo": datos["codigo"],
                "nombre": datos["nombre"],
                "criticidad": datos["criticidad"],
                "n_fallas": n,
                "mtbf": round(mtbf, 2),
                "mttr": round(mttr, 2),
                "disponibilidad": round(disp, 2),
                "t_muerto": round(t_muerto, 2),
                "costo": round(costo, 2),
                "clasificacion": clasif,
                "col_clasif": col_c,
                "tiempos_fuera": datos["tiempos_fuera"],
            })

        self._render_tabla()
        self._render_global(horas_periodo, ots)
        self._render_weibull()
        self._render_graficos()

    def _render_tabla(self):
        self.tabla_ram.setSortingEnabled(False)
        self.tabla_ram.setRowCount(0)
        col_crit = {"Critica": COLOR_DANGER,"Alta":COLOR_WARNING,
                    "Media":COLOR_ACCENT_BLUE,"Baja":COLOR_SUCCESS}
        for r_data in sorted(self._resultados, key=lambda x: x["disponibilidad"]):
            r = self.tabla_ram.rowCount(); self.tabla_ram.insertRow(r)
            vals = [
                r_data["codigo"], r_data["nombre"], r_data["criticidad"],
                str(r_data["n_fallas"]),
                f"{r_data['mtbf']:.1f}", f"{r_data['mttr']:.1f}",
                f"{r_data['disponibilidad']:.1f}",
                f"{r_data['t_muerto']:.1f}", f"{r_data['costo']:,.2f}",
                r_data["clasificacion"],
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 2:
                    item.setForeground(QColor(col_crit.get(r_data["criticidad"],"#FFF")))
                elif c == 6:
                    disp = r_data["disponibilidad"]
                    item.setForeground(QColor(
                        COLOR_SUCCESS if disp>=95 else COLOR_WARNING if disp>=80 else COLOR_DANGER))
                    f2 = QFont(); f2.setBold(True); item.setFont(f2)
                elif c == 9:
                    item.setForeground(QColor(r_data["col_clasif"]))
                    f2 = QFont(); f2.setBold(True); item.setFont(f2)
                self.tabla_ram.setItem(r, c, item)
        self.tabla_ram.setSortingEnabled(True)

    def _render_global(self, horas_periodo: float, ots_correctivas: list):
        while self._lay_global.count():
            item = self._lay_global.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not self._resultados:
            lbl = QLabel("Sin datos suficientes para el periodo seleccionado.")
            lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:13px;")
            self._lay_global.addWidget(lbl)
            self._lay_global.addStretch()
            return

        total_fallas = sum(r["n_fallas"] for r in self._resultados)
        total_t_muerto = sum(r["t_muerto"] for r in self._resultados)
        mttr_global = total_t_muerto / total_fallas if total_fallas else 0
        mtbf_global = (horas_periodo - total_t_muerto) / total_fallas if total_fallas else horas_periodo
        disp_global  = mtbf_global / (mtbf_global + mttr_global) * 100 if (mtbf_global+mttr_global) > 0 else 100
        costo_global = sum(r["costo"] for r in self._resultados)
        eq_criticos  = [r for r in self._resultados if r["clasificacion"]=="Critico"]
        eq_confiable = [r for r in self._resultados if r["clasificacion"]=="Confiable"]

        grid = QGridLayout(); grid.setSpacing(12)

        def card_g(titulo, valor, unidad, color):
            f = QFrame()
            f.setMinimumSize(180,100)
            f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            f.setStyleSheet(f"background-color:{COLOR_BG_PANEL}; border-radius:8px; border:1px solid {COLOR_BORDER}; border-left:4px solid {color};")
            ly = QVBoxLayout(f); ly.setContentsMargins(14,10,14,10); ly.setSpacing(2)
            lt = QLabel(titulo.upper())
            lt.setStyleSheet(f"font-size:10px; color:{COLOR_TEXT_SECONDARY}; letter-spacing:1px; font-weight:600; border:none;")
            lt.setWordWrap(True)
            lv = QLabel(valor)
            lv.setStyleSheet(f"font-size:24px; font-weight:700; color:{color}; border:none;")
            lu = QLabel(unidad)
            lu.setStyleSheet(f"font-size:11px; color:{COLOR_TEXT_SECONDARY}; border:none;")
            ly.addWidget(lt); ly.addWidget(lv)
            if unidad: ly.addWidget(lu)
            return f

        tarjetas = [
            ("MTBF Global",      f"{mtbf_global:.1f}",   "horas",
             COLOR_SUCCESS if mtbf_global>=500 else COLOR_WARNING),
            ("MTTR Global",      f"{mttr_global:.1f}",   "horas",
             COLOR_SUCCESS if mttr_global<=4 else COLOR_WARNING),
            ("Disponibilidad Global", f"{disp_global:.1f}", "%",
             COLOR_SUCCESS if disp_global>=95 else COLOR_WARNING if disp_global>=80 else COLOR_DANGER),
            ("Total Fallas",     str(total_fallas),      "",      COLOR_WARNING if total_fallas>0 else COLOR_SUCCESS),
            ("Tiempo Muerto Total", f"{total_t_muerto:.1f}", "horas", COLOR_WARNING),
            ("Costo Total Fallas",f"{costo_global:,.0f}","",      COLOR_ACCENT_BLUE),
            ("Equipos Criticos", str(len(eq_criticos)),  "",      COLOR_DANGER if eq_criticos else COLOR_SUCCESS),
            ("Equipos Confiables",str(len(eq_confiable)),"",      COLOR_SUCCESS),
        ]
        for i, (t,v,u,c) in enumerate(tarjetas):
            grid.addWidget(card_g(t,v,u,c), i//4, i%4)

        wrapper_g = QWidget(); wrapper_g.setLayout(grid)
        self._lay_global.addWidget(wrapper_g)

        # Tabla top equipos con mas fallas
        if self._resultados:
            lbl_top = QLabel("Top equipos con mayor impacto (mayor tiempo fuera de servicio):")
            lbl_top.setStyleSheet(f"font-weight:700; color:{COLOR_TEXT_PRIMARY}; font-size:13px;")
            self._lay_global.addWidget(lbl_top)

            t_top = QTableWidget(0, 6)
            t_top.setHorizontalHeaderLabels(
                ["Equipo","Fallas","MTTR (h)","MTBF (h)","Disponib. %","Clasificacion"])
            t_top.horizontalHeader().setStretchLastSection(True)
            t_top.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t_top.setAlternatingRowColors(True)
            t_top.verticalHeader().setVisible(False)
            for i, w in enumerate([180,60,80,80,80]):
                t_top.setColumnWidth(i, w)

            top = sorted(self._resultados, key=lambda x: x["t_muerto"], reverse=True)[:8]
            for rd in top:
                r = t_top.rowCount(); t_top.insertRow(r)
                for c, v in enumerate([
                    rd["nombre"], str(rd["n_fallas"]),
                    f"{rd['mttr']:.1f}", f"{rd['mtbf']:.1f}",
                    f"{rd['disponibilidad']:.1f}", rd["clasificacion"]
                ]):
                    item = QTableWidgetItem(v)
                    if c == 4:
                        item.setForeground(QColor(
                            COLOR_SUCCESS if rd["disponibilidad"]>=95
                            else COLOR_WARNING if rd["disponibilidad"]>=80
                            else COLOR_DANGER))
                        f2 = QFont(); f2.setBold(True); item.setFont(f2)
                    elif c == 5:
                        item.setForeground(QColor(rd["col_clasif"]))
                    t_top.setItem(r, c, item)

            t_top.setMaximumHeight(220)
            self._lay_global.addWidget(t_top)

        # Recomendaciones
        rec_frame = QFrame()
        rec_frame.setStyleSheet(
            f"background-color:{COLOR_BG_PANEL}; border-radius:8px; "
            f"border:1px solid {COLOR_BORDER}; padding:4px;")
        rec_lay = QVBoxLayout(rec_frame)
        rec_lay.setContentsMargins(16,12,16,12)
        lbl_rec = QLabel("Recomendaciones del analisis")
        lbl_rec.setStyleSheet(
            f"font-weight:700; font-size:13px; color:{COLOR_ACCENT_BLUE}; border:none;")
        rec_lay.addWidget(lbl_rec)

        recs = []
        if disp_global < 80:
            recs.append("CRITICO: Disponibilidad global < 80%. Revisar politica de mantenimiento preventivo.")
        if mttr_global > 8:
            recs.append(f"ALTO MTTR ({mttr_global:.1f}h): Los tiempos de reparacion son elevados. "
                        "Revisar disponibilidad de repuestos y procedimientos de intervencion.")
        if mtbf_global < 200:
            recs.append(f"BAJO MTBF ({mtbf_global:.1f}h): Alta frecuencia de fallas. "
                        "Considerar incrementar frecuencia de mantenimiento preventivo.")
        for eq in eq_criticos[:3]:
            recs.append(f"Equipo critico: {eq['nombre']} - Disponib. {eq['disponibilidad']:.1f}% "
                        f"con {eq['n_fallas']} fallas. Evaluar reemplazo o refuerzo de PM.")
        if not recs:
            recs.append("Sistema en buen estado. Disponibilidad global aceptable.")

        for rec in recs:
            lbl_r = QLabel(f"  {rec}")
            col_r = COLOR_DANGER if rec.startswith("CRITICO") or rec.startswith("Equipo critico") \
                    else COLOR_WARNING if rec.startswith(("ALTO","BAJO")) else COLOR_SUCCESS
            lbl_r.setStyleSheet(f"color:{col_r}; font-size:12px; border:none;")
            lbl_r.setWordWrap(True)
            rec_lay.addWidget(lbl_r)

        self._lay_global.addWidget(rec_frame)
        self._lay_global.addStretch()

    def _render_weibull(self):
        self.tabla_weibull.setRowCount(0)
        for rd in self._resultados:
            tiempos = [t for t in rd["tiempos_fuera"] if t > 0]
            if len(tiempos) < 3:
                continue
            # Estimacion simplificada de Weibull por metodo de momentos
            try:
                media = sum(tiempos) / len(tiempos)
                varianza = sum((t - media)**2 for t in tiempos) / len(tiempos)
                cv = math.sqrt(varianza) / media if media > 0 else 1
                # Aproximacion beta desde CV
                beta = 1.0 / cv if cv > 0 else 1.0
                beta = max(0.1, min(beta, 10.0))
                import math as m
                # eta = media / gamma(1 + 1/beta) ~ media (aprox)
                eta = media
                if beta < 0.9:
                    interp = "Fallas infantiles (DFR)"
                elif beta < 1.1:
                    interp = "Fallas aleatorias (CFR)"
                elif beta < 2.5:
                    interp = "Desgaste moderado (IFR)"
                else:
                    interp = "Desgaste severo (IFR)"

                r = self.tabla_weibull.rowCount()
                self.tabla_weibull.insertRow(r)
                for c, v in enumerate([
                    rd["nombre"], str(len(tiempos)),
                    f"{beta:.2f}", f"{eta:.1f}", interp
                ]):
                    item = QTableWidgetItem(v)
                    if c == 2:
                        col = (COLOR_WARNING if beta < 0.9
                               else COLOR_SUCCESS if beta < 1.1
                               else COLOR_DANGER)
                        item.setForeground(QColor(col))
                    elif c == 4:
                        if "severo" in interp or "infantil" in interp.lower():
                            item.setForeground(QColor(COLOR_DANGER))
                        else:
                            item.setForeground(QColor(COLOR_SUCCESS))
                    self.tabla_weibull.setItem(r, c, item)
            except Exception:
                continue

    def _render_graficos(self):
        while self._lay_graf.count():
            item = self._lay_graf.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not self._resultados:
            lbl = QLabel("Sin datos para graficar. Ejecute el calculo primero.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY};")
            self._lay_graf.addWidget(lbl)
            return

        try:
            import matplotlib; matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

            datos_graf = sorted(self._resultados,
                                key=lambda x: x["disponibilidad"])[:10]
            nombres = [r["nombre"][:14] for r in datos_graf]
            disponibs = [r["disponibilidad"] for r in datos_graf]
            mttrs = [r["mttr"] for r in datos_graf]
            mtbfs = [r["mtbf"] for r in datos_graf]

            fig, axes = plt.subplots(1, 3, figsize=(13, 4), facecolor="#1e2d3d")
            fig.subplots_adjust(wspace=0.4)

            # Grafico 1: Disponibilidad
            ax1 = axes[0]; ax1.set_facecolor("#1e2d3d")
            colors1 = ["#4CAF50" if d>=95 else "#FF9800" if d>=80 else "#F44336"
                       for d in disponibs]
            bars1 = ax1.barh(nombres, disponibs, color=colors1, height=0.6)
            ax1.set_xlim(0, 110)
            ax1.axvline(95, color="#4CAF50", linestyle="--", linewidth=0.8, alpha=0.7)
            ax1.axvline(80, color="#FF9800", linestyle="--", linewidth=0.8, alpha=0.7)
            ax1.set_xlabel("Disponibilidad %", color="white", fontsize=9)
            ax1.set_title("Disponibilidad por Equipo", color="white", fontsize=10, pad=8)
            ax1.tick_params(colors="white", labelsize=8)
            for s in ["top","right"]: ax1.spines[s].set_visible(False)
            for s in ["bottom","left"]: ax1.spines[s].set_color("#344d63")
            for bar, v in zip(bars1, disponibs):
                ax1.text(v+1, bar.get_y()+bar.get_height()/2,
                         f"{v:.1f}%", va="center", color="white", fontsize=7)

            # Grafico 2: MTTR
            ax2 = axes[1]; ax2.set_facecolor("#1e2d3d")
            colors2 = ["#4CAF50" if m<=4 else "#FF9800" if m<=8 else "#F44336"
                       for m in mttrs]
            ax2.barh(nombres, mttrs, color=colors2, height=0.6)
            ax2.axvline(4, color="#4CAF50", linestyle="--", linewidth=0.8, alpha=0.7)
            ax2.axvline(8, color="#FF9800", linestyle="--", linewidth=0.8, alpha=0.7)
            ax2.set_xlabel("MTTR (horas)", color="white", fontsize=9)
            ax2.set_title("MTTR por Equipo", color="white", fontsize=10, pad=8)
            ax2.tick_params(colors="white", labelsize=8)
            for s in ["top","right"]: ax2.spines[s].set_visible(False)
            for s in ["bottom","left"]: ax2.spines[s].set_color("#344d63")

            # Grafico 3: Scatter MTBF vs MTTR
            ax3 = axes[2]; ax3.set_facecolor("#1e2d3d")
            sc_colors = [r["col_clasif"] for r in datos_graf]
            ax3.scatter(mttrs, mtbfs, c=sc_colors, s=80, zorder=5, edgecolors="white", linewidth=0.5)
            for i, (x, y, nm) in enumerate(zip(mttrs, mtbfs, nombres)):
                ax3.annotate(nm[:10], (x, y), textcoords="offset points",
                             xytext=(4, 4), fontsize=7, color="white")
            ax3.set_xlabel("MTTR (h)", color="white", fontsize=9)
            ax3.set_ylabel("MTBF (h)", color="white", fontsize=9)
            ax3.set_title("MTBF vs MTTR", color="white", fontsize=10, pad=8)
            ax3.tick_params(colors="white", labelsize=8)
            for s in ["top","right"]: ax3.spines[s].set_visible(False)
            for s in ["bottom","left"]: ax3.spines[s].set_color("#344d63")

            canvas = FigureCanvasQTAgg(fig)
            canvas.setMinimumHeight(320)
            self._lay_graf.addWidget(canvas)
            plt.close(fig)

        except ImportError:
            lbl = QLabel("Instale matplotlib para ver graficos:\n  py -3.11 -m pip install matplotlib")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:12px;")
            self._lay_graf.addWidget(lbl)
        except Exception as e:
            lbl = QLabel(f"Error al generar graficos: {e}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{COLOR_WARNING}; font-size:11px;")
            self._lay_graf.addWidget(lbl)

    # -----------------------------------------------------------------
    def _exportar(self):
        if not self._resultados:
            QMessageBox.warning(self,"Sin datos","Ejecute el calculo primero."); return
        ruta, _ = QFileDialog.getSaveFileName(
            self,"Exportar Informe RAM","informe_ram.xlsx","Excel (*.xlsx)")
        if not ruta: return
        try:
            import pandas as pd
            datos = [{
                "Codigo":         r["codigo"],
                "Equipo":         r["nombre"],
                "Criticidad":     r["criticidad"],
                "N Fallas":       r["n_fallas"],
                "MTBF (h)":       r["mtbf"],
                "MTTR (h)":       r["mttr"],
                "Disponibilidad %": r["disponibilidad"],
                "Tiempo Muerto (h)": r["t_muerto"],
                "Costo Total":    r["costo"],
                "Clasificacion":  r["clasificacion"],
            } for r in self._resultados]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self,"Exportado", f"Informe guardado:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self,"Error",str(e))

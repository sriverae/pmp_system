"""
Modulo Calendario - Vista mensual de OTs programadas y planes.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy,
    QGridLayout, QScrollArea, QMessageBox, QDialog, QInputDialog,
    QLineEdit, QListWidget
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor, QFont
from app.services.ot_service import OTService
from app.services.plan_service import PlanService
from app.services.equipo_service import EquipoService
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_BG_MEDIUM, COLOR_BG_DARK,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER
)
from datetime import datetime, timedelta
import calendar


DIAS_ES = ["Lun","Mar","Mie","Jue","Vie","Sab","Dom"]
MESES_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

COL_TIPO = {
    "Preventivo":  "#1565C0",
    "Correctivo":  "#C62828",
    "Inspeccion":  "#1B5E20",
    "Predictivo":  "#4A148C",
    "Emergencia":  "#B71C1C",
    "Lubricacion": "#E65100",
    "Mejora":      "#00695C",
}
COL_ESTADO = {
    "Programada": "#FF9800",
    "Liberada":   "#2196F3",
    "En proceso": "#9C27B0",
    "Cerrada":    "#4CAF50",
    "Anulada":    "#9E9E9E",
    "Vencida":    "#F44336",
}


class CalendarioWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hoy = datetime.now()
        self._anio  = hoy.year
        self._mes   = hoy.month
        self._ots_mes = []
        self._planes_mes = []
        self._uso_diario_estimado = 8.0
        self._equipos_cache = []
        self._actividades_plan = []
        self._construir_ui()
        QTimer.singleShot(100, self.cargar_mes)

    def _construir_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        # Encabezado + navegacion
        enc = QHBoxLayout()
        lbl = QLabel("Calendario de Mantenimiento")
        lbl.setStyleSheet(f"font-size:18px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")

        btn_ant = QPushButton("< Anterior")
        btn_ant.setFixedSize(90, 30)
        btn_ant.clicked.connect(self._mes_anterior)

        self.lbl_mes = QLabel()
        self.lbl_mes.setFixedWidth(180)
        self.lbl_mes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_mes.setStyleSheet(
            f"font-size:15px; font-weight:700; color:{COLOR_ACCENT_BLUE};")

        btn_sig = QPushButton("Siguiente >")
        btn_sig.setFixedSize(90, 30)
        btn_sig.clicked.connect(self._mes_siguiente)

        btn_hoy = QPushButton("Hoy")
        btn_hoy.setFixedSize(60, 30)
        btn_hoy.setStyleSheet(
            f"background-color:{COLOR_ACCENT_BLUE}; color:white; "
            f"border-radius:4px; border:none;")
        btn_hoy.clicked.connect(self._ir_hoy)

        self.combo_vista = QComboBox()
        self.combo_vista.addItems([
            "Plan PM - Fechas",
            "Plan PM - Hra/Km",
            "Cronograma Anual PM",
            "Lista OTs/Planes",
            "Vista Semanal"
        ])
        self.combo_vista.setFixedWidth(170)
        self.combo_vista.currentIndexChanged.connect(self._cambiar_vista)
        btn_lectura = QPushButton("Registrar horómetro")
        btn_lectura.setFixedHeight(30)
        btn_lectura.clicked.connect(self._registrar_lectura)
        btn_alertas = QPushButton("Alertas proximas")
        btn_alertas.setFixedHeight(30)
        btn_alertas.clicked.connect(self._mostrar_alertas)

        enc.addWidget(lbl)
        enc.addStretch()
        enc.addWidget(btn_ant)
        enc.addWidget(self.lbl_mes)
        enc.addWidget(btn_sig)
        enc.addWidget(btn_hoy)
        enc.addWidget(self.combo_vista)
        enc.addWidget(btn_lectura)
        enc.addWidget(btn_alertas)
        lay.addLayout(enc)

        # Leyenda
        leyenda = QHBoxLayout()
        leyenda.setSpacing(12)
        for tipo, col in list(COL_TIPO.items())[:6]:
            lbl_l = QLabel(tipo)
            lbl_l.setStyleSheet(
                f"background-color:{col}; color:white; border-radius:3px; "
                f"padding:2px 8px; font-size:11px; font-weight:600;")
            leyenda.addWidget(lbl_l)
        leyenda.addStretch()
        lay.addLayout(leyenda)

        # Area principal (calendario + panel lateral)
        main = QHBoxLayout()
        main.setSpacing(12)

        # Contenedor calendario con scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._contenedor_cal = QWidget()
        self._lay_cal = QVBoxLayout(self._contenedor_cal)
        self._lay_cal.setContentsMargins(0,0,0,0)
        self._scroll.setWidget(self._contenedor_cal)

        # Panel lateral: lista de OTs del dia seleccionado
        panel_lat = QFrame()
        panel_lat.setFixedWidth(280)
        panel_lat.setStyleSheet(
            f"background-color:{COLOR_BG_PANEL}; border-radius:8px; "
            f"border:1px solid {COLOR_BORDER};")
        lay_lat = QVBoxLayout(panel_lat)
        lay_lat.setContentsMargins(12,10,12,10)
        lay_lat.setSpacing(6)
        lbl_lat = QLabel("OTs del dia seleccionado")
        lbl_lat.setStyleSheet(
            f"font-weight:700; font-size:12px; color:{COLOR_TEXT_PRIMARY}; border:none;")
        lay_lat.addWidget(lbl_lat)
        self.tabla_dia = QTableWidget(0, 3)
        self.tabla_dia.setHorizontalHeaderLabels(["Numero","Equipo","Estado"])
        self.tabla_dia.verticalHeader().setVisible(False)
        self.tabla_dia.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_dia.horizontalHeader().setStretchLastSection(True)
        self.tabla_dia.setColumnWidth(0, 90)
        self.tabla_dia.setColumnWidth(1, 110)
        self.tabla_dia.setAlternatingRowColors(True)
        lay_lat.addWidget(self.tabla_dia)

        self.lbl_dia_sel = QLabel("")
        self.lbl_dia_sel.setStyleSheet(
            f"font-size:11px; color:{COLOR_TEXT_SECONDARY}; border:none;")
        lay_lat.addWidget(self.lbl_dia_sel)

        # Resumen del mes
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; border-top: 1px solid {COLOR_BORDER};")
        lay_lat.addWidget(sep)

        lbl_res = QLabel("Resumen del mes")
        lbl_res.setStyleSheet(
            f"font-weight:700; font-size:12px; color:{COLOR_TEXT_PRIMARY}; border:none;")
        lay_lat.addWidget(lbl_res)
        self.lbl_resumen = QLabel("Cargando...")
        self.lbl_resumen.setStyleSheet(
            f"font-size:11px; color:{COLOR_TEXT_SECONDARY}; border:none;")
        self.lbl_resumen.setWordWrap(True)
        lay_lat.addWidget(self.lbl_resumen)
        lay_lat.addStretch()

        main.addWidget(self._scroll, 1)
        main.addWidget(panel_lat)
        lay.addLayout(main)

    # -----------------------------------------------------------------
    # Navegacion
    # -----------------------------------------------------------------
    def _mes_anterior(self):
        if self.combo_vista.currentText() == "Cronograma Anual PM":
            self._anio -= 1
            self.cargar_mes()
            return
        if self._mes == 1:
            self._mes = 12; self._anio -= 1
        else:
            self._mes -= 1
        self.cargar_mes()

    def _mes_siguiente(self):
        if self.combo_vista.currentText() == "Cronograma Anual PM":
            self._anio += 1
            self.cargar_mes()
            return
        if self._mes == 12:
            self._mes = 1; self._anio += 1
        else:
            self._mes += 1
        self.cargar_mes()

    def _ir_hoy(self):
        hoy = datetime.now()
        self._anio = hoy.year; self._mes = hoy.month
        self.cargar_mes()

    def _cambiar_vista(self):
        self.cargar_mes()

    # -----------------------------------------------------------------
    # Carga de datos
    # -----------------------------------------------------------------
    def cargar_mes(self):
        self.lbl_mes.setText(f"{MESES_ES[self._mes]}  {self._anio}")
        primer_dia = datetime(self._anio, self._mes, 1)
        ultimo_dia_n = calendar.monthrange(self._anio, self._mes)[1]
        ultimo_dia = datetime(self._anio, self._mes, ultimo_dia_n, 23, 59, 59)

        try:
            self._ots_mes = OTService.listar_ots({
                "fecha_desde": primer_dia,
                "fecha_hasta": ultimo_dia,
            })
        except Exception as e:
            print(f"[Calendario] Error cargando OTs: {e}")
            self._ots_mes = []
        try:
            planes = PlanService.listar(estado="Activo")
            self._planes_mes = [
                p for p in planes
                if p.proxima_ejecucion
                and primer_dia <= p.proxima_ejecucion <= ultimo_dia
            ]
        except Exception:
            self._planes_mes = []

        vista = self.combo_vista.currentText()
        if vista == "Plan PM - Fechas":
            self._render_mensual(primer_dia, ultimo_dia_n)
        elif vista == "Plan PM - Hra/Km":
            self._render_horometro()
        elif vista == "Cronograma Anual PM":
            self._render_cronograma_anual(self._anio)
        elif vista == "Vista Semanal":
            self._render_semanal()
        else:
            self._render_lista()

        self._actualizar_resumen()

    # -----------------------------------------------------------------
    # Vista mensual
    # -----------------------------------------------------------------
    def _render_mensual(self, primer_dia: datetime, dias_mes: int):
        # Limpiar contenedor
        while self._lay_cal.count():
            item = self._lay_cal.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        grid = QGridLayout()
        grid.setSpacing(2)

        # Cabecera dias semana
        for col, dia in enumerate(DIAS_ES):
            lbl = QLabel(dia)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(28)
            lbl.setStyleSheet(
                f"background-color:{COLOR_BG_PANEL}; color:{COLOR_TEXT_SECONDARY}; "
                f"font-weight:700; font-size:11px; border-radius:3px; "
                f"letter-spacing:1px;")
            grid.addWidget(lbl, 0, col)

        # Construir mapa dia -> ots
        mapa = {}
        for ot in self._ots_mes:
            if ot.fecha_programada:
                d = ot.fecha_programada.day
                mapa.setdefault(d, []).append(("ot", ot))
        for plan in self._planes_mes:
            d = plan.proxima_ejecucion.day
            mapa.setdefault(d, []).append(("plan", plan))

        hoy = datetime.now()
        # Semana en que empieza el mes (0=lunes)
        inicio_col = primer_dia.weekday()
        dia_num = 1
        row = 1

        while dia_num <= dias_mes:
            for col in range(7):
                if row == 1 and col < inicio_col:
                    # Celda vacia
                    cel = QFrame()
                    cel.setMinimumHeight(80)
                    cel.setStyleSheet(f"background-color:{COLOR_BG_DARK}; border-radius:4px;")
                    grid.addWidget(cel, row, col)
                    continue
                if dia_num > dias_mes:
                    cel = QFrame()
                    cel.setMinimumHeight(80)
                    cel.setStyleSheet(f"background-color:{COLOR_BG_DARK}; border-radius:4px;")
                    grid.addWidget(cel, row, col)
                    continue

                es_hoy = (hoy.year==self._anio and hoy.month==self._mes and hoy.day==dia_num)
                eventos_dia = mapa.get(dia_num, [])
                cel = self._celda_dia(dia_num, eventos_dia, es_hoy)
                grid.addWidget(cel, row, col)
                dia_num += 1

            row += 1
            if dia_num > dias_mes:
                break

        wrapper = QWidget()
        wrapper.setLayout(grid)
        self._lay_cal.addWidget(wrapper)
        self._lay_cal.addStretch()

    def _celda_dia(self, dia: int, eventos: list, es_hoy: bool) -> QFrame:
        f = QFrame()
        f.setMinimumHeight(80)
        f.setMaximumHeight(110)
        borde = COLOR_ACCENT_BLUE if es_hoy else COLOR_BORDER
        bg    = f"{COLOR_BG_MEDIUM}" if not es_hoy else "#1a3a5c"
        f.setStyleSheet(
            f"background-color:{bg}; border-radius:5px; "
            f"border:1px solid {borde};")

        lay = QVBoxLayout(f)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(2)

        lbl_d = QLabel(str(dia))
        lbl_d.setStyleSheet(
            f"font-weight:{'900' if es_hoy else '600'}; "
            f"font-size:{'14' if es_hoy else '12'}px; "
            f"color:{'white' if es_hoy else COLOR_TEXT_SECONDARY}; border:none;")
        lay.addWidget(lbl_d)

        for tipo_evento, item in eventos[:3]:
            if tipo_evento == "ot":
                color = COL_TIPO.get(item.tipo_ot, COLOR_ACCENT_BLUE)
                texto = item.numero[:12]
                tip = f"{item.numero} - {item.tipo_ot}\nEstado: {item.estado}"
            else:
                color = "#8B5CF6"
                texto = f"PLAN {item.codigo[:8]}"
                tip = (
                    f"Plan: {item.codigo}\n"
                    f"Tipo: {item.tipo_mantenimiento}\n"
                    f"Alerta: {int(item.alerta_dias_anticipacion or 7)} dia(s)"
                )
            lbl_e = QLabel(texto)
            lbl_e.setStyleSheet(
                f"background-color:{color}; color:white; border-radius:2px; "
                f"padding:1px 4px; font-size:10px; font-weight:600; border:none;")
            lbl_e.setToolTip(tip)
            lay.addWidget(lbl_e)

        if len(eventos) > 3:
            lbl_m = QLabel(f"+{len(eventos)-3} mas")
            lbl_m.setStyleSheet(
                f"color:{COLOR_TEXT_SECONDARY}; font-size:10px; border:none;")
            lay.addWidget(lbl_m)

        lay.addStretch()

        # Click para ver OTs del dia
        f.mousePressEvent = lambda e, d=dia, ev=eventos: self._click_dia(d, ev)
        return f

    def _click_dia(self, dia: int, eventos: list):
        fecha_str = f"{dia:02d}/{self._mes:02d}/{self._anio}"
        total_ots = sum(1 for t, _ in eventos if t == "ot")
        total_planes = sum(1 for t, _ in eventos if t == "plan")
        self.lbl_dia_sel.setText(
            f"Fecha: {fecha_str} ({total_ots} OT(s), {total_planes} plan(es))")
        self.tabla_dia.setRowCount(0)
        for tipo_evento, evento in eventos:
            if tipo_evento != "ot":
                continue
            r = self.tabla_dia.rowCount()
            self.tabla_dia.insertRow(r)
            try: eq = evento.equipo.nombre[:14] if evento.equipo else "-"
            except: eq = "-"
            for c, v in enumerate([evento.numero, eq, evento.estado]):
                cell = QTableWidgetItem(v)
                if c == 2:
                    col = COL_ESTADO.get(evento.estado, "#FFF")
                    cell.setForeground(QColor(col))
                    f2 = QFont(); f2.setBold(True); cell.setFont(f2)
                self.tabla_dia.setItem(r, c, cell)

    # -----------------------------------------------------------------
    # Vista lista
    # -----------------------------------------------------------------
    def _render_lista(self):
        while self._lay_cal.count():
            item = self._lay_cal.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        tabla = QTableWidget(0, 7)
        tabla.setHorizontalHeaderLabels(
            ["Numero","Equipo","Tipo","Estado","Fecha","Horario","Responsable"])
        tabla.horizontalHeader().setStretchLastSection(True)
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setSortingEnabled(True)
        for i, w in enumerate([110,160,100,90,90,90]):
            tabla.setColumnWidth(i, w)

        for ot in sorted(self._ots_mes,
                         key=lambda o: o.fecha_programada or datetime.max):
            r = tabla.rowCount(); tabla.insertRow(r)
            try: eq = ot.equipo.nombre if ot.equipo else "-"
            except: eq = "-"
            try: resp = ot.responsable.nombre_completo if ot.responsable else "-"
            except: resp = "-"
            fecha = ot.fecha_programada.strftime("%d/%m/%Y") if ot.fecha_programada else "-"
            horario = f"{ot.hora_inicio_prog or '-'} - {ot.hora_fin_prog or '-'}"
            vals = [ot.numero, eq, ot.tipo_ot, ot.estado, fecha, horario, resp]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 1:  # tipo color
                    item.setForeground(
                        QColor(COL_TIPO.get(ot.tipo_ot, "#FFF")))
                elif c == 3:  # estado color
                    item.setForeground(
                        QColor(COL_ESTADO.get(ot.estado, "#FFF")))
                    ff = QFont(); ff.setBold(True); item.setFont(ff)
                tabla.setItem(r, c, item)
        for plan in sorted(self._planes_mes,
                           key=lambda p: p.proxima_ejecucion or datetime.max):
            r = tabla.rowCount(); tabla.insertRow(r)
            try: eq = plan.equipo.nombre if plan.equipo else "-"
            except: eq = "-"
            fecha = plan.proxima_ejecucion.strftime("%d/%m/%Y") if plan.proxima_ejecucion else "-"
            vals = [f"PLAN-{plan.codigo}", eq, plan.tipo_mantenimiento, "Pendiente", fecha, "-", "Planificado"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 2:
                    item.setForeground(QColor("#8B5CF6"))
                if c == 3:
                    ff = QFont(); ff.setBold(True); item.setFont(ff)
                    item.setForeground(QColor("#8B5CF6"))
                tabla.setItem(r, c, item)

        self._lay_cal.addWidget(tabla)

    # -----------------------------------------------------------------
    # Vista semanal
    # -----------------------------------------------------------------
    def _render_semanal(self):
        while self._lay_cal.count():
            item = self._lay_cal.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        # Semana actual dentro del mes
        hoy = datetime.now()
        if hoy.year == self._anio and hoy.month == self._mes:
            base = hoy - timedelta(days=hoy.weekday())
        else:
            base = datetime(self._anio, self._mes, 1)
            base = base - timedelta(days=base.weekday())

        grid = QGridLayout(); grid.setSpacing(4)

        # Cabecera
        for col in range(7):
            dia = base + timedelta(days=col)
            es_hoy = (dia.date() == datetime.now().date())
            lbl = QLabel(f"{DIAS_ES[col]}\n{dia.strftime('%d/%m')}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"background-color:{'#1a3a5c' if es_hoy else COLOR_BG_PANEL}; "
                f"color:{'white' if es_hoy else COLOR_TEXT_PRIMARY}; "
                f"font-weight:700; font-size:12px; border-radius:4px; "
                f"padding:4px; border:1px solid {COLOR_ACCENT_BLUE if es_hoy else COLOR_BORDER};")
            grid.addWidget(lbl, 0, col)

        # Celdas
        for col in range(7):
            dia = base + timedelta(days=col)
            ots_dia = [o for o in self._ots_mes if o.fecha_programada and o.fecha_programada.date() == dia.date()]
            planes_dia = [p for p in self._planes_mes if p.proxima_ejecucion and p.proxima_ejecucion.date() == dia.date()]
            cel = QFrame()
            cel.setMinimumHeight(200)
            cel.setStyleSheet(
                f"background-color:{COLOR_BG_MEDIUM}; border-radius:5px; "
                f"border:1px solid {COLOR_BORDER};")
            lay_c = QVBoxLayout(cel)
            lay_c.setContentsMargins(4,4,4,4)
            lay_c.setSpacing(3)
            for ot in ots_dia:
                color = COL_TIPO.get(ot.tipo_ot, COLOR_ACCENT_BLUE)
                try: eq = ot.equipo.nombre[:12] if ot.equipo else "-"
                except: eq = "-"
                lbl_ot = QLabel(f"{ot.numero}\n{eq}\n{ot.estado}")
                lbl_ot.setStyleSheet(
                    f"background-color:{color}; color:white; border-radius:3px; "
                    f"padding:3px 5px; font-size:10px; font-weight:600; border:none;")
                lbl_ot.setWordWrap(True)
                lay_c.addWidget(lbl_ot)
            for plan in planes_dia:
                lbl_pl = QLabel(f"PLAN {plan.codigo}\n{plan.tipo_mantenimiento}\nPendiente")
                lbl_pl.setStyleSheet(
                    "background-color:#8B5CF6; color:white; border-radius:3px; "
                    "padding:3px 5px; font-size:10px; font-weight:600; border:none;")
                lbl_pl.setWordWrap(True)
                lay_c.addWidget(lbl_pl)
            lay_c.addStretch()
            grid.addWidget(cel, 1, col)

        wrapper = QWidget()
        wrapper.setLayout(grid)
        self._lay_cal.addWidget(wrapper)
        self._lay_cal.addStretch()

    # -----------------------------------------------------------------
    # Resumen lateral
    # -----------------------------------------------------------------
    def _actualizar_resumen(self):
        total  = len(self._ots_mes)
        prev   = sum(1 for o in self._ots_mes if o.tipo_ot in ("Preventivo","Lubricacion","Inspeccion","Predictivo"))
        corr   = sum(1 for o in self._ots_mes if o.tipo_ot in ("Correctivo","Emergencia"))
        cerr   = sum(1 for o in self._ots_mes if o.estado == "Cerrada")
        proc   = sum(1 for o in self._ots_mes if o.estado == "En proceso")
        venc   = sum(1 for o in self._ots_mes
                     if o.estado in ("Programada","Liberada")
                     and o.fecha_programada
                     and o.fecha_programada < datetime.now())
        costo  = sum(o.costo_total or 0 for o in self._ots_mes if o.estado=="Cerrada")

        self.lbl_resumen.setText(
            f"Total OTs: {total}\n"
            f"Planes en calendario: {len(self._planes_mes)}\n"
            f"Preventivas: {prev}\n"
            f"Correctivas: {corr}\n"
            f"Cerradas: {cerr}\n"
            f"En proceso: {proc}\n"
            f"Vencidas: {venc}\n"
            f"Costo mes: {costo:,.2f}"
        )

    def _mostrar_alertas(self):
        alertas = PlanService.obtener_alertas_mantenimiento(dias_max=60)
        dlg = QDialog(self)
        dlg.setWindowTitle("Alertas de mantenimientos proximos")
        dlg.resize(760, 380)
        lay = QVBoxLayout(dlg)
        lbl = QLabel(f"Total alertas: {len(alertas)}")
        lbl.setStyleSheet(f"font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        lay.addWidget(lbl)

        tabla = QTableWidget(0, 7)
        tabla.setHorizontalHeaderLabels(
            ["Plan", "Equipo", "Tipo", "Proxima ejecucion", "Dias restantes", "Anticipacion", "Prioridad"]
        )
        tabla.horizontalHeader().setStretchLastSection(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i, w in enumerate([95, 170, 90, 130, 95, 90]):
            tabla.setColumnWidth(i, w)

        for a in alertas:
            r = tabla.rowCount()
            tabla.insertRow(r)
            vals = [
                a["codigo"],
                a["equipo"],
                a["tipo"],
                a["proxima_ejecucion"].strftime("%d/%m/%Y"),
                str(a["dias_restantes"]),
                f"{a['dias_alerta']} dia(s)",
                a["prioridad"],
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 4 and int(a["dias_restantes"]) <= 0:
                    item.setForeground(QColor(COLOR_DANGER))
                    ff = QFont(); ff.setBold(True); item.setFont(ff)
                tabla.setItem(r, c, item)
        lay.addWidget(tabla)

        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(dlg.accept)
        lay.addWidget(cerrar, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def _registrar_lectura(self):
        from app.services.equipo_service import EquipoService
        equipos = EquipoService.listar(solo_activos=True)
        if not equipos:
            QMessageBox.information(self, "Lecturas", "No hay equipos activos.")
            return
        opciones = [f"{e.codigo} - {e.nombre}" for e in equipos]
        sel, ok = QInputDialog.getItem(
            self, "Registrar horómetro/km", "Equipo:", opciones, 0, False
        )
        if not ok:
            return
        eq = equipos[opciones.index(sel)]
        lectura, ok = QInputDialog.getDouble(
            self,
            "Registrar lectura",
            f"Lectura actual para {eq.codigo}:",
            float(eq.lectura_actual or 0),
            0,
            999999999,
            2
        )
        if not ok:
            return
        ok_s, msg = PlanService.registrar_lectura_diaria(eq.id, lectura)
        (QMessageBox.information if ok_s else QMessageBox.critical)(self, "Lecturas", msg)
        if ok_s:
            self.cargar_mes()

    def _render_horometro(self):
        while self._lay_cal.count():
            item = self._lay_cal.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tabla = QTableWidget(0, 9)
        tabla.setHorizontalHeaderLabels([
            "Plan", "Equipo", "Tipo contador", "Lectura actual",
            "Meta siguiente", "Faltante", "Días estimados",
            "Prioridad", "Estado"
        ])
        tabla.horizontalHeader().setStretchLastSection(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        for i, w in enumerate([90, 170, 110, 100, 100, 90, 95, 80]):
            tabla.setColumnWidth(i, w)

        rows = PlanService.obtener_estado_planes_contador(self._uso_diario_estimado)
        for d in rows:
            r = tabla.rowCount()
            tabla.insertRow(r)
            estado = "ALERTA" if d["dias_estimados"] <= 3 else ("Próximo" if d["dias_estimados"] <= 7 else "Normal")
            vals = [
                d["codigo"], d["equipo"], d["tipo_contador"],
                f"{d['lectura_actual']:.2f}", f"{d['meta_siguiente']:.2f}",
                f"{d['faltante']:.2f}", f"{d['dias_estimados']:.1f}",
                d["prioridad"], estado
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 8:
                    color = COLOR_DANGER if estado == "ALERTA" else COLOR_WARNING if estado == "Próximo" else COLOR_SUCCESS
                    it.setForeground(QColor(color))
                    fnt = QFont(); fnt.setBold(True); it.setFont(fnt)
                tabla.setItem(r, c, it)

        lbl = QLabel("Modo Hra/Km: registra lecturas diarias para actualizar faltantes y días estimados.")
        lbl.setStyleSheet(f"color:{COLOR_TEXT_SECONDARY}; font-size:12px;")
        self._lay_cal.addWidget(lbl)
        self._lay_cal.addWidget(tabla)

    def _render_cronograma_anual(self, anio: int):
        while self._lay_cal.count():
            item = self._lay_cal.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        inicio_anio = datetime(anio, 1, 1)
        fin_anio = datetime(anio, 12, 31, 23, 59, 59)
        planes = PlanService.listar(estado="Activo")
        planes = [p for p in planes if p.proxima_ejecucion]

        dias_en_anio = 366 if calendar.isleap(anio) else 365
        tabla = QTableWidget(0, 8 + dias_en_anio)
        headers = [
            "Código", "Equipo", "Tipo", "Prioridad", "Frecuencia",
            "Inicio", "Próxima", "Estado"
        ] + [f"{(inicio_anio + timedelta(days=i-1)).strftime('%d/%m')}" for i in range(1, dias_en_anio + 1)]
        tabla.setHorizontalHeaderLabels(headers)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        for i, w in enumerate([90, 170, 95, 80, 95, 80, 85, 90]):
            tabla.setColumnWidth(i, w)
        for i in range(8, 8 + dias_en_anio):
            tabla.setColumnWidth(i, 24)

        for p in planes:
            fila = tabla.rowCount()
            tabla.insertRow(fila)
            try:
                equipo = p.equipo.nombre if p.equipo else "-"
            except Exception:
                equipo = "-"
            base_vals = [
                p.codigo,
                equipo,
                p.tipo_mantenimiento,
                p.prioridad,
                f"{p.frecuencia:.0f} {p.unidad_frecuencia}",
                p.fecha_inicio.strftime("%d/%m") if p.fecha_inicio else "-",
                p.proxima_ejecucion.strftime("%d/%m/%Y"),
                p.estado,
            ]
            for c, v in enumerate(base_vals):
                tabla.setItem(fila, c, QTableWidgetItem(str(v)))

            for dia in self._dias_programados_plan(p, inicio_anio, fin_anio):
                col = 8 + dia - 1
                if 8 <= col < tabla.columnCount():
                    it = QTableWidgetItem("X")
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    it.setForeground(QColor(COLOR_ACCENT_BLUE))
                    tabla.setItem(fila, col, it)

        titulo = QLabel(f"Cronograma Anual de Mantenimiento Preventivo - Año {anio}")
        titulo.setStyleSheet(f"font-size:18px; font-weight:700; color:{COLOR_TEXT_PRIMARY};")
        self._lay_cal.addWidget(self._crear_panel_plan())
        self._lay_cal.addWidget(titulo)
        self._lay_cal.addWidget(tabla)

    def _dias_programados_plan(self, plan, inicio: datetime, fin: datetime) -> list[int]:
        """
        Calcula día-del-año programado dentro del año según la frecuencia del plan.
        """
        from dateutil.relativedelta import relativedelta

        actual = plan.proxima_ejecucion or inicio
        unidad = (plan.unidad_frecuencia or "Dias").lower()
        freq = max(1, int(plan.frecuencia or 1))
        dias = set()
        guard = 0
        while actual <= fin and guard < 500:
            guard += 1
            if actual >= inicio:
                dias.add(actual.timetuple().tm_yday)
            if "dia" in unidad:
                actual += timedelta(days=freq)
            elif "sem" in unidad:
                actual += timedelta(weeks=freq)
            elif "mes" in unidad:
                actual += relativedelta(months=freq)
            elif "año" in unidad or "ano" in unidad:
                actual += relativedelta(years=freq)
            else:
                actual += timedelta(days=freq)
        return sorted(dias)

    def _crear_panel_plan(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background-color:{COLOR_BG_PANEL}; border:1px solid {COLOR_BORDER}; border-radius:8px;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        titulo = QLabel("Registro rápido de Plan PM (en esta misma pantalla)")
        titulo.setStyleSheet(f"font-weight:700; color:{COLOR_TEXT_PRIMARY}; font-size:13px;")
        lay.addWidget(titulo)

        fila1 = QHBoxLayout()
        self.inp_buscar_equipo = QLineEdit()
        self.inp_buscar_equipo.setPlaceholderText("Buscar equipo por código o descripción...")
        self.inp_buscar_equipo.textChanged.connect(self._filtrar_equipos_panel)
        self.cmb_equipo_panel = QComboBox()
        self.cmb_equipo_panel.setMinimumWidth(300)
        self._equipos_cache = EquipoService.listar(solo_activos=True)
        for e in self._equipos_cache:
            self.cmb_equipo_panel.addItem(f"{e.codigo} - {e.nombre}", e.id)

        self.inp_codigo_plan = QLineEdit()
        self.inp_codigo_plan.setPlaceholderText("Código plan (auto si vacío)")
        self.cmb_tipo_plan = QComboBox()
        self.cmb_tipo_plan.addItems(["Preventivo", "Predictivo", "Lubricacion", "Inspeccion", "Mejora"])
        self.cmb_prioridad_plan = QComboBox()
        self.cmb_prioridad_plan.addItems(["Urgente", "Alta", "Normal", "Baja"])
        self.cmb_frecuencia = QComboBox()
        self.cmb_frecuencia.addItems(["7 Dias", "15 Dias", "30 Dias", "60 Dias", "90 Dias", "180 Dias", "365 Dias"])

        fila1.addWidget(QLabel("Equipo:"))
        fila1.addWidget(self.inp_buscar_equipo, 2)
        fila1.addWidget(self.cmb_equipo_panel, 3)
        fila1.addWidget(QLabel("Código:"))
        fila1.addWidget(self.inp_codigo_plan, 2)
        fila1.addWidget(QLabel("Tipo:"))
        fila1.addWidget(self.cmb_tipo_plan)
        fila1.addWidget(QLabel("Prioridad:"))
        fila1.addWidget(self.cmb_prioridad_plan)
        fila1.addWidget(QLabel("Frecuencia:"))
        fila1.addWidget(self.cmb_frecuencia)
        lay.addLayout(fila1)

        fila2 = QHBoxLayout()
        self.inp_actividad = QLineEdit()
        self.inp_actividad.setPlaceholderText("Actividad individual...")
        btn_add = QPushButton("Agregar actividad")
        btn_add.clicked.connect(self._agregar_actividad_panel)
        btn_del = QPushButton("Quitar actividad")
        btn_del.clicked.connect(self._quitar_actividad_panel)
        self.lst_actividades = QListWidget()
        self.lst_actividades.setMaximumHeight(95)

        botones = QVBoxLayout()
        btn_pack = QPushButton("Paquete PM")
        btn_pack.clicked.connect(self._boton_paquete_pm)
        btn_reg = QPushButton("Registrar Plan")
        btn_reg.setObjectName("btn_primary")
        btn_reg.clicked.connect(self._registrar_plan_panel)
        botones.addWidget(btn_pack)
        botones.addWidget(btn_reg)
        botones.addStretch()

        fila2.addWidget(QLabel("Actividad:"))
        fila2.addWidget(self.inp_actividad, 3)
        fila2.addWidget(btn_add)
        fila2.addWidget(btn_del)
        fila2.addWidget(self.lst_actividades, 4)
        fila2.addLayout(botones)
        lay.addLayout(fila2)
        return panel

    def _filtrar_equipos_panel(self, texto: str):
        texto = (texto or "").lower().strip()
        self.cmb_equipo_panel.clear()
        for e in self._equipos_cache:
            cad = f"{e.codigo} {e.nombre}".lower()
            if texto and texto not in cad:
                continue
            self.cmb_equipo_panel.addItem(f"{e.codigo} - {e.nombre}", e.id)

    def _agregar_actividad_panel(self):
        act = self.inp_actividad.text().strip()
        if not act:
            return
        self._actividades_plan.append(act)
        self.lst_actividades.addItem(act)
        self.inp_actividad.clear()

    def _quitar_actividad_panel(self):
        row = self.lst_actividades.currentRow()
        if row < 0:
            return
        self.lst_actividades.takeItem(row)
        if 0 <= row < len(self._actividades_plan):
            self._actividades_plan.pop(row)

    def _boton_paquete_pm(self):
        QMessageBox.information(
            self, "Paquete PM",
            "Botón preparado. En el siguiente paso implementamos la lógica de paquetes de mantenimiento.")

    def _registrar_plan_panel(self):
        equipo_id = self.cmb_equipo_panel.currentData()
        if not equipo_id:
            QMessageBox.warning(self, "Plan PM", "Seleccione un equipo.")
            return
        codigo = self.inp_codigo_plan.text().strip()
        if not codigo:
            codigo = f"PM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        freq_txt = self.cmb_frecuencia.currentText().split()[0]
        frecuencia = float(freq_txt)
        datos = {
            "codigo": codigo,
            "equipo_id": equipo_id,
            "descripcion": " / ".join(self._actividades_plan) if self._actividades_plan else "Plan PM desde cronograma",
            "tipo_mantenimiento": self.cmb_tipo_plan.currentText(),
            "frecuencia": frecuencia,
            "unidad_frecuencia": "Dias",
            "criterio": "Fecha",
            "duracion_estimada": 2.0,
            "prioridad": self.cmb_prioridad_plan.currentText(),
            "criticidad": "Media",
            "alerta_dias_anticipacion": 7,
        }
        checklist = [{"descripcion": a, "obligatorio": False} for a in self._actividades_plan]
        ok, msg, _ = PlanService.crear(datos, checklist, [])
        (QMessageBox.information if ok else QMessageBox.critical)(self, "Plan PM", msg)
        if ok:
            self.inp_codigo_plan.clear()
            self._actividades_plan = []
            self.lst_actividades.clear()
            self.cargar_mes()

"""
Módulo Materiales — Gestión de stock e inventario.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QComboBox,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QTextEdit, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.views.shared.tabla_base import TablaBase
from app.services.material_service import MaterialService
from app.core.session import session_usuario
from app.views.shared.styles import (
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_ACCENT_BLUE,
    COLOR_BORDER, COLOR_BG_PANEL, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING
)


COLUMNAS_MATS = [
    {"header": "Código",     "key": "codigo",      "width": 100},
    {"header": "Descripción","key": "descripcion", "width": 240},
    {"header": "Categoría",  "key": "categoria",   "width": 110},
    {"header": "Unidad",     "key": "unidad",      "width": 65},
    {"header": "Stock",      "key": "stock",       "width": 80,
     "align": Qt.AlignmentFlag.AlignRight},
    {"header": "Mínimo",     "key": "minimo",      "width": 70,
     "align": Qt.AlignmentFlag.AlignRight},
    {"header": "Estado Stock","key": "alerta",     "width": 90},
    {"header": "Costo Unit.","key": "costo",       "width": 90,
     "align": Qt.AlignmentFlag.AlignRight},
    {"header": "Estado",     "key": "estado",      "width": 75},
]


class MaterialesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()
        self.cargar_datos()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        enc = QHBoxLayout()
        lbl = QLabel("[Mat]  Gestión de Materiales")
        lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};")
        self.lbl_alertas = QLabel()
        self.lbl_alertas.setStyleSheet(
            f"color: {COLOR_DANGER}; font-weight: 600; font-size: 12px;")
        enc.addWidget(lbl)
        enc.addWidget(self.lbl_alertas)
        enc.addStretch()
        layout.addLayout(enc)

        # Filtros
        fil = QHBoxLayout()
        fil.setSpacing(8)

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(
            ["Todos", "Activo", "Inactivo"])
        self.combo_estado.setFixedWidth(100)
        self.combo_estado.currentIndexChanged.connect(self.cargar_datos)

        self.chk_alerta = QComboBox()
        self.chk_alerta.addItems(
            ["Todo stock", "Solo alertas (bajo/crítico)"])
        self.chk_alerta.setFixedWidth(180)
        self.chk_alerta.currentIndexChanged.connect(self.cargar_datos)

        fil.addWidget(QLabel("Estado:"))
        fil.addWidget(self.combo_estado)
        fil.addWidget(QLabel("Stock:"))
        fil.addWidget(self.chk_alerta)
        fil.addStretch()
        layout.addLayout(fil)

        # Tabla
        self.tabla = TablaBase(columnas=COLUMNAS_MATS)
        self.tabla.doble_click.connect(self._ver_movimientos)
        layout.addWidget(self.tabla)

        # Botones
        btn_frame = QFrame()
        btn_frame.setStyleSheet(
            f"background-color: {COLOR_BG_PANEL}; border-radius: 6px; "
            f"border: 1px solid {COLOR_BORDER}; padding: 6px;")
        bl = QHBoxLayout(btn_frame)
        bl.setSpacing(6)

        acciones = [
            ("[+] Nuevo",          self._nuevo,           "normal"),
            ("[Edit] Editar",          self._editar,          "normal"),
            ("[Hist] Movimientos",    self._ver_movimientos_btn, "normal"),
            ("[Ajst] Ajustar stock",  self._ajustar,         "normal"),
            ("[X] Desactivar",     self._desactivar,      "danger"),
            ("[Imp] Importar",       self._importar,        "normal"),
            ("[Exp] Exportar",       self._exportar,        "normal"),
        ]
        for texto, cb, est in acciones:
            b = QPushButton(texto)
            b.setFixedHeight(30)
            if est == "danger":
                b.setStyleSheet(
                    "background-color: #C62828; color: white; "
                    "border-radius: 4px; border: none; padding: 0 10px;")
            b.clicked.connect(cb)
            bl.addWidget(b)
        bl.addStretch()
        layout.addWidget(btn_frame)

    def cargar_datos(self):
        estado = self.combo_estado.currentText()
        solo_alerta = self.chk_alerta.currentIndex() == 1

        filtro_estado = None if estado == "Todos" else estado
        mats = MaterialService.listar(
            solo_activos=(filtro_estado == "Activo"),
            alerta_stock=solo_alerta
        )
        if filtro_estado and filtro_estado != "Activo":
            mats = [m for m in mats if m.estado == filtro_estado]

        datos, ids = [], []
        alertas = 0
        for m in mats:
            if m.alerta_stock != "normal":
                alertas += 1
            datos.append({
                "codigo": m.codigo,
                "descripcion": m.descripcion,
                "categoria": m.categoria or "-",
                "unidad": m.unidad,
                "stock": f"{m.stock_actual:.1f}",
                "minimo": f"{m.stock_minimo:.1f}",
                "alerta": m.alerta_stock.upper(),
                "costo": f"{m.costo_unitario:,.2f}",
                "estado": m.estado,
            })
            ids.append(m.id)

        self.tabla.cargar(datos, ids)
        self.lbl_alertas.setText(
            f"[!] {alertas} alerta(s) de stock" if alertas else "")

    # ---------------------------------------------------------------------
    # Acciones
    # ---------------------------------------------------------------------

    def _nuevo(self):
        from app.views.materiales.material_form import MaterialForm
        dlg = MaterialForm(parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _editar(self):
        mid = self.tabla.id_seleccionado()
        if not mid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un material.")
            return
        from app.views.materiales.material_form import MaterialForm
        dlg = MaterialForm(material_id=mid, parent=self)
        if dlg.exec():
            self.cargar_datos()

    def _ver_movimientos(self, mid: int = None):
        eid = mid or self.tabla.id_seleccionado()
        if not eid:
            return
        movs = MaterialService.obtener_movimientos(eid)
        mat = MaterialService.obtener(eid)
        texto = f"Movimientos: {mat.descripcion}\n\n"
        for mv in movs:
            texto += (f"{mv.fecha.strftime('%d/%m/%Y %H:%M')}  "
                      f"{mv.tipo_movimiento:12s}  "
                      f"{mv.cantidad:8.2f}  "
                      f"Stock: {mv.stock_posterior:.2f}  "
                      f"{mv.motivo or ''}\n")
        QMessageBox.information(self, "Historial de movimientos", texto or "Sin movimientos.")

    def _ver_movimientos_btn(self):
        self._ver_movimientos()

    def _ajustar(self):
        mid = self.tabla.id_seleccionado()
        if not mid:
            QMessageBox.information(self, "Seleccionar",
                                     "Seleccione un material.")
            return
        mat = MaterialService.obtener(mid)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Ajustar stock — {mat.descripcion}")
        dlg.setFixedSize(360, 220)
        lay = QFormLayout(dlg)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        lbl_curr = QLabel(f"Stock actual: {mat.stock_actual:.2f} {mat.unidad}")
        lbl_curr.setStyleSheet(
            f"color: {COLOR_ACCENT_BLUE}; font-weight: 600;")

        inp_nuevo = QDoubleSpinBox()
        inp_nuevo.setRange(0, 9999999.0)
        inp_nuevo.setDecimals(2)
        inp_nuevo.setValue(mat.stock_actual)

        inp_motivo = QLineEdit()
        inp_motivo.setPlaceholderText("Motivo del ajuste (obligatorio)")

        lay.addRow("Info:", lbl_curr)
        lay.addRow("Nuevo stock *:", inp_nuevo)
        lay.addRow("Motivo *:", inp_motivo)

        btns = QHBoxLayout()
        btn_ok = QPushButton("Aplicar ajuste")
        btn_ok.setStyleSheet(
            f"background-color: {COLOR_ACCENT_BLUE}; color: white; "
            f"border-radius: 4px; border: none;")
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        lay.addRow(btns)

        if dlg.exec():
            if not inp_motivo.text().strip():
                QMessageBox.warning(self, "Motivo requerido",
                                     "El motivo del ajuste es obligatorio.")
                return
            ok, msg = MaterialService.ajustar_stock(
                mid, inp_nuevo.value(), inp_motivo.text().strip())
            if ok:
                QMessageBox.information(self, "Ajuste aplicado", msg)
                self.cargar_datos()
            else:
                QMessageBox.critical(self, "Error", msg)

    def _desactivar(self):
        mid = self.tabla.id_seleccionado()
        if not mid:
            return
        mat = MaterialService.obtener(mid)
        resp = QMessageBox.question(
            self, "Desactivar material",
            f"¿Desactivar '{mat.descripcion}'?\n"
            "Si tiene movimientos, solo se desactivará (no se eliminará).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            ok, msg = MaterialService.desactivar(mid)
            if ok:
                QMessageBox.information(self, "OK", msg)
                self.cargar_datos()
            else:
                QMessageBox.critical(self, "Error", msg)

    def _importar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar materiales", "", "Excel (*.xlsx *.xls)")
        if not ruta:
            return
        try:
            import pandas as pd
            df = pd.read_excel(ruta)
            req = ["codigo", "descripcion"]
            falt = [c for c in req if c not in df.columns]
            if falt:
                QMessageBox.critical(
                    self, "Error",
                    f"Faltan columnas: {', '.join(falt)}")
                return
            ok_c, err_c = 0, []
            for i, row in df.iterrows():
                datos = {c: str(row[c]) if __import__("pandas").notna(
                    row.get(c)) else "" for c in df.columns}
                ok, msg, _ = MaterialService.crear(datos)
                if ok:
                    ok_c += 1
                else:
                    err_c.append(f"Fila {i+2}: {msg}")
            QMessageBox.information(
                self, "Importación",
                f"Importados: {ok_c}. Errores: {len(err_c)}.")
            self.cargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))

    def _exportar(self):
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar materiales", "materiales.xlsx",
            "Excel (*.xlsx)")
        if not ruta:
            return
        try:
            import pandas as pd
            mats = MaterialService.listar()
            datos = [{
                "Código": m.codigo, "Descripción": m.descripcion,
                "Categoría": m.categoria, "Unidad": m.unidad,
                "Stock": m.stock_actual, "Mínimo": m.stock_minimo,
                "Costo unitario": m.costo_unitario,
                "Proveedor": m.proveedor, "Estado": m.estado,
            } for m in mats]
            pd.DataFrame(datos).to_excel(ruta, index=False)
            QMessageBox.information(self, "Exportado", ruta)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

"""
TablaBase — QTableWidget reutilizable con:
  - columnas configurables
  - filtro de texto en tiempo real
  - coloración de filas por estado
  - doble clic para abrir detalle
  - exportación básica a Excel/CSV
"""
from typing import List, Dict, Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QLabel,
    QPushButton, QAbstractItemView, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel
from PySide6.QtGui import QColor, QFont

from app.views.shared.styles import COLORES_ESTADO_TABLA, COLOR_TEXT_SECONDARY


class TablaBase(QWidget):
    """
    Widget de tabla genérico y reutilizable.

    Señales:
      fila_seleccionada(int)     — emite el ID de la fila seleccionada
      doble_click(int)           — emite el ID al hacer doble clic
    """
    fila_seleccionada = Signal(int)
    doble_click = Signal(int)

    def __init__(self,
                 columnas: List[Dict],
                 mostrar_filtro: bool = True,
                 columna_estado: str = None,
                 parent=None):
        """
        Args:
            columnas: Lista de dicts con claves:
                      'header': str, 'key': str, 'width': int (opcional),
                      'align': Qt.AlignmentFlag (opcional)
            mostrar_filtro: Si mostrar input de filtro de texto
            columna_estado: Nombre de la clave cuyo valor define el color de fila
        """
        super().__init__(parent)
        self.columnas = columnas
        self.columna_estado = columna_estado
        self._datos: List[Dict] = []
        self._ids: List[int] = []
        self._doble_click_cb: Optional[Callable] = None

        self._construir_ui(mostrar_filtro)

    def _construir_ui(self, mostrar_filtro: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Barra de filtro
        if mostrar_filtro:
            bar = QHBoxLayout()
            lbl = QLabel("[Aud] Buscar:")
            lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
            self.input_filtro = QLineEdit()
            self.input_filtro.setPlaceholderText("Escriba para filtrar...")
            self.input_filtro.setMaximumWidth(340)
            self.input_filtro.textChanged.connect(self._filtrar)
            self.lbl_conteo = QLabel("0 registros")
            self.lbl_conteo.setStyleSheet(
                f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
            bar.addWidget(lbl)
            bar.addWidget(self.input_filtro)
            bar.addStretch()
            bar.addWidget(self.lbl_conteo)
            layout.addLayout(bar)

        # Tabla
        self.tabla = QTableWidget(0, len(self.columnas))
        self.tabla.setHorizontalHeaderLabels(
            [c["header"] for c in self.columnas])
        self.tabla.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSortingEnabled(True)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.doubleClicked.connect(self._on_doble_click)
        self.tabla.selectionModel().selectionChanged.connect(
            self._on_seleccion_cambio)

        # Anchos de columna
        for i, col in enumerate(self.columnas):
            if "width" in col:
                self.tabla.setColumnWidth(i, col["width"])
            else:
                self.tabla.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.Interactive)

        layout.addWidget(self.tabla)

    def cargar(self, datos: List[Dict], ids: List[int] = None):
        """
        Carga datos en la tabla.

        Args:
            datos: Lista de dicts, cada dict debe tener las mismas claves
                   que en columnas[i]['key']
            ids: Lista de IDs correspondientes a cada fila (mismo orden)
        """
        self._datos = datos
        self._ids = ids or list(range(len(datos)))
        self._renderizar(datos, self._ids)

    def _renderizar(self, datos: List[Dict], ids: List[int]):
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)

        for row_idx, (dato, rid) in enumerate(zip(datos, ids)):
            self.tabla.insertRow(row_idx)
            for col_idx, col_def in enumerate(self.columnas):
                valor = dato.get(col_def["key"], "")
                item = QTableWidgetItem(str(valor) if valor is not None else "")
                item.setData(Qt.ItemDataRole.UserRole, rid)

                align = col_def.get("align", Qt.AlignmentFlag.AlignLeft)
                item.setTextAlignment(
                    align | Qt.AlignmentFlag.AlignVCenter)

                # Colorear fila según estado
                if self.columna_estado:
                    estado = dato.get(self.columna_estado, "")
                    color_pair = COLORES_ESTADO_TABLA.get(estado)
                    if color_pair:
                        # Usamos color sutil en dark theme
                        bg = QColor(color_pair[0])
                        bg.setAlpha(60)
                        item.setBackground(bg)

                self.tabla.setItem(row_idx, col_idx, item)

        self.tabla.setSortingEnabled(True)
        if hasattr(self, "lbl_conteo"):
            self.lbl_conteo.setText(f"{len(datos)} registros")

    def _filtrar(self, texto: str):
        """Filtra filas cuyo texto no contenga la búsqueda."""
        texto = texto.lower().strip()
        if not texto:
            self._renderizar(self._datos, self._ids)
            return

        filtrados_datos = []
        filtrados_ids = []
        for dato, rid in zip(self._datos, self._ids):
            # Buscar en todos los campos como string
            haystack = " ".join(str(v) for v in dato.values()).lower()
            if texto in haystack:
                filtrados_datos.append(dato)
                filtrados_ids.append(rid)

        self._renderizar(filtrados_datos, filtrados_ids)

    def _on_doble_click(self, index):
        rid = self._get_id_fila(index.row())
        if rid is not None:
            self.doble_click.emit(rid)

    def _on_seleccion_cambio(self, selected, deselected):
        rows = self.tabla.selectedItems()
        if rows:
            rid = self._get_id_fila(self.tabla.currentRow())
            if rid is not None:
                self.fila_seleccionada.emit(rid)

    def _get_id_fila(self, row: int) -> Optional[int]:
        item = self.tabla.item(row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def id_seleccionado(self) -> Optional[int]:
        """Retorna el ID de la fila actualmente seleccionada."""
        row = self.tabla.currentRow()
        return self._get_id_fila(row)

    def limpiar(self):
        self.tabla.setRowCount(0)
        self._datos = []
        self._ids = []
        if hasattr(self, "lbl_conteo"):
            self.lbl_conteo.setText("0 registros")

    def colorear_fila(self, row: int, color_hex: str, alpha: int = 60):
        """Colorea manualmente una fila específica."""
        c = QColor(color_hex)
        c.setAlpha(alpha)
        for col in range(self.tabla.columnCount()):
            item = self.tabla.item(row, col)
            if item:
                item.setBackground(c)

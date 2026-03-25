"""
Estilos globales QSS — Tema "Aurora Graphite" PMP.
Paleta moderna: grafito profundo + acentos cian/violeta/esmeralda.
"""

# Colores principales
COLOR_BG_DARK = "#0B1020"
COLOR_BG_MEDIUM = "#121A2F"
COLOR_BG_LIGHT = "#1A2542"
COLOR_BG_PANEL = "#1E2B4D"
COLOR_ACCENT_BLUE = "#5EEAD4"
COLOR_ACCENT_BLUE_DARK = "#14B8A6"
COLOR_TEXT_PRIMARY = "#E6EDF7"
COLOR_TEXT_SECONDARY = "#9FB0CC"
COLOR_BORDER = "#2D3E68"

# Colores de estado
COLOR_SUCCESS = "#22C55E"    # Verde moderno
COLOR_WARNING = "#F59E0B"    # Ámbar moderno
COLOR_DANGER = "#F43F5E"     # Rosa/rojo moderno
COLOR_INFO = "#38BDF8"       # Cian/azul moderno

STYLESHEET_GLOBAL = f"""
/* ===========================================================
   BASE
=========================================================== */
QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {COLOR_BG_DARK};
}}

/* ===========================================================
   BARRA DE MENÚ
=========================================================== */
QMenuBar {{
    background-color: {COLOR_BG_MEDIUM};
    color: {COLOR_TEXT_PRIMARY};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 2px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 3px;
}}
QMenuBar::item:selected {{
    background-color: #2A3C66;
    color: #D7FDF6;
}}
QMenu {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 2px;
}}
QMenu::item:selected {{
    background-color: #2A3C66;
    color: #D7FDF6;
}}
QMenu::separator {{
    height: 1px;
    background-color: {COLOR_BORDER};
    margin: 4px 8px;
}}

/* ===========================================================
   TOOLBAR
=========================================================== */
QToolBar {{
    background-color: {COLOR_BG_MEDIUM};
    border-bottom: 1px solid {COLOR_BORDER};
    spacing: 4px;
    padding: 4px;
}}
QToolButton {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}}
QToolButton:hover {{
    background-color: #23345D;
    border-color: {COLOR_ACCENT_BLUE_DARK};
}}
QToolButton:pressed {{
    background-color: {COLOR_ACCENT_BLUE};
}}

/* ===========================================================
   BOTONES
=========================================================== */
QPushButton {{
    background-color: {COLOR_BG_LIGHT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 30px;
}}
QPushButton:hover {{
    background-color: #243A68;
    border-color: {COLOR_ACCENT_BLUE_DARK};
}}
QPushButton:pressed {{
    background-color: {COLOR_ACCENT_BLUE_DARK};
}}
QPushButton:disabled {{
    background-color: {COLOR_BG_MEDIUM};
    color: #556677;
    border-color: #2a3a4a;
}}

QPushButton#btn_primary {{
    background-color: {COLOR_ACCENT_BLUE};
    border-color: {COLOR_ACCENT_BLUE_DARK};
    color: #06231F;
    font-weight: 700;
}}
QPushButton#btn_primary:hover {{
    background-color: #99F6E4;
}}

QPushButton#btn_success {{
    background-color: #166534;
    border-color: #22C55E;
}}
QPushButton#btn_success:hover {{
    background-color: #22C55E;
    color: #06220F;
}}

QPushButton#btn_danger {{
    background-color: #9F1239;
    border-color: {COLOR_DANGER};
}}
QPushButton#btn_danger:hover {{
    background-color: {COLOR_DANGER};
}}

QPushButton#btn_warning {{
    background-color: #B45309;
    border-color: {COLOR_WARNING};
    color: #FFF8EB;
}}

/* ===========================================================
   INPUTS
=========================================================== */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox,
QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {COLOR_BG_MEDIUM};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {COLOR_ACCENT_BLUE};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
QTimeEdit:focus, QDateTimeEdit:focus {{
    border-color: {COLOR_ACCENT_BLUE};
}}
QLineEdit:read-only {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_SECONDARY};
}}

QComboBox {{
    background-color: {COLOR_BG_MEDIUM};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 8px;
    min-height: 28px;
}}
QComboBox:hover {{
    border-color: {COLOR_ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_ACCENT_BLUE};
    outline: none;
}}

/* ===========================================================
   TABLAS
=========================================================== */
QTableWidget, QTableView {{
    background-color: {COLOR_BG_MEDIUM};
    color: {COLOR_TEXT_PRIMARY};
    gridline-color: {COLOR_BORDER};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    selection-background-color: {COLOR_ACCENT_BLUE};
    alternate-background-color: {COLOR_BG_LIGHT};
}}
QTableWidget::item {{
    padding: 6px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {COLOR_ACCENT_BLUE};
    color: white;
}}
QHeaderView::section {{
    background-color: #263965;
    color: {COLOR_TEXT_PRIMARY};
    border: none;
    border-right: 1px solid {COLOR_BORDER};
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 8px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QHeaderView::section:hover {{
    background-color: #35508B;
}}

/* ===========================================================
   TABS
=========================================================== */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_BG_MEDIUM};
    border-radius: 4px;
}}
QTabBar::tab {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-radius: 4px 4px 0 0;
}}
QTabBar::tab:selected {{
    background-color: {COLOR_BG_MEDIUM};
    color: {COLOR_TEXT_PRIMARY};
    border-bottom: 2px solid #8B5CF6;
}}
QTabBar::tab:hover {{
    background-color: {COLOR_BG_LIGHT};
    color: {COLOR_TEXT_PRIMARY};
}}

/* ===========================================================
   SCROLL
=========================================================== */
QScrollBar:vertical {{
    background-color: {COLOR_BG_DARK};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #8B5CF6;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {COLOR_BG_DARK};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLOR_BORDER};
    border-radius: 5px;
    min-width: 30px;
}}

/* ===========================================================
   LABELS ESPECIALES
=========================================================== */
QLabel#label_titulo {{
    font-size: 22px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
    letter-spacing: 1px;
}}
QLabel#label_subtitulo {{
    font-size: 13px;
    color: {COLOR_TEXT_SECONDARY};
    letter-spacing: 0.5px;
}}
QLabel#kpi_valor {{
    font-size: 28px;
    font-weight: 700;
    color: #A78BFA;
}}
QLabel#kpi_titulo {{
    font-size: 11px;
    color: {COLOR_TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ===========================================================
   CARDS KPI
=========================================================== */
QFrame#card_kpi {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 12px;
}}
QFrame#card_kpi_success {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_SUCCESS};
    border-radius: 12px;
    border-left: 4px solid {COLOR_SUCCESS};
}}
QFrame#card_kpi_warning {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_WARNING};
    border-radius: 12px;
    border-left: 4px solid {COLOR_WARNING};
}}
QFrame#card_kpi_danger {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_DANGER};
    border-radius: 12px;
    border-left: 4px solid {COLOR_DANGER};
}}
QFrame#card_kpi_info {{
    background-color: {COLOR_BG_PANEL};
    border: 1px solid {COLOR_ACCENT_BLUE};
    border-radius: 12px;
    border-left: 4px solid {COLOR_ACCENT_BLUE};
}}

/* ===========================================================
   BARRA DE ESTADO
=========================================================== */
QStatusBar {{
    background-color: {COLOR_BG_MEDIUM};
    color: {COLOR_TEXT_SECONDARY};
    border-top: 1px solid {COLOR_BORDER};
    font-size: 12px;
}}

/* ===========================================================
   GROUPBOX
=========================================================== */
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: 600;
    color: {COLOR_TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {COLOR_ACCENT_BLUE};
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ===========================================================
   CHECKBOX / RADIO
=========================================================== */
QCheckBox {{
    spacing: 8px;
    color: {COLOR_TEXT_PRIMARY};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    background-color: {COLOR_BG_MEDIUM};
}}
QCheckBox::indicator:checked {{
    background-color: {COLOR_ACCENT_BLUE};
    border-color: {COLOR_ACCENT_BLUE};
}}

/* ===========================================================
   SPLITTER
=========================================================== */
QSplitter::handle {{
    background-color: {COLOR_BORDER};
}}
QSplitter::handle:hover {{
    background-color: {COLOR_ACCENT_BLUE};
}}

/* ===========================================================
   DIALOG
=========================================================== */
QDialog {{
    background-color: {COLOR_BG_MEDIUM};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
}}

/* ===========================================================
   PROGRESS BAR
=========================================================== */
QProgressBar {{
    background-color: {COLOR_BG_DARK};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    text-align: center;
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {COLOR_ACCENT_BLUE};
    border-radius: 3px;
}}

/* ===========================================================
   BADGE / ESTADO COLORES (vía objectName)
=========================================================== */
QLabel#badge_activo, QLabel#badge_cerrada {{
    background-color: #1B5E20;
    color: #A5D6A7;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#badge_proceso, QLabel#badge_liberada {{
    background-color: #0D47A1;
    color: #90CAF9;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#badge_vencida, QLabel#badge_critico {{
    background-color: #B71C1C;
    color: #FFCDD2;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#badge_advertencia, QLabel#badge_proximo {{
    background-color: #E65100;
    color: #FFE0B2;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}
"""

# Colores para filas de tabla según estado
COLORES_ESTADO_TABLA = {
    "Cerrada":   ("#1B5E20", "#E8F5E9"),   # verde oscuro / verde claro
    "Activo":    ("#1B5E20", "#E8F5E9"),
    "En proceso": ("#0D47A1", "#E3F2FD"),  # azul
    "Liberada":  ("#0D47A1", "#E3F2FD"),
    "Vencida":   ("#B71C1C", "#FFEBEE"),   # rojo
    "Dado de baja": ("#B71C1C", "#FFEBEE"),
    "Programada": ("#1a2332", "#E3F2FD"),  # neutro
    "Borrador":  ("#263238", "#ECEFF1"),
    "Anulada":   ("#37474F", "#ECEFF1"),
    "Pausado":   ("#4A148C", "#F3E5F5"),
}

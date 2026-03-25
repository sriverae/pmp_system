# Software PMP — Versión 5.0
## Programa de Mantenimiento Planificado

Aplicación de escritorio para gestión integral de mantenimiento industrial.
Desarrollada en Python 3.12 + PySide6 + SQLite/SQLAlchemy.

---

## Requisitos del sistema

| Componente | Mínimo |
|------------|--------|
| Python     | 3.10+  |
| RAM        | 4 GB   |
| Disco      | 500 MB |
| OS         | Windows 10/11, macOS 12+, Ubuntu 20.04+ |

---

## Instalación

### 1. Clonar / descomprimir el proyecto

```bash
cd pmp_system
```

### 2. Crear entorno virtual (recomendado)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Las dependencias principales son:
- `PySide6` — Interfaz gráfica
- `SQLAlchemy` — ORM / base de datos
- `pandas` — Exportación Excel
- `openpyxl` — Lectura/escritura Excel
- `matplotlib` — Gráficos en dashboard y KPIs
- `reportlab` — Generación de PDFs
- `scipy`, `numpy` — Cálculos RAM (opcional)
- `Pillow` — Procesamiento de imágenes

---

## Ejecución

```bash
python main.py
```

### Credenciales iniciales

| Campo | Valor |
|-------|-------|
| Usuario | `admin` |
| Contraseña | `admin123` |

**⚠ Cambie la contraseña del administrador en su primer acceso.**

---

## Configuración de la base de datos

Por defecto la BD se crea en `pmp_data.db` en el directorio del proyecto.

Para usar otra ubicación:
1. En la pantalla de login, haga clic en **"Configurar base de datos..."**
2. Seleccione o cree un archivo `.db`
3. La configuración se guarda en `config.ini`

---

## Estructura del proyecto

```
pmp_system/
├── main.py                    # Punto de entrada
├── requirements.txt
├── config.ini                 # Configuración (se crea automáticamente)
├── pmp_data.db                # Base de datos SQLite (se crea al iniciar)
├── backups/                   # Respaldos automáticos
├── logs/                      # Logs de errores
├── assets/
│   └── adjuntos/              # Archivos adjuntos a registros
└── app/
    ├── core/
    │   ├── database.py        # Engine SQLAlchemy, inicialización
    │   ├── session.py         # Sesión de usuario activo
    │   └── config_manager.py  # Lector/escritor config.ini
    ├── models/                # Modelos SQLAlchemy (tablas)
    ├── services/              # Lógica de negocio
    ├── validators/            # Restricciones de negocio
    └── views/                 # Interfaz gráfica (PySide6)
        ├── login/
        ├── main_window.py
        ├── dashboard/
        ├── equipos/
        ├── materiales/
        ├── rrhh/
        ├── planes/
        ├── ordenes/
        ├── kpis/
        ├── reportes/
        ├── auditoria/
        ├── configuracion/
        └── backup/
```

---

## Módulos disponibles

| Módulo | Descripción |
|--------|-------------|
| Dashboard | KPIs en tiempo real, alertas, gráficos |
| Equipos | Registro, lecturas de contador, historial, adjuntos |
| Materiales | Stock, movimientos, alertas mínimos, ajustes |
| RRHH | Personal, turnos, ausencias, vacaciones |
| Planes | Planes de mantenimiento preventivo/predictivo |
| Órdenes de Trabajo | Crear, liberar, iniciar, cerrar, anular OTs |
| KPIs | MTTR, MTBF, Disponibilidad, % Preventivo |
| Reportes | PDF y Excel: KPIs, OTs, inventario |
| Auditoría | Registro de todos los eventos del sistema |
| Configuración | Parámetros generales, empresa, seguridad |
| Backup | Copias de seguridad y restauración |

---

## Roles y permisos

| Rol | Permisos |
|-----|----------|
| Administrador | Acceso total, gestión de usuarios, restaurar backup |
| Jefe de Mantenimiento | OTs, KPIs, costos, reportes |
| Planificador | Planes, generar OTs, recursos |
| Técnico | Ver OTs asignadas, cerrar OT propia |
| Consulta | Solo lectura |

---

## Restricciones de negocio implementadas

1. Técnico no puede estar en 2 OTs en el mismo horario
2. Equipo no puede tener 2 OTs simultáneas
3. Personal fuera de turno requiere autorización
4. Trabajador inactivo/vacaciones/suspendido no asignable
5. Máximo horas diarias por técnico configurable
6. Stock de materiales obligatorios verificado al liberar
7. Equipo dado de baja no recibe OTs
8. OT cerrada no editable
9. OT anulada excluida de KPIs
10. Registros con historial no se eliminan físicamente

---

## Empaquetar como ejecutable (PyInstaller)

```bash
pip install pyinstaller

# Windows
pyinstaller --onefile --windowed --name "SoftwarePMP" ^
    --add-data "assets;assets" ^
    --add-data "config.ini;." ^
    main.py

# Linux / macOS
pyinstaller --onefile --windowed --name "SoftwarePMP" \
    --add-data "assets:assets" \
    main.py
```

El ejecutable quedará en `dist/SoftwarePMP.exe` (Windows) o `dist/SoftwarePMP` (Linux/macOS).

---

## Solución de problemas

### Error: "No module named 'PySide6'"
```bash
pip install PySide6
```

### Error al iniciar: "unable to open database file"
Verifique que tiene permisos de escritura en el directorio del proyecto.

### Los gráficos no aparecen
```bash
pip install matplotlib
```

### Error al exportar PDF
```bash
pip install reportlab
```

---

## Changelog v5.0

- Arquitectura MVC/MVVM completa
- Motor SQLAlchemy con FK enforcement
- 10 restricciones de negocio validadas
- Dashboard con KPIs en tiempo real
- Generación automática de OTs desde planes
- Auditoría completa de todos los eventos
- Exportación PDF y Excel
- Sistema de backup/restauración
- Soporte multi-usuario con roles y permisos

---

*Software PMP v5.0 — Desarrollado con Python 3.12 + PySide6 + SQLite*

"""
Servicio de importación masiva desde Excel.
Soporta: equipos, rrhh (trabajadores), materiales, planes y ots.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Tuple

import pandas as pd

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.equipo import Equipo
from app.models.material import Material
from app.models.orden_trabajo import OrdenTrabajo
from app.models.plan import PlanMantenimiento
from app.models.trabajador import Trabajador


@dataclass
class ResultadoImportacion:
    insertados: int = 0
    actualizados: int = 0
    omitidos: int = 0
    errores: int = 0
    detalle_errores: List[str] = None

    def __post_init__(self):
        if self.detalle_errores is None:
            self.detalle_errores = []


class BulkImportService:
    PLANTILLAS: Dict[str, List[str]] = {
        "equipos": [
            "codigo", "nombre", "descripcion", "ubicacion", "area", "centro_costo",
            "marca", "modelo", "serie", "fabricante", "criticidad", "tipo_contador",
            "lectura_inicial", "lectura_actual", "estado", "costo_reposicion", "observaciones",
        ],
        "rrhh": [
            "codigo", "nombres", "apellidos", "dni", "cargo", "especialidad", "turno",
            "empresa", "horas_max_dia", "tarifa_hora", "estado", "fecha_ingreso", "observaciones",
        ],
        "materiales": [
            "codigo", "descripcion", "categoria", "unidad", "stock_actual", "stock_minimo",
            "costo_unitario", "proveedor", "ubicacion_almacen", "estado", "criticidad", "observaciones",
        ],
        "planes": [
            "codigo", "equipo_codigo", "descripcion", "tipo_mantenimiento", "frecuencia",
            "unidad_frecuencia", "criterio", "duracion_estimada", "prioridad", "criticidad",
            "alerta_dias_anticipacion", "estado", "proxima_ejecucion", "procedimiento",
        ],
        "ots": [
            "numero", "equipo_codigo", "tipo_ot", "estado", "prioridad", "criticidad",
            "fecha_programada", "hora_inicio_prog", "hora_fin_prog", "duracion_estimada",
            "responsable_codigo", "descripcion_trabajo",
        ],
    }

    @staticmethod
    def exportar_plantilla(modulo: str, ruta_salida: str) -> Tuple[bool, str]:
        modulo = modulo.lower().strip()
        if modulo not in BulkImportService.PLANTILLAS:
            return False, f"Módulo no soportado: {modulo}"
        cols = BulkImportService.PLANTILLAS[modulo]
        df = pd.DataFrame(columns=cols)
        df.to_excel(ruta_salida, index=False)
        return True, f"Plantilla creada: {ruta_salida}"

    @staticmethod
    def importar_excel(modulo: str, ruta_excel: str) -> Tuple[bool, ResultadoImportacion]:
        modulo = modulo.lower().strip()
        if modulo not in BulkImportService.PLANTILLAS:
            r = ResultadoImportacion(errores=1, detalle_errores=[f"Módulo no soportado: {modulo}"])
            return False, r

        df = pd.read_excel(ruta_excel)
        df.columns = [str(c).strip() for c in df.columns]
        resultado = ResultadoImportacion()
        session = get_session()
        try:
            handlers: Dict[str, Callable] = {
                "equipos": BulkImportService._upsert_equipo,
                "rrhh": BulkImportService._upsert_trabajador,
                "materiales": BulkImportService._upsert_material,
                "planes": BulkImportService._upsert_plan,
                "ots": BulkImportService._upsert_ot,
            }
            handler = handlers[modulo]
            for idx, row in df.iterrows():
                try:
                    accion = handler(session, row.to_dict())
                    if accion == "insertado":
                        resultado.insertados += 1
                    elif accion == "actualizado":
                        resultado.actualizados += 1
                    else:
                        resultado.omitidos += 1
                except Exception as e:
                    resultado.errores += 1
                    resultado.detalle_errores.append(f"Fila {idx + 2}: {e}")
            session.commit()
            return resultado.errores == 0, resultado
        except Exception as e:
            session.rollback()
            resultado.errores += 1
            resultado.detalle_errores.append(str(e))
            return False, resultado
        finally:
            session.close()

    @staticmethod
    def _valor(data: dict, key: str, default=None):
        v = data.get(key, default)
        if pd.isna(v):
            return default
        return v

    @staticmethod
    def _dt(data: dict, key: str):
        v = BulkImportService._valor(data, key)
        if v in (None, ""):
            return None
        if isinstance(v, datetime):
            return v
        return pd.to_datetime(v).to_pydatetime()

    @staticmethod
    def _upsert_equipo(session, data: dict) -> str:
        codigo = str(BulkImportService._valor(data, "codigo", "")).strip()
        nombre = str(BulkImportService._valor(data, "nombre", "")).strip()
        if not codigo or not nombre:
            raise ValueError("codigo y nombre son obligatorios")
        eq = session.query(Equipo).filter_by(codigo=codigo).first()
        creado = eq is None
        if creado:
            eq = Equipo(codigo=codigo, nombre=nombre)
            session.add(eq)
        eq.nombre = nombre
        eq.descripcion = BulkImportService._valor(data, "descripcion")
        eq.ubicacion = BulkImportService._valor(data, "ubicacion")
        eq.area = BulkImportService._valor(data, "area")
        eq.centro_costo = BulkImportService._valor(data, "centro_costo")
        eq.marca = BulkImportService._valor(data, "marca")
        eq.modelo = BulkImportService._valor(data, "modelo")
        eq.serie = BulkImportService._valor(data, "serie")
        eq.fabricante = BulkImportService._valor(data, "fabricante")
        eq.criticidad = BulkImportService._valor(data, "criticidad", "Media")
        eq.tipo_contador = BulkImportService._valor(data, "tipo_contador")
        eq.lectura_inicial = float(BulkImportService._valor(data, "lectura_inicial", 0) or 0)
        eq.lectura_actual = float(BulkImportService._valor(data, "lectura_actual", 0) or 0)
        eq.estado = BulkImportService._valor(data, "estado", "Activo")
        eq.costo_reposicion = float(BulkImportService._valor(data, "costo_reposicion", 0) or 0)
        eq.observaciones = BulkImportService._valor(data, "observaciones")
        return "insertado" if creado else "actualizado"

    @staticmethod
    def _upsert_trabajador(session, data: dict) -> str:
        codigo = str(BulkImportService._valor(data, "codigo", "")).strip()
        nombres = str(BulkImportService._valor(data, "nombres", "")).strip()
        apellidos = str(BulkImportService._valor(data, "apellidos", "")).strip()
        if not codigo or not nombres or not apellidos:
            raise ValueError("codigo, nombres y apellidos son obligatorios")
        tr = session.query(Trabajador).filter_by(codigo=codigo).first()
        creado = tr is None
        if creado:
            tr = Trabajador(codigo=codigo, nombres=nombres, apellidos=apellidos)
            session.add(tr)
        tr.nombres = nombres
        tr.apellidos = apellidos
        tr.dni = BulkImportService._valor(data, "dni")
        tr.cargo = BulkImportService._valor(data, "cargo")
        tr.especialidad = BulkImportService._valor(data, "especialidad")
        tr.turno = BulkImportService._valor(data, "turno")
        tr.empresa = BulkImportService._valor(data, "empresa")
        tr.horas_max_dia = float(BulkImportService._valor(data, "horas_max_dia", 8) or 8)
        tr.tarifa_hora = float(BulkImportService._valor(data, "tarifa_hora", 0) or 0)
        tr.estado = BulkImportService._valor(data, "estado", "Activo")
        tr.observaciones = BulkImportService._valor(data, "observaciones")
        fi = BulkImportService._valor(data, "fecha_ingreso")
        tr.fecha_ingreso = pd.to_datetime(fi).date() if fi not in (None, "") else None
        return "insertado" if creado else "actualizado"

    @staticmethod
    def _upsert_material(session, data: dict) -> str:
        codigo = str(BulkImportService._valor(data, "codigo", "")).strip()
        descripcion = str(BulkImportService._valor(data, "descripcion", "")).strip()
        if not codigo or not descripcion:
            raise ValueError("codigo y descripcion son obligatorios")
        mat = session.query(Material).filter_by(codigo=codigo).first()
        creado = mat is None
        if creado:
            mat = Material(codigo=codigo, descripcion=descripcion)
            session.add(mat)
        mat.descripcion = descripcion
        mat.categoria = BulkImportService._valor(data, "categoria")
        mat.unidad = BulkImportService._valor(data, "unidad", "UN")
        mat.stock_actual = float(BulkImportService._valor(data, "stock_actual", 0) or 0)
        mat.stock_minimo = float(BulkImportService._valor(data, "stock_minimo", 0) or 0)
        mat.costo_unitario = float(BulkImportService._valor(data, "costo_unitario", 0) or 0)
        mat.proveedor = BulkImportService._valor(data, "proveedor")
        mat.ubicacion_almacen = BulkImportService._valor(data, "ubicacion_almacen")
        mat.estado = BulkImportService._valor(data, "estado", "Activo")
        mat.criticidad = BulkImportService._valor(data, "criticidad", "Normal")
        mat.observaciones = BulkImportService._valor(data, "observaciones")
        return "insertado" if creado else "actualizado"

    @staticmethod
    def _upsert_plan(session, data: dict) -> str:
        codigo = str(BulkImportService._valor(data, "codigo", "")).strip()
        equipo_codigo = str(BulkImportService._valor(data, "equipo_codigo", "")).strip()
        if not codigo or not equipo_codigo:
            raise ValueError("codigo y equipo_codigo son obligatorios")
        equipo = session.query(Equipo).filter_by(codigo=equipo_codigo).first()
        if not equipo:
            raise ValueError(f"equipo_codigo '{equipo_codigo}' no existe")
        plan = session.query(PlanMantenimiento).filter_by(codigo=codigo).first()
        creado = plan is None
        if creado:
            plan = PlanMantenimiento(codigo=codigo, equipo_id=equipo.id, descripcion="-", tipo_mantenimiento="Preventivo",
                                     frecuencia=30, unidad_frecuencia="Dias")
            session.add(plan)
        plan.equipo_id = equipo.id
        plan.descripcion = BulkImportService._valor(data, "descripcion", "-")
        plan.tipo_mantenimiento = BulkImportService._valor(data, "tipo_mantenimiento", "Preventivo")
        plan.frecuencia = float(BulkImportService._valor(data, "frecuencia", 30) or 30)
        plan.unidad_frecuencia = BulkImportService._valor(data, "unidad_frecuencia", "Dias")
        plan.criterio = BulkImportService._valor(data, "criterio", "Fecha")
        plan.duracion_estimada = float(BulkImportService._valor(data, "duracion_estimada", 1) or 1)
        plan.prioridad = BulkImportService._valor(data, "prioridad", "Normal")
        plan.criticidad = BulkImportService._valor(data, "criticidad", "Media")
        plan.alerta_dias_anticipacion = int(BulkImportService._valor(data, "alerta_dias_anticipacion", 7) or 7)
        plan.estado = BulkImportService._valor(data, "estado", "Activo")
        plan.proxima_ejecucion = BulkImportService._dt(data, "proxima_ejecucion") or plan.calcular_proxima_ejecucion()
        plan.procedimiento = BulkImportService._valor(data, "procedimiento")
        if creado:
            plan.creado_por = session_usuario.usuario_id
        return "insertado" if creado else "actualizado"

    @staticmethod
    def _upsert_ot(session, data: dict) -> str:
        numero = str(BulkImportService._valor(data, "numero", "")).strip()
        equipo_codigo = str(BulkImportService._valor(data, "equipo_codigo", "")).strip()
        if not numero or not equipo_codigo:
            raise ValueError("numero y equipo_codigo son obligatorios")
        equipo = session.query(Equipo).filter_by(codigo=equipo_codigo).first()
        if not equipo:
            raise ValueError(f"equipo_codigo '{equipo_codigo}' no existe")
        responsable_codigo = str(BulkImportService._valor(data, "responsable_codigo", "")).strip()
        responsable_id = None
        if responsable_codigo:
            trab = session.query(Trabajador).filter_by(codigo=responsable_codigo).first()
            if not trab:
                raise ValueError(f"responsable_codigo '{responsable_codigo}' no existe")
            responsable_id = trab.id

        ot = session.query(OrdenTrabajo).filter_by(numero=numero).first()
        creado = ot is None
        if creado:
            ot = OrdenTrabajo(numero=numero, tipo_ot="Preventivo", equipo_id=equipo.id)
            session.add(ot)
        ot.equipo_id = equipo.id
        ot.tipo_ot = BulkImportService._valor(data, "tipo_ot", "Preventivo")
        ot.estado = BulkImportService._valor(data, "estado", "Programada")
        ot.prioridad = BulkImportService._valor(data, "prioridad", "Normal")
        ot.criticidad = BulkImportService._valor(data, "criticidad", "Media")
        ot.fecha_programada = BulkImportService._dt(data, "fecha_programada")
        ot.hora_inicio_prog = BulkImportService._valor(data, "hora_inicio_prog")
        ot.hora_fin_prog = BulkImportService._valor(data, "hora_fin_prog")
        ot.duracion_estimada = float(BulkImportService._valor(data, "duracion_estimada", 1) or 1)
        ot.responsable_id = responsable_id
        ot.descripcion_trabajo = BulkImportService._valor(data, "descripcion_trabajo")
        if creado:
            ot.creado_por = session_usuario.usuario_id
        return "insertado" if creado else "actualizado"

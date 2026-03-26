"""
Carga de datos demo para pruebas rápidas funcionales.
"""
from datetime import datetime, timedelta

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.equipo import Equipo
from app.models.material import Material
from app.models.orden_trabajo import OrdenTrabajo
from app.models.plan import PlanMantenimiento
from app.models.trabajador import Trabajador


class DemoDataService:
    @staticmethod
    def cargar_datos_demo():
        session = get_session()
        try:
            # Equipos
            equipos_seed = [
                ("EQ-DEMO-01", "Compresor Principal", "Horas"),
                ("EQ-DEMO-02", "Bomba de Agua", "Horas"),
                ("EQ-DEMO-03", "Montacarga Planta", "Kilometros"),
                ("EQ-DEMO-04", "Secador Línea 1", "Horas"),
            ]
            equipos = {}
            for codigo, nombre, tipo_cont in equipos_seed:
                e = session.query(Equipo).filter_by(codigo=codigo).first()
                if not e:
                    e = Equipo(
                        codigo=codigo, nombre=nombre, tipo_contador=tipo_cont,
                        criticidad="Alta", estado="Activo", lectura_actual=120.0
                    )
                    session.add(e)
                    session.flush()
                equipos[codigo] = e

            # Trabajadores
            trab_seed = [
                ("TR-DEMO-01", "Carlos", "Mendoza", "Mecánico"),
                ("TR-DEMO-02", "Rosa", "Vega", "Electricista"),
                ("TR-DEMO-03", "Luis", "Pérez", "Supervisor"),
            ]
            trabajadores = {}
            for codigo, nom, ape, cargo in trab_seed:
                t = session.query(Trabajador).filter_by(codigo=codigo).first()
                if not t:
                    t = Trabajador(
                        codigo=codigo, nombres=nom, apellidos=ape,
                        cargo=cargo, estado="Activo", horas_max_dia=8
                    )
                    session.add(t)
                    session.flush()
                trabajadores[codigo] = t

            # Materiales
            mat_seed = [
                ("MAT-DEMO-01", "Filtro de aceite", 25),
                ("MAT-DEMO-02", "Lubricante ISO 68", 80),
                ("MAT-DEMO-03", "Rodamiento 6205", 40),
            ]
            for codigo, desc, stock in mat_seed:
                m = session.query(Material).filter_by(codigo=codigo).first()
                if not m:
                    m = Material(
                        codigo=codigo, descripcion=desc, unidad="UND",
                        stock_actual=stock, stock_minimo=10, estado="Activo",
                        costo_unitario=35
                    )
                    session.add(m)

            session.flush()

            # Planes
            planes_seed = [
                ("PM-DEMO-01", "EQ-DEMO-01", "Inspección general compresor", "Preventivo", 30),
                ("PM-DEMO-02", "EQ-DEMO-02", "Cambio sello mecánico", "Preventivo", 60),
                ("PM-DEMO-03", "EQ-DEMO-03", "Revisión de seguridad", "Inspeccion", 15),
            ]
            planes = {}
            for cod, eq_cod, desc, tipo, freq in planes_seed:
                p = session.query(PlanMantenimiento).filter_by(codigo=cod).first()
                if not p:
                    p = PlanMantenimiento(
                        codigo=cod,
                        equipo_id=equipos[eq_cod].id,
                        descripcion=desc,
                        tipo_mantenimiento=tipo,
                        frecuencia=float(freq),
                        unidad_frecuencia="Dias",
                        criterio="Fecha",
                        prioridad="Alta",
                        criticidad="Media",
                        responsable_id=trabajadores["TR-DEMO-03"].id,
                        estado="Activo",
                        proxima_ejecucion=datetime.now() + timedelta(days=freq // 2),
                        alerta_dias_anticipacion=7,
                        creado_por=session_usuario.usuario_id
                    )
                    session.add(p)
                    session.flush()
                planes[cod] = p

            # OTs
            ot_seed = [
                ("OT-DEMO-0001", "PM-DEMO-01", "Programada", 2),
                ("OT-DEMO-0002", "PM-DEMO-02", "Liberada", 4),
                ("OT-DEMO-0003", "PM-DEMO-03", "En proceso", 0),
            ]
            for numero, plan_cod, estado, dias in ot_seed:
                ot = session.query(OrdenTrabajo).filter_by(numero=numero).first()
                p = planes[plan_cod]
                if not ot:
                    ot = OrdenTrabajo(
                        numero=numero,
                        tipo_ot=p.tipo_mantenimiento,
                        equipo_id=p.equipo_id,
                        plan_id=p.id,
                        prioridad=p.prioridad,
                        criticidad=p.criticidad,
                        estado=estado,
                        fecha_programada=datetime.now() + timedelta(days=dias),
                        responsable_id=p.responsable_id,
                        descripcion_trabajo=p.descripcion,
                        creado_por=session_usuario.usuario_id
                    )
                    session.add(ot)

            session.commit()
            return True, "Datos demo cargados correctamente (equipos, RRHH, materiales, planes y OTs)."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

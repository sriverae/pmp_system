"""
Servicio de Auditoría.
Toda acción importante pasa por aquí para registrarse.
"""
from datetime import datetime
from app.core.database import get_session
from app.models.auditoria import Auditoria
from app.core.session import session_usuario
import json


class AuditoriaService:

    @staticmethod
    def registrar(modulo: str, accion: str, tabla: str = None,
                  registro_id: int = None, valor_anterior=None,
                  valor_nuevo=None, observacion: str = None):
        """
        Registra un evento de auditoría.

        Args:
            modulo: Nombre del módulo (ej: 'Login', 'OT', 'Equipos')
            accion: Descripción de la acción (ej: 'Crear OT', 'Cerrar sesión')
            tabla: Tabla afectada en la BD
            registro_id: ID del registro afectado
            valor_anterior: Valor previo (se serializa a JSON si es dict)
            valor_nuevo: Valor nuevo (se serializa a JSON si es dict)
            observacion: Texto libre adicional
        """
        session = get_session()
        try:
            val_ant = json.dumps(valor_anterior, ensure_ascii=False,
                                  default=str) if valor_anterior else None
            val_nvo = json.dumps(valor_nuevo, ensure_ascii=False,
                                  default=str) if valor_nuevo else None

            entrada = Auditoria(
                usuario_id=session_usuario.usuario_id,
                username=session_usuario.username or "sistema",
                fecha_hora=datetime.now(),
                modulo=modulo,
                accion=accion,
                tabla_afectada=tabla,
                registro_id=registro_id,
                valor_anterior=val_ant,
                valor_nuevo=val_nvo,
                observacion=observacion
            )
            session.add(entrada)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"[AuditoriaService] Error registrando: {e}")
        finally:
            session.close()

    @staticmethod
    def obtener_registros(desde=None, hasta=None, modulo=None,
                          usuario=None, limit=500):
        """Consulta registros de auditoría con filtros opcionales."""
        session = get_session()
        try:
            q = session.query(Auditoria)
            if desde:
                q = q.filter(Auditoria.fecha_hora >= desde)
            if hasta:
                q = q.filter(Auditoria.fecha_hora <= hasta)
            if modulo:
                q = q.filter(Auditoria.modulo.ilike(f"%{modulo}%"))
            if usuario:
                q = q.filter(Auditoria.username.ilike(f"%{usuario}%"))
            return q.order_by(Auditoria.fecha_hora.desc()).limit(limit).all()
        finally:
            session.close()

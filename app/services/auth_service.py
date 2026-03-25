"""
Servicio de Autenticación.
Gestiona login, logout, bloqueo por intentos y recuperación.
"""
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.usuario import Usuario
from app.models.base import ConfiguracionSistema
from app.services.auditoria_service import AuditoriaService


@dataclass
class ResultadoLogin:
    exitoso: bool
    mensaje: str
    bloqueado: bool = False
    segundos_restantes: int = 0


class AuthService:

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _get_config_int(session, clave: str, defecto: int) -> int:
        cfg = session.query(ConfiguracionSistema).filter_by(clave=clave).first()
        if cfg and cfg.valor:
            try:
                return int(cfg.valor)
            except ValueError:
                pass
        return defecto

    @staticmethod
    def login(username: str, password: str) -> ResultadoLogin:
        """
        Intenta autenticar al usuario.

        Reglas:
        - Usuario debe existir y estar activo
        - Contraseña no puede estar vacía
        - Si supera max_intentos_fallidos, bloquear por minutos_bloqueo minutos
        - Registrar en auditoría
        """
        if not username or not password:
            return ResultadoLogin(exitoso=False, mensaje="Usuario y contraseña son obligatorios.")

        session = get_session()
        try:
            usuario = session.query(Usuario).filter_by(username=username).first()

            if not usuario:
                AuditoriaService.registrar(
                    "Login", "Intento fallido - usuario no existe",
                    observacion=f"Username: {username}"
                )
                return ResultadoLogin(exitoso=False,
                                      mensaje="Usuario o contraseña incorrectos.")

            if not usuario.activo:
                return ResultadoLogin(exitoso=False,
                                      mensaje="El usuario está inactivo. Contacte al administrador.")

            # Verificar bloqueo temporal
            if usuario.bloqueado_hasta and usuario.bloqueado_hasta > datetime.now():
                segundos = int((usuario.bloqueado_hasta - datetime.now()).total_seconds())
                return ResultadoLogin(
                    exitoso=False,
                    bloqueado=True,
                    segundos_restantes=segundos,
                    mensaje=f"Cuenta bloqueada. Intente en {segundos // 60}m {segundos % 60}s."
                )

            max_intentos = AuthService._get_config_int(session, "max_intentos_login", 3)
            minutos_bloqueo = AuthService._get_config_int(session, "minutos_bloqueo", 5)

            # Verificar contraseña
            hash_ingresado = AuthService._hash_password(password)
            if usuario.password_hash != hash_ingresado:
                usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1

                if usuario.intentos_fallidos >= max_intentos:
                    usuario.bloqueado_hasta = datetime.now() + timedelta(minutes=minutos_bloqueo)
                    session.commit()
                    AuditoriaService.registrar(
                        "Login", "Cuenta bloqueada por intentos fallidos",
                        observacion=f"Username: {username}"
                    )
                    return ResultadoLogin(
                        exitoso=False,
                        bloqueado=True,
                        segundos_restantes=minutos_bloqueo * 60,
                        mensaje=f"Demasiados intentos fallidos. Cuenta bloqueada por {minutos_bloqueo} minutos."
                    )

                session.commit()
                AuditoriaService.registrar(
                    "Login", "Intento fallido - contraseña incorrecta",
                    registro_id=usuario.id, observacion=f"Intento #{usuario.intentos_fallidos}"
                )
                restantes = max_intentos - usuario.intentos_fallidos
                return ResultadoLogin(
                    exitoso=False,
                    mensaje=f"Contraseña incorrecta. Intentos restantes: {restantes}"
                )

            # Login exitoso
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.ultimo_login = datetime.now()
            session.commit()

            # Cargar rol
            rol_nombre = usuario.rol.nombre if usuario.rol else "Consulta"

            # Iniciar sesión global
            session_usuario.iniciar(
                usuario_id=usuario.id,
                username=usuario.username,
                nombre=usuario.nombre_completo,
                rol=rol_nombre,
                rol_id=usuario.rol_id
            )

            AuditoriaService.registrar(
                "Login", "Ingreso exitoso",
                registro_id=usuario.id,
                observacion=f"Rol: {rol_nombre}"
            )

            return ResultadoLogin(exitoso=True, mensaje=f"Bienvenido, {usuario.nombre_completo}.")

        except Exception as e:
            session.rollback()
            return ResultadoLogin(exitoso=False, mensaje=f"Error del sistema: {str(e)}")
        finally:
            session.close()

    @staticmethod
    def logout():
        """Cierra la sesión activa y registra en auditoría."""
        AuditoriaService.registrar("Login", "Cierre de sesión")
        session_usuario.cerrar()

    @staticmethod
    def cambiar_password(usuario_id: int, password_actual: str,
                         password_nueva: str) -> tuple[bool, str]:
        """Cambia la contraseña del usuario autenticado."""
        if not password_nueva or len(password_nueva) < 6:
            return False, "La nueva contraseña debe tener al menos 6 caracteres."

        session = get_session()
        try:
            usuario = session.query(Usuario).get(usuario_id)
            if not usuario:
                return False, "Usuario no encontrado."

            if usuario.password_hash != AuthService._hash_password(password_actual):
                return False, "La contraseña actual es incorrecta."

            usuario.password_hash = AuthService._hash_password(password_nueva)
            session.commit()

            AuditoriaService.registrar("Usuarios", "Cambio de contraseña",
                                        registro_id=usuario_id)
            return True, "Contraseña actualizada correctamente."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

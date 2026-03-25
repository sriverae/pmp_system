"""
Gestión de la sesión del usuario activo.
Patrón Singleton para acceso global.
"""
from datetime import datetime
from typing import Optional


class UserSession:
    """Almacena el usuario logueado y su rol durante la sesión activa."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._reset()
        return cls._instance

    def _reset(self):
        self.usuario_id: Optional[int] = None
        self.username: str = ""
        self.nombre_completo: str = ""
        self.rol: str = ""
        self.rol_id: Optional[int] = None
        self.login_time: Optional[datetime] = None
        self.activo: bool = False

    def iniciar(self, usuario_id: int, username: str, nombre: str,
                rol: str, rol_id: int):
        self.usuario_id = usuario_id
        self.username = username
        self.nombre_completo = nombre
        self.rol = rol
        self.rol_id = rol_id
        self.login_time = datetime.now()
        self.activo = True

    def cerrar(self):
        self._reset()

    def is_admin(self) -> bool:
        return self.rol == "Administrador"

    def is_jefe(self) -> bool:
        return self.rol in ("Administrador", "Jefe de Mantenimiento")

    def is_planificador(self) -> bool:
        return self.rol in ("Administrador", "Jefe de Mantenimiento", "Planificador")

    def is_tecnico(self) -> bool:
        return self.rol in ("Administrador", "Jefe de Mantenimiento",
                            "Planificador", "Técnico")

    def puede(self, accion: str) -> bool:
        """
        Verifica permiso por acción string.
        Acciones: 'crear', 'editar', 'eliminar', 'cerrar_ot',
                  'liberar_ot', 'ver_costos', 'configurar', 'restaurar_backup'
        """
        permisos = {
            "Administrador": {
                "crear", "editar", "eliminar", "cerrar_ot",
                "liberar_ot", "ver_costos", "configurar",
                "restaurar_backup", "ver_auditoria", "gestionar_usuarios"
            },
            "Jefe de Mantenimiento": {
                "crear", "editar", "cerrar_ot", "liberar_ot",
                "ver_costos", "ver_auditoria"
            },
            "Planificador": {
                "crear", "editar", "liberar_ot"
            },
            "Técnico": {
                "cerrar_ot"
            },
            "Consulta": set()
        }
        return accion in permisos.get(self.rol, set())


# Instancia global
session_usuario = UserSession()

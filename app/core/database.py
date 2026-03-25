"""
Gestión del engine y sesión de SQLAlchemy.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.models.base import Base
import os

_engine = None
_SessionFactory = None


def inicializar_base_datos(db_path: str = "pmp_data.db"):
    """Crea el engine, habilita FK en SQLite e inicializa todas las tablas."""
    global _engine, _SessionFactory

    db_url = f"sqlite:///{db_path}"
    _engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})

    # Habilitar claves foráneas en SQLite
    @event.listens_for(_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)

    # Importar todos los modelos para que Base los conozca
    from app.models import (  # noqa: F401
        usuario, equipo, material, trabajador,
        plan, orden_trabajo, historial, auditoria, adjunto
    )

    Base.metadata.create_all(_engine)

    # Insertar datos iniciales si la BD es nueva
    _inicializar_datos_base()


def get_session() -> Session:
    """Retorna una nueva sesión de base de datos."""
    if _SessionFactory is None:
        raise RuntimeError("Base de datos no inicializada. Llame a inicializar_base_datos() primero.")
    return _SessionFactory()


def get_engine():
    return _engine


def _inicializar_datos_base():
    """Inserta registros semilla si no existen."""
    from app.models.usuario import Rol, Usuario, Permiso
    from app.models.base import ConfiguracionSistema

    session = get_session()
    try:
        # Roles base
        if session.query(Rol).count() == 0:
            roles = [
                Rol(nombre="Administrador", descripcion="Acceso total al sistema"),
                Rol(nombre="Jefe de Mantenimiento", descripcion="Gestión de OTs, KPIs y reportes"),
                Rol(nombre="Planificador", descripcion="Planes y programación"),
                Rol(nombre="Técnico", descripcion="Ejecución y cierre de OTs"),
                Rol(nombre="Consulta", descripcion="Solo lectura"),
            ]
            session.add_all(roles)
            session.flush()

        # Usuario admin por defecto
        if session.query(Usuario).count() == 0:
            rol_admin = session.query(Rol).filter_by(nombre="Administrador").first()
            pwd_hash = _hash_password("admin123")
            admin = Usuario(
                username="admin",
                password_hash=pwd_hash,
                nombre="Administrador",
                apellido="Sistema",
                email="admin@pmp.local",
                rol_id=rol_admin.id,
                activo=True
            )
            session.add(admin)

        # Configuraciones iniciales
        if session.query(ConfiguracionSistema).count() == 0:
            configs = [
                ConfiguracionSistema(clave="empresa_nombre", valor="Mi Empresa Industrial",
                                     descripcion="Nombre de la empresa", tipo_dato="str"),
                ConfiguracionSistema(clave="moneda", valor="PEN",
                                     descripcion="Moneda del sistema", tipo_dato="str"),
                ConfiguracionSistema(clave="max_intentos_login", valor="3",
                                     descripcion="Intentos fallidos antes de bloqueo", tipo_dato="int"),
                ConfiguracionSistema(clave="minutos_bloqueo", valor="5",
                                     descripcion="Minutos de bloqueo tras intentos fallidos", tipo_dato="int"),
                ConfiguracionSistema(clave="dias_alerta_preventivo", valor="7",
                                     descripcion="Días de anticipación para alertas", tipo_dato="int"),
            ]
            session.add_all(configs)

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error inicializando datos base: {e}")
    finally:
        session.close()


def _hash_password(password: str) -> str:
    """Hash SHA-256 simple para contraseñas (producción usar bcrypt)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

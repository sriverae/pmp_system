"""
Servicio de Materiales.
Gestiona stock, movimientos y ajustes.
"""
from typing import List, Optional, Tuple
from datetime import datetime

from app.core.database import get_session
from app.core.session import session_usuario
from app.models.material import Material, MovimientoMaterial
from app.services.auditoria_service import AuditoriaService


class MaterialService:

    @staticmethod
    def listar(texto: str = None, categoria: str = None,
               solo_activos: bool = False,
               alerta_stock: bool = False) -> List[Material]:
        session = get_session()
        try:
            q = session.query(Material)
            if solo_activos:
                q = q.filter(Material.estado == "Activo")
            if categoria:
                q = q.filter(Material.categoria == categoria)
            if texto:
                like = f"%{texto}%"
                q = q.filter(
                    (Material.codigo.ilike(like)) |
                    (Material.descripcion.ilike(like))
                )
            mats = q.order_by(Material.codigo).all()
            if alerta_stock:
                mats = [m for m in mats if m.alerta_stock != "normal"]
            return mats
        finally:
            session.close()

    @staticmethod
    def obtener(material_id: int) -> Optional[Material]:
        session = get_session()
        try:
            return session.query(Material).get(material_id)
        finally:
            session.close()

    @staticmethod
    def crear(datos: dict) -> Tuple[bool, str, Optional[int]]:
        if not datos.get("codigo"):
            return False, "El código es obligatorio.", None
        if not datos.get("descripcion"):
            return False, "La descripción es obligatoria.", None
        if float(datos.get("costo_unitario", 0)) < 0:
            return False, "El costo unitario no puede ser negativo.", None

        session = get_session()
        try:
            dup = session.query(Material).filter_by(
                codigo=datos["codigo"]).first()
            if dup:
                return False, f"Ya existe el código '{datos['codigo']}'.", None

            mat = Material(
                codigo=datos["codigo"],
                descripcion=datos["descripcion"],
                categoria=datos.get("categoria"),
                unidad=datos.get("unidad", "UN"),
                stock_actual=float(datos.get("stock_actual", 0)),
                stock_minimo=float(datos.get("stock_minimo", 0)),
                costo_unitario=float(datos.get("costo_unitario", 0)),
                proveedor=datos.get("proveedor"),
                ubicacion_almacen=datos.get("ubicacion_almacen"),
                estado="Activo",
                criticidad=datos.get("criticidad", "Normal"),
                observaciones=datos.get("observaciones")
            )
            session.add(mat)
            session.flush()

            # Si tiene stock inicial, registrar movimiento de entrada
            if mat.stock_actual > 0:
                session.add(MovimientoMaterial(
                    material_id=mat.id,
                    tipo_movimiento="Entrada",
                    cantidad=mat.stock_actual,
                    costo_unitario=mat.costo_unitario,
                    motivo="Stock inicial",
                    usuario_id=session_usuario.usuario_id,
                    stock_anterior=0,
                    stock_posterior=mat.stock_actual
                ))

            session.commit()
            AuditoriaService.registrar(
                "Materiales", "Crear material",
                tabla="materiales", registro_id=mat.id,
                valor_nuevo={"codigo": mat.codigo}
            )
            return True, "Material creado.", mat.id
        except Exception as e:
            session.rollback()
            return False, str(e), None
        finally:
            session.close()

    @staticmethod
    def actualizar(material_id: int, datos: dict) -> Tuple[bool, str]:
        session = get_session()
        try:
            mat = session.query(Material).get(material_id)
            if not mat:
                return False, "Material no encontrado."

            anterior = {"descripcion": mat.descripcion, "stock": mat.stock_actual}
            campos = ["descripcion", "categoria", "unidad", "stock_minimo",
                      "costo_unitario", "proveedor", "ubicacion_almacen",
                      "criticidad", "observaciones"]
            for c in campos:
                if c in datos:
                    setattr(mat, c, datos[c])
            session.commit()
            AuditoriaService.registrar(
                "Materiales", "Editar material",
                tabla="materiales", registro_id=material_id,
                valor_anterior=anterior
            )
            return True, "Material actualizado."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def ajustar_stock(material_id: int, cantidad_nueva: float,
                       motivo: str) -> Tuple[bool, str]:
        """
        Ajuste de inventario.
        RESTRICCIÓN: motivo obligatorio. Registra diferencia en movimientos.
        """
        if not motivo or not motivo.strip():
            return False, "El motivo del ajuste es obligatorio."

        session = get_session()
        try:
            mat = session.query(Material).get(material_id)
            if not mat:
                return False, "Material no encontrado."

            diferencia = cantidad_nueva - mat.stock_actual
            tipo_mov = "Ajuste" if diferencia != 0 else "Ajuste (sin cambio)"
            stock_ant = mat.stock_actual
            mat.stock_actual = cantidad_nueva

            session.add(MovimientoMaterial(
                material_id=material_id,
                tipo_movimiento=tipo_mov,
                cantidad=abs(diferencia),
                costo_unitario=mat.costo_unitario,
                motivo=motivo,
                usuario_id=session_usuario.usuario_id,
                stock_anterior=stock_ant,
                stock_posterior=cantidad_nueva
            ))
            session.commit()

            AuditoriaService.registrar(
                "Materiales", "Ajuste de stock",
                tabla="materiales", registro_id=material_id,
                valor_anterior={"stock": stock_ant},
                valor_nuevo={"stock": cantidad_nueva, "motivo": motivo}
            )
            return True, f"Stock ajustado de {stock_ant} a {cantidad_nueva}."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def desactivar(material_id: int) -> Tuple[bool, str]:
        """
        RESTRICCIÓN: No eliminar si tuvo movimientos. Solo desactivar.
        """
        session = get_session()
        try:
            mat = session.query(Material).get(material_id)
            if not mat:
                return False, "Material no encontrado."

            tiene_movs = session.query(MovimientoMaterial).filter_by(
                material_id=material_id).first()
            if tiene_movs:
                mat.estado = "Inactivo"
                session.commit()
                return True, "Material desactivado (tiene movimientos, no se elimina)."
            else:
                mat.estado = "Inactivo"
                session.commit()
                return True, "Material desactivado."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    @staticmethod
    def obtener_movimientos(material_id: int,
                             limit: int = 100) -> List[MovimientoMaterial]:
        session = get_session()
        try:
            return (session.query(MovimientoMaterial)
                    .filter_by(material_id=material_id)
                    .order_by(MovimientoMaterial.fecha.desc())
                    .limit(limit).all())
        finally:
            session.close()

    @staticmethod
    def obtener_alertas_stock() -> List[Material]:
        """Retorna materiales con stock en alerta (bajo o crítico)."""
        session = get_session()
        try:
            mats = session.query(Material).filter(
                Material.estado == "Activo"
            ).all()
            return [m for m in mats if m.alerta_stock != "normal"]
        finally:
            session.close()

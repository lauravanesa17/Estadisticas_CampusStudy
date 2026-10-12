from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MateriaProyeccion, UsuarioProyeccion
from app.schemas import CatalogoItem, EstadisticasGrupo, EstadisticasMateria, EstadisticasUsuario
from app.services.agregador import estadisticas_grupo, estadisticas_materia, estadisticas_usuario
from app.services.sincronizacion import refrescar_usuario

router = APIRouter(prefix="/api/v1/estadisticas", tags=["estadisticas"])


def _error(codigo: int, mensaje: str, dependencia: str | None = None) -> HTTPException:
    detalle: dict = {"codigo": codigo, "mensaje": mensaje}
    if dependencia:
        detalle["dependencia"] = dependencia
    return HTTPException(status_code=codigo, detail=detalle)


@router.get("/usuario/{usuario_id}", response_model=EstadisticasUsuario, response_model_exclude_none=True)
def reporte_usuario(
    usuario_id: int,
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    materia_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> EstadisticasUsuario:
    if usuario_id <= 0:
        raise _error(400, "Solicitud incorrecta (parámetro inválido, ej. usuario_id no numérico).")

    try:
        refrescar_usuario(db, usuario_id)
    except ConnectionError:
        if not db.get(UsuarioProyeccion, usuario_id):
            raise _error(503, "estadísticas no disponibles por el momento", "usuarios-service") from None

    reporte = estadisticas_usuario(db, usuario_id, periodo=periodo, materia_id=materia_id)
    if not reporte:
        raise _error(404, "Usuario no encontrado.")
    return reporte


@router.get("/materia/{materia_id}", response_model=EstadisticasMateria, response_model_exclude_none=True)
def reporte_materia(
    materia_id: int,
    periodo: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
) -> EstadisticasMateria:
    if materia_id <= 0:
        raise _error(400, "Solicitud incorrecta (parámetro inválido).")
    reporte = estadisticas_materia(db, materia_id, periodo=periodo)
    if not reporte:
        raise _error(404, "Materia no encontrada.")
    return reporte


@router.get("/grupo/{grupo_id}", response_model=EstadisticasGrupo)
def reporte_grupo(grupo_id: int, db: Session = Depends(get_db)) -> EstadisticasGrupo:
    if grupo_id <= 0:
        raise _error(400, "Solicitud incorrecta (parámetro inválido).")
    reporte = estadisticas_grupo(db, grupo_id)
    if not reporte:
        raise _error(404, "Grupo no encontrado.")
    return reporte


@router.get("/catalogo/usuarios", response_model=list[CatalogoItem], include_in_schema=False)
def catalogo_usuarios(db: Session = Depends(get_db)) -> list[CatalogoItem]:
    return [
        CatalogoItem(id=item.id, nombre=item.nombre or str(item.id), extra=item.email)
        for item in db.query(UsuarioProyeccion).all()
    ]


@router.get("/catalogo/materias", response_model=list[CatalogoItem], include_in_schema=False)
def catalogo_materias(db: Session = Depends(get_db)) -> list[CatalogoItem]:
    return [
        CatalogoItem(id=item.id, nombre=item.nombre or str(item.id), extra=item.nrc)
        for item in db.query(MateriaProyeccion).all()
    ]

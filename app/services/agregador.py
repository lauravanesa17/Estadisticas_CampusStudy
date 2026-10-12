from datetime import datetime

from sqlalchemy.orm import Session

from app.models import GrupoProyeccion, MateriaProyeccion, MiembroGrupo, TareaProyeccion, UsuarioProyeccion
from app.schemas import (
    EstadisticasGrupo,
    EstadisticasMateria,
    EstadisticasUsuario,
    GruposResumen,
    MateriaResumen,
    TareasResumen,
)
from app.services.tiempo import ahora, estado_efectivo, hoy_iso


def _tareas(
    db: Session,
    usuario_id: int | None = None,
    materia_id: int | None = None,
    grupo_id: int | None = None,
    periodo: str | None = None,
) -> list[TareaProyeccion]:
    consulta = db.query(TareaProyeccion)
    if usuario_id:
        consulta = consulta.filter(TareaProyeccion.usuario_id == usuario_id)
    if materia_id:
        consulta = consulta.filter(TareaProyeccion.materia_id == materia_id)
    if grupo_id:
        consulta = consulta.filter(TareaProyeccion.grupo_id == grupo_id)
    filas = consulta.all()
    if periodo:
        filas = [
            tarea
            for tarea in filas
            if tarea.fecha_entrega and tarea.fecha_entrega.strftime("%Y-%m") == periodo
        ]
    return filas


def resumen_tareas(tareas: list[TareaProyeccion], momento: datetime | None = None) -> TareasResumen:
    referencia = momento or ahora()
    activas = [tarea for tarea in tareas if estado_efectivo(tarea.estado, tarea.fecha_entrega, referencia) != "cancelada"]
    completadas = 0
    vencidas = 0
    for tarea in activas:
        efectivo = estado_efectivo(tarea.estado, tarea.fecha_entrega, referencia)
        if efectivo == "completada":
            completadas += 1
        elif efectivo == "vencida":
            vencidas += 1
    total = len(activas)
    pendientes = total - completadas - vencidas
    porcentaje = round((completadas / total) * 100, 1) if total else 0.0
    return TareasResumen(
        total=total,
        completadas=completadas,
        pendientes=pendientes,
        vencidas=vencidas,
        porcentaje_completado=porcentaje,
    )


def _grupos_usuario(db: Session, usuario_id: int, tareas: list[TareaProyeccion], momento: datetime) -> GruposResumen:
    ids = {fila.grupo_id for fila in db.query(MiembroGrupo).filter_by(usuario_id=usuario_id).all()}
    ids.update(tarea.grupo_id for tarea in tareas if tarea.grupo_id)
    activos = set()
    for tarea in tareas:
        if not tarea.grupo_id:
            continue
        efectivo = estado_efectivo(tarea.estado, tarea.fecha_entrega, momento)
        if efectivo in {"pendiente", "en_progreso", "vencida"}:
            activos.add(tarea.grupo_id)
    return GruposResumen(total_grupos=len(ids), grupos_activos=len(activos))


def _materias_usuario(db: Session, tareas: list[TareaProyeccion], momento: datetime) -> list[MateriaResumen]:
    agrupadas: dict[int, list[TareaProyeccion]] = {}
    for tarea in tareas:
        if tarea.materia_id:
            agrupadas.setdefault(tarea.materia_id, []).append(tarea)
    resultado: list[MateriaResumen] = []
    for materia_id, items in agrupadas.items():
        materia = db.get(MateriaProyeccion, materia_id)
        conteo = resumen_tareas(items, momento)
        resultado.append(
            MateriaResumen(
                materia_id=materia_id,
                nombre=materia.nombre if materia and materia.nombre else f"Materia {materia_id}",
                tareas_completadas=conteo.completadas,
                tareas_total=conteo.total,
            )
        )
    return sorted(resultado, key=lambda item: item.tareas_total, reverse=True)


def estadisticas_usuario(
    db: Session,
    usuario_id: int,
    periodo: str | None = None,
    materia_id: int | None = None,
) -> EstadisticasUsuario | None:
    usuario = db.get(UsuarioProyeccion, usuario_id)
    if not usuario:
        return None
    momento = ahora()
    tareas = _tareas(db, usuario_id=usuario_id, materia_id=materia_id, periodo=periodo)
    return EstadisticasUsuario(
        usuario_id=usuario_id,
        nombre=usuario.nombre or f"Usuario {usuario_id}",
        periodo=periodo,
        tareas=resumen_tareas(tareas, momento),
        grupos=_grupos_usuario(db, usuario_id, tareas, momento),
        materias=_materias_usuario(db, tareas, momento),
        fecha_calculo=hoy_iso(),
    )


def estadisticas_materia(db: Session, materia_id: int, periodo: str | None = None) -> EstadisticasMateria | None:
    materia = db.get(MateriaProyeccion, materia_id)
    if not materia:
        return None
    momento = ahora()
    tareas = _tareas(db, materia_id=materia_id, periodo=periodo)
    grupos = db.query(GrupoProyeccion).filter_by(materia_id=materia_id).all()
    activos = {
        tarea.grupo_id
        for tarea in tareas
        if tarea.grupo_id and estado_efectivo(tarea.estado, tarea.fecha_entrega, momento) in {"pendiente", "en_progreso", "vencida"}
    }
    return EstadisticasMateria(
        materia_id=materia_id,
        nombre=materia.nombre or f"Materia {materia_id}",
        nrc=materia.nrc or None,
        periodo=periodo,
        tareas=resumen_tareas(tareas, momento),
        grupos=GruposResumen(total_grupos=len(grupos), grupos_activos=len(activos)),
        fecha_calculo=hoy_iso(),
    )


def estadisticas_grupo(db: Session, grupo_id: int) -> EstadisticasGrupo | None:
    grupo = db.get(GrupoProyeccion, grupo_id)
    if not grupo:
        return None
    tareas = _tareas(db, grupo_id=grupo_id)
    integrantes = db.query(MiembroGrupo).filter_by(grupo_id=grupo_id).count()
    return EstadisticasGrupo(
        grupo_id=grupo_id,
        nombre=grupo.nombre or f"Grupo {grupo_id}",
        materia_id=grupo.materia_id,
        integrantes=integrantes,
        tareas=resumen_tareas(tareas),
        fecha_calculo=hoy_iso(),
    )

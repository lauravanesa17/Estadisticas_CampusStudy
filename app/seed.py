from sqlalchemy.orm import Session

from app.models import EventoRecibido
from app.schemas import EventoEntrada
from app.services.eventos import procesar_evento

EVENTOS_DEMO = [
    EventoEntrada(evento_id="seed-u-25", evento="usuario.registrado", payload={
        "usuario_id": 25, "nombre": "Ana", "email": "ana@uniminuto.edu.co", "rol": "estudiante",
    }),
    EventoEntrada(evento_id="seed-u-26", evento="usuario.registrado", payload={
        "usuario_id": 26, "nombre": "Carlos Gómez", "email": "carlos.gomez@uniminuto.edu.co", "rol": "estudiante",
    }),
    EventoEntrada(evento_id="seed-u-27", evento="usuario.registrado", payload={
        "usuario_id": 27, "nombre": "Laura Díaz", "email": "laura.diaz@uniminuto.edu.co", "rol": "estudiante",
    }),
    EventoEntrada(evento_id="seed-m-4", evento="materia.creada", payload={
        "materia_id": 4, "nombre": "Sistemas Distribuidos", "nrc": "12345",
    }),
    EventoEntrada(evento_id="seed-m-12", evento="materia.creada", payload={
        "materia_id": 12, "nombre": "Bases de Datos", "nrc": "30210",
    }),
    EventoEntrada(evento_id="seed-m-3", evento="materia.creada", payload={
        "materia_id": 3, "nombre": "Ingeniería de Software", "nrc": "30311",
    }),
    EventoEntrada(evento_id="seed-m-5", evento="materia.creada", payload={
        "materia_id": 5, "nombre": "Redes", "nrc": "20412",
    }),
    EventoEntrada(evento_id="seed-g-7", evento="grupo.creado", payload={
        "grupo_id": 7,
        "nombre": "Grupo de estudio - Sistemas Distribuidos",
        "materia_id": 4,
        "creado_por": 25,
        "integrantes": [
            {"usuario_id": 25, "rol": "lider"},
            {"usuario_id": 26, "rol": "miembro"},
        ],
    }),
    EventoEntrada(evento_id="seed-g-8", evento="grupo.creado", payload={
        "grupo_id": 8,
        "nombre": "Taller de Bases de Datos",
        "materia_id": 12,
        "creado_por": 25,
        "integrantes": [
            {"usuario_id": 25, "rol": "lider"},
            {"usuario_id": 27, "rol": "miembro"},
        ],
    }),
    EventoEntrada(evento_id="seed-t-15", evento="tarea.creada", payload={
        "tarea_id": 15, "titulo": "Informe de arquitectura distribuida",
        "usuario_id": 25, "materia_id": 4, "grupo_id": 7,
        "prioridad": "alta", "estado": "completada",
        "fecha_entrega": "2026-10-05", "hora_entrega": "23:59",
        "fecha_completada": "2026-10-04T18:00:00",
    }),
    EventoEntrada(evento_id="seed-t-16", evento="tarea.creada", payload={
        "tarea_id": 16, "titulo": "Demo de microservicio de estadísticas",
        "usuario_id": 25, "materia_id": 4, "grupo_id": 7,
        "prioridad": "alta", "estado": "en_progreso",
        "fecha_entrega": "2026-10-15", "hora_entrega": "18:00",
    }),
    EventoEntrada(evento_id="seed-t-17", evento="tarea.creada", payload={
        "tarea_id": 17, "titulo": "Modelo entidad-relación",
        "usuario_id": 25, "materia_id": 12, "grupo_id": 8,
        "prioridad": "media", "estado": "pendiente",
        "fecha_entrega": "2026-10-08", "hora_entrega": "23:59",
    }),
    EventoEntrada(evento_id="seed-t-18", evento="tarea.creada", payload={
        "tarea_id": 18, "titulo": "Casos de uso del sistema",
        "usuario_id": 25, "materia_id": 3,
        "prioridad": "baja", "estado": "completada",
        "fecha_entrega": "2026-10-01", "hora_entrega": "18:00",
        "fecha_completada": "2026-10-03T10:00:00",
    }),
    EventoEntrada(evento_id="seed-t-19", evento="tarea.creada", payload={
        "tarea_id": 19, "titulo": "Laboratorio de sockets",
        "usuario_id": 26, "materia_id": 4, "grupo_id": 7,
        "prioridad": "alta", "estado": "completada",
        "fecha_entrega": "2026-10-05", "hora_entrega": "23:59",
        "fecha_completada": "2026-10-06T09:00:00",
    }),
    EventoEntrada(evento_id="seed-t-20", evento="tarea.creada", payload={
        "tarea_id": 20, "titulo": "Mapa de red del campus",
        "usuario_id": 26, "materia_id": 5,
        "prioridad": "media", "estado": "pendiente",
        "fecha_entrega": "2026-10-20", "hora_entrega": "18:00",
    }),
    EventoEntrada(evento_id="seed-t-21", evento="tarea.creada", payload={
        "tarea_id": 21, "titulo": "Práctica de SQL",
        "usuario_id": 26, "materia_id": 12,
        "prioridad": "media", "estado": "en_progreso",
        "fecha_entrega": "2026-10-13", "hora_entrega": "18:00",
    }),
    EventoEntrada(evento_id="seed-t-22", evento="tarea.creada", payload={
        "tarea_id": 22, "titulo": "Encuesta de investigación de campo",
        "usuario_id": 27, "materia_id": 4,
        "prioridad": "alta", "estado": "pendiente",
        "fecha_entrega": "2026-10-10", "hora_entrega": "23:59",
    }),
    EventoEntrada(evento_id="seed-t-23", evento="tarea.creada", payload={
        "tarea_id": 23, "titulo": "Normalización de tablas",
        "usuario_id": 27, "materia_id": 12, "grupo_id": 8,
        "prioridad": "media", "estado": "completada",
        "fecha_entrega": "2026-10-09", "hora_entrega": "23:59",
        "fecha_completada": "2026-10-09T21:00:00",
    }),
    EventoEntrada(evento_id="seed-t-24", evento="tarea.creada", payload={
        "tarea_id": 24, "titulo": "Prototipo de interfaz",
        "usuario_id": 27, "materia_id": 3,
        "prioridad": "baja", "estado": "pendiente",
        "fecha_entrega": "2026-10-25", "hora_entrega": "18:00",
    }),
]


def seed_si_vacio(db: Session) -> int:
    if db.query(EventoRecibido).first():
        return 0
    for evento in EVENTOS_DEMO:
        procesar_evento(db, evento)
    return len(EVENTOS_DEMO)

from datetime import datetime, timezone

from app.services.tiempo import ZONA_COLOMBIA, estado_efectivo, parsear_fecha


def _evento_tarea(client, fecha, hora=None):
    client.post("/api/v1/eventos", json={"evento_id": "u", "evento": "usuario.registrado", "payload": {"usuario_id": 25, "nombre": "Ana"}})
    payload = {"tarea_id": 1, "titulo": "X", "usuario_id": 25, "materia_id": 4, "estado": "pendiente", "fecha_entrega": fecha}
    if hora:
        payload["hora_entrega"] = hora
    client.post("/api/v1/eventos", json={"evento_id": "t", "evento": "tarea.creada", "payload": payload})


def test_noche_en_colombia_no_adelanta_el_dia(client, reloj):
    # 21:00 en Colombia = 02:00 UTC del día siguiente.
    reloj.momento = datetime(2026, 10, 13, 2, 0, tzinfo=timezone.utc)
    _evento_tarea(client, "2026-10-12")

    cuerpo = client.get("/api/v1/estadisticas/usuario/25").json()

    assert cuerpo["fecha_calculo"] == "2026-10-12"
    assert cuerpo["tareas"]["vencidas"] == 0


def test_hora_entrega_se_respeta(client, reloj):
    _evento_tarea(client, "2026-10-12", "18:00")

    reloj.momento = datetime(2026, 10, 12, 17, 59, tzinfo=ZONA_COLOMBIA)
    assert client.get("/api/v1/estadisticas/usuario/25").json()["tareas"]["vencidas"] == 0

    reloj.momento = datetime(2026, 10, 12, 18, 1, tzinfo=ZONA_COLOMBIA)
    assert client.get("/api/v1/estadisticas/usuario/25").json()["tareas"]["vencidas"] == 1


def test_sin_hora_vence_al_final_del_dia():
    entrega = parsear_fecha("2026-10-12")
    assert estado_efectivo("pendiente", entrega, datetime(2026, 10, 12, 23, 0)) == "pendiente"
    assert estado_efectivo("pendiente", entrega, datetime(2026, 10, 13, 0, 1)) == "vencida"


def test_fechas_con_zona_se_convierten_a_colombia():
    assert parsear_fecha("2026-10-13T02:00:00Z") == datetime(2026, 10, 12, 21, 0)

"""Integración con los demás microservicios, simulados con la forma exacta del contrato."""

from datetime import datetime

from app.services.tiempo import ZONA_COLOMBIA

USUARIO_ANA = {"usuario_id": 25, "nombre": "Ana", "email": "ana@uniminuto.edu.co", "rol": "estudiante"}


def _item_tarea(tarea_id, materia_id=4, estado="pendiente", fecha="2026-12-01"):
    # tareaListadoItemSchema: no trae usuario_id, grupo_id ni hora_entrega.
    return {"tarea_id": tarea_id, "titulo": f"T{tarea_id}", "materia_id": materia_id, "fecha_entrega": fecha, "estado": estado}


def _listado(tareas, total=None, pagina=1, tamano=100):
    # tareas-service envuelve en {exito, datos, mensaje}.
    return {
        "exito": True,
        "datos": {"total": len(tareas) if total is None else total, "pagina": pagina, "tamano": tamano, "tareas": tareas},
        "mensaje": "ok",
    }


def _detalle_tarea(tarea_id, grupo_id=None, **extra):
    datos = {
        "tarea_id": tarea_id, "titulo": f"T{tarea_id}", "usuario_id": 25, "materia_id": 4,
        "grupo_id": grupo_id, "fecha_entrega": "2026-12-01", "hora_entrega": "18:00",
        "prioridad": "media", "estado": "pendiente",
        "fecha_creacion": "2026-10-01T10:00:00", "fecha_actualizacion": "2026-10-01T10:00:00",
        **extra,
    }
    return {"exito": True, "datos": datos, "mensaje": "ok"}


def _configurar_ok(servicios, tareas):
    servicios.rutas[("usuarios", "/api/v1/usuarios/25")] = USUARIO_ANA
    servicios.rutas[("tareas", "/api/v1/tareas")] = _listado(tareas)
    for item in tareas:
        servicios.rutas[("tareas", f"/api/v1/tareas/{item['tarea_id']}")] = _detalle_tarea(item["tarea_id"], estado=item["estado"])
    servicios.rutas[("materias", "/api/v1/materias")] = [
        {"materia_id": 4, "nombre": "Sistemas Distribuidos", "nrc": "12345", "fecha_creacion": "2026-09-20T14:30:00"},
    ]
    servicios.rutas[("grupos", "/api/v1/grupos")] = []


def test_tareas_del_listado_se_asignan_al_usuario(client, servicios):
    _configurar_ok(servicios, [_item_tarea(1, estado="completada"), _item_tarea(2)])

    respuesta = client.get("/api/v1/estadisticas/usuario/25")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Ana"
    assert cuerpo["tareas"]["total"] == 2
    assert cuerpo["tareas"]["completadas"] == 1
    assert cuerpo["materias"][0]["nombre"] == "Sistemas Distribuidos"
    assert "en_cache" not in cuerpo
    assert "X-Datos-En-Cache" not in respuesta.headers


def test_recorre_todas_las_paginas_de_tareas(client, servicios):
    _configurar_ok(servicios, [])
    paginas = {
        "1": _listado([_item_tarea(1), _item_tarea(2)], total=3, pagina=1, tamano=2),
        "2": _listado([_item_tarea(3)], total=3, pagina=2, tamano=2),
    }
    servicios.rutas[("tareas", "/api/v1/tareas")] = lambda req: paginas[req.url.params["pagina"]]

    cuerpo = client.get("/api/v1/estadisticas/usuario/25").json()

    assert cuerpo["tareas"]["total"] == 3


def test_detalle_trae_grupo_y_hora_de_tareas_nuevas(client, servicios):
    _configurar_ok(servicios, [_item_tarea(1)])
    servicios.rutas[("tareas", "/api/v1/tareas/1")] = _detalle_tarea(1, grupo_id=7)
    servicios.rutas[("grupos", "/api/v1/grupos")] = [{
        "grupo_id": 7, "nombre": "G7", "materia_id": 4, "creado_por": 25,
        "integrantes": [{"usuario_id": 25, "rol": "lider", "unido_en": "2026-09-20T14:30:00"}],
        "fecha_creacion": "2026-09-20T14:30:00",
    }]

    cuerpo = client.get("/api/v1/estadisticas/usuario/25").json()

    assert cuerpo["grupos"] == {"total_grupos": 1, "grupos_activos": 1}
    assert client.get("/api/v1/estadisticas/grupo/7").json()["tareas"]["total"] == 1


def test_tarea_que_desaparece_del_origen_sale_de_la_cache(client, servicios, reloj):
    _configurar_ok(servicios, [_item_tarea(1), _item_tarea(2)])
    assert client.get("/api/v1/estadisticas/usuario/25").json()["tareas"]["total"] == 2

    servicios.rutas[("tareas", "/api/v1/tareas")] = _listado([_item_tarea(1)])
    reloj.momento = datetime(2026, 10, 12, 10, 5, tzinfo=ZONA_COLOMBIA)  # vence el TTL

    assert client.get("/api/v1/estadisticas/usuario/25").json()["tareas"]["total"] == 1


def test_integrante_que_sale_del_grupo_se_quita(client, servicios, reloj):
    _configurar_ok(servicios, [])
    grupo = {"grupo_id": 7, "nombre": "G7", "materia_id": 4, "creado_por": 25,
             "integrantes": [{"usuario_id": 25, "rol": "lider"}, {"usuario_id": 26, "rol": "miembro"}]}
    servicios.rutas[("grupos", "/api/v1/grupos")] = [grupo]
    client.get("/api/v1/estadisticas/usuario/25")
    assert client.get("/api/v1/estadisticas/grupo/7").json()["integrantes"] == 2

    servicios.rutas[("grupos", "/api/v1/grupos")] = [{**grupo, "integrantes": [{"usuario_id": 25, "rol": "lider"}]}]
    reloj.momento = datetime(2026, 10, 12, 10, 5, tzinfo=ZONA_COLOMBIA)
    client.get("/api/v1/estadisticas/usuario/25")

    assert client.get("/api/v1/estadisticas/grupo/7").json()["integrantes"] == 1


def test_usuarios_caido_sin_cache_responde_503_con_dependencia(client, servicios):
    _configurar_ok(servicios, [])
    servicios.caidos.add("usuarios")

    respuesta = client.get("/api/v1/estadisticas/usuario/25")

    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == 503
    assert respuesta.json()["dependencia"] == "usuarios-service"


def test_tareas_caido_sin_datos_previos_responde_503_no_ceros(client, servicios):
    _configurar_ok(servicios, [])
    servicios.rutas[("tareas", "/api/v1/tareas")] = 500

    respuesta = client.get("/api/v1/estadisticas/usuario/25")

    assert respuesta.status_code == 503
    assert respuesta.json()["dependencia"] == "tareas-service"


def test_tareas_caido_con_cache_sirve_dato_marcado(client, servicios, reloj):
    _configurar_ok(servicios, [_item_tarea(1, estado="completada")])
    assert client.get("/api/v1/estadisticas/usuario/25").status_code == 200

    servicios.caidos.add("tareas")
    reloj.momento = datetime(2026, 10, 12, 10, 5, tzinfo=ZONA_COLOMBIA)
    respuesta = client.get("/api/v1/estadisticas/usuario/25")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["tareas"]["completadas"] == 1
    assert cuerpo["en_cache"] is True
    assert cuerpo["dependencias_no_disponibles"] == ["tareas-service"]
    assert cuerpo["actualizado_en"] == "2026-10-12T10:00:00"
    assert respuesta.headers["X-Datos-En-Cache"] == "true"


def test_un_servicio_caido_no_impide_consultar_los_demas(client, servicios):
    _configurar_ok(servicios, [_item_tarea(1)])
    servicios.caidos.add("materias")

    cuerpo = client.get("/api/v1/estadisticas/usuario/25").json()

    assert cuerpo["tareas"]["total"] == 1
    assert cuerpo["dependencias_no_disponibles"] == ["materias-service"]


def test_cache_vigente_no_vuelve_a_llamar(client, servicios):
    _configurar_ok(servicios, [])
    client.get("/api/v1/estadisticas/usuario/25")
    llamadas = len(servicios.peticiones)

    client.get("/api/v1/estadisticas/usuario/25")

    assert len(servicios.peticiones) == llamadas


def test_usuario_inexistente_en_origen_da_404(client, servicios):
    _configurar_ok(servicios, [])
    servicios.rutas[("usuarios", "/api/v1/usuarios/25")] = 404

    respuesta = client.get("/api/v1/estadisticas/usuario/25")

    assert respuesta.status_code == 404


def test_reenvia_token_del_frontend(client, servicios):
    _configurar_ok(servicios, [])

    client.get("/api/v1/estadisticas/usuario/25", headers={"Authorization": "Bearer abc"})

    assert servicios.peticiones
    assert all(p.headers.get("Authorization") == "Bearer abc" for p in servicios.peticiones)


def test_usa_token_de_servicio_si_no_llega_uno(client, servicios, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "servicio_token", "secreto")
    _configurar_ok(servicios, [])

    client.get("/api/v1/estadisticas/usuario/25")

    assert all(p.headers.get("Authorization") == "Bearer secreto" for p in servicios.peticiones)

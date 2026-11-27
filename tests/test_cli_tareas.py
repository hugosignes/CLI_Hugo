from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from tareas.acciones import Accion
from tareas.cli import app
from tareas.configuracion import Configuracion
from tareas.errores import AccionNoValida, ConfigError, RutaNoValida
from tareas.ia import ProveedorIA
from tareas.motor import Motor

runner = CliRunner()


# --- CAMINO FELIZ (en carpetas temporales) ---

def test_ordenar_y_renombrar_camino_feliz(tmp_path: Path) -> None:
    (tmp_path / "Apuntes Física 1.PDF").write_text("contenido pdf", encoding="utf-8")
    (tmp_path / "captura pantalla.PNG").write_bytes(b"png")

    cfg = Configuracion(
        {
            "limpiar": Accion.desde_dict({"nombre": "limpiar", "tipo": "renombrar_limpio"}),
            "ordenar": Accion.desde_dict(
                {
                    "nombre": "ordenar",
                    "tipo": "ordenar",
                    "categorias": {"PDF": [".pdf"], "Imagenes": [".png"]},
                }
            ),
            "todo": Accion.desde_dict(
                {"nombre": "todo", "tipo": "encadenar", "pasos": ["limpiar", "ordenar"]}
            ),
        }
    )
    motor = Motor(cfg)

    # Simulación no altera disco
    inf_sim = motor.ejecutar("todo", tmp_path, simular=True)
    assert len(inf_sim.operaciones) == 4
    assert (tmp_path / "Apuntes Física 1.PDF").exists()

    # Ejecución real normaliza y clasifica
    inf_real = motor.ejecutar("todo", tmp_path, simular=False)
    assert len(inf_real.operaciones) == 4
    assert (tmp_path / "PDF" / "Apuntes_Fisica_1.pdf").exists()
    assert (tmp_path / "Imagenes" / "captura_pantalla.png").exists()


def test_limpiar_temporales_antiguos(tmp_path: Path) -> None:
    viejo = tmp_path / "sesion.tmp"
    nuevo = tmp_path / "reciente.tmp"
    viejo.write_text("viejo", encoding="utf-8")
    nuevo.write_text("nuevo", encoding="utf-8")

    hace_40_dias = time.time() - (40 * 86400)
    os.utime(viejo, (hace_40_dias, hace_40_dias))

    accion = Accion.desde_dict(
        {"nombre": "limpiar-tmp", "tipo": "limpiar_temporales", "dias_antiguedad": 30}
    )
    motor = Motor(Configuracion({"limpiar-tmp": accion}))
    inf = motor.ejecutar("limpiar-tmp", tmp_path, simular=False)

    assert len(inf.operaciones) == 1
    assert inf.operaciones[0].origen == "sesion.tmp"
    assert not viejo.exists()
    assert nuevo.exists()


def test_detectar_duplicados(tmp_path: Path) -> None:
    (tmp_path / "original.txt").write_text("datos identicos", encoding="utf-8")
    (tmp_path / "z_copia.txt").write_text("datos identicos", encoding="utf-8")

    accion = Accion.desde_dict({"nombre": "dup", "tipo": "duplicados", "eliminar": False})
    motor = Motor(Configuracion({"dup": accion}))
    inf = motor.ejecutar("dup", tmp_path)

    assert len(inf.operaciones) == 1
    assert inf.operaciones[0].origen == "z_copia.txt"
    assert inf.operaciones[0].estado == "detectado"


def test_acciones_ia_con_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doc = tmp_path / "borrador.txt"
    doc.write_text("Acta de la reunión trimestral de arquitectura.", encoding="utf-8")

    monkeypatch.setattr(ProveedorIA, "resumir_texto", lambda self, t, n: "- Resumen de prueba")
    monkeypatch.setattr(ProveedorIA, "sugerir_nombre", lambda self, t, ext: f"acta_trimestral{ext}")

    cfg = Configuracion(
        {
            "resumir": Accion.desde_dict({"nombre": "resumir", "tipo": "resumir_ia"}),
            "renombrar": Accion.desde_dict({"nombre": "renombrar", "tipo": "renombrar_ia"}),
        }
    )
    motor = Motor(cfg)

    inf_res = motor.ejecutar("resumir", tmp_path)
    assert inf_res.operaciones[0].destino == "- Resumen de prueba"

    inf_ren = motor.ejecutar("renombrar", tmp_path)
    assert inf_ren.operaciones[0].destino == "acta_trimestral.txt"
    assert (tmp_path / "acta_trimestral.txt").exists()


# --- CASOS FEOS Y DEGRADACIÓN SIN RED ---

def test_caso_feo_json_mal_formado(tmp_path: Path) -> None:
    bad_json = tmp_path / "roto.json"
    bad_json.write_text("{acciones: [sin comillas}", encoding="utf-8")

    with pytest.raises(ConfigError, match="sintaxis JSON"):
        Configuracion.desde_archivo(bad_json)


def test_caso_feo_campo_obligatorio_faltante_en_accion(tmp_path: Path) -> None:
    cfg_file = tmp_path / "incompleto.json"
    cfg_file.write_text(
        json.dumps({"acciones": [{"nombre": "sin-categorias", "tipo": "ordenar"}]}),
        encoding="utf-8",
    )

    with pytest.raises(AccionNoValida, match="categorias"):
        Configuracion.desde_archivo(cfg_file)


def test_caso_feo_carpeta_inexistente(tmp_path: Path) -> None:
    cfg = Configuracion({"dup": Accion.desde_dict({"nombre": "dup", "tipo": "duplicados"})})
    motor = Motor(cfg)

    with pytest.raises(RutaNoValida, match="no existe"):
        motor.ejecutar("dup", tmp_path / "no_existe")


def test_caso_feo_sin_red_ia_continua_acciones_locales(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "nota importante.txt").write_text("Contenido sin red", encoding="utf-8")

    def fallo_red(*args, **kwargs):
        raise httpx.ConnectError("Sin conexión a Ollama")

    monkeypatch.setattr(httpx, "post", fallo_red)

    cfg = Configuracion(
        {
            "resumir": Accion.desde_dict({"nombre": "resumir", "tipo": "resumir_ia"}),
            "normalizar": Accion.desde_dict({"nombre": "normalizar", "tipo": "renombrar_limpio"}),
            "flujo": Accion.desde_dict(
                {"nombre": "flujo", "tipo": "encadenar", "pasos": ["resumir", "normalizar"]}
            ),
        }
    )
    motor = Motor(cfg)
    informe = motor.ejecutar("flujo", tmp_path, simular=False)

    # La IA falla con aviso controlado, pero la acción local posterior sí se completa
    assert len(informe.avisos) == 1
    assert "IA no disponible" in informe.avisos[0]
    assert len(informe.operaciones) == 1
    assert (tmp_path / "nota_importante.txt").exists()


def test_cli_codigos_salida_sin_traceback(tmp_path: Path) -> None:
    res = runner.invoke(app, ["--config", str(tmp_path / "no_existe.json"), "validar"])
    assert res.exit_code == 3
    assert "Traceback" not in res.output

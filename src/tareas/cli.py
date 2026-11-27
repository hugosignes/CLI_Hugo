from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from tareas.configuracion import Configuracion
from tareas.errores import ErrorCLI
from tareas.motor import Motor

load_dotenv()

app = typer.Typer(
    name="tareas",
    help="CLI multiplataforma para automatizar tareas sobre ficheros con sistema e IA.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _manejar_error(err: ErrorCLI) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {err}")
    raise typer.Exit(code=err.codigo_salida)


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(Path("acciones.json"), "--config", "-c", help="Ruta a acciones.json."),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@app.command("acciones")
def cmd_acciones(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Salida estructurada en JSON."),
) -> None:
    """Muestra las acciones configuradas en acciones.json."""
    try:
        cfg = Configuracion.desde_archivo(ctx.obj["config_path"])
        if as_json:
            salida = [
                {"nombre": a.nombre, "requiere_ia": a.requiere_ia, "descripcion": a.descripcion}
                for a in cfg.acciones
            ]
            typer.echo(json.dumps(salida, ensure_ascii=False, indent=2))
            return

        tabla = Table(title="Acciones disponibles")
        tabla.add_column("Nombre", style="cyan", no_wrap=True)
        tabla.add_column("IA", style="magenta")
        tabla.add_column("Descripción")
        for a in cfg.acciones:
            tabla.add_row(a.nombre, "Sí" if a.requiere_ia else "No", a.descripcion)
        console.print(tabla)
    except ErrorCLI as err:
        _manejar_error(err)


@app.command("validar")
def cmd_validar(ctx: typer.Context) -> None:
    """Valida la sintaxis y los campos de acciones.json."""
    try:
        cfg = Configuracion.desde_archivo(ctx.obj["config_path"])
        console.print(f"[green]OK:[/green] {len(cfg.acciones)} acciones validadas correctamente.")
    except ErrorCLI as err:
        _manejar_error(err)


@app.command("listar")
def cmd_listar(
    ctx: typer.Context,
    carpeta: Path = typer.Argument(Path("."), help="Carpeta a inspeccionar."),
    as_json: bool = typer.Option(False, "--json", help="Salida estructurada en JSON."),
) -> None:
    """Lista los ficheros de una carpeta."""
    try:
        cfg = Configuracion.desde_archivo(ctx.obj["config_path"])
        motor = Motor(cfg)
        items = motor.listar_carpeta(carpeta)
        if as_json:
            typer.echo(json.dumps(items, ensure_ascii=False, indent=2))
            return

        tabla = Table(title=f"Ficheros en {carpeta}")
        tabla.add_column("Nombre", style="cyan")
        tabla.add_column("Extensión", style="yellow")
        tabla.add_column("Tamaño (bytes)", justify="right")
        for it in items:
            tabla.add_row(it["nombre"], it["extension"], str(it["tamano_bytes"]))
        console.print(tabla)
    except ErrorCLI as err:
        _manejar_error(err)


@app.command("ejecutar")
def cmd_ejecutar(
    ctx: typer.Context,
    nombre_accion: str = typer.Argument(..., help="Nombre de la acción a ejecutar."),
    carpeta: Optional[Path] = typer.Argument(Path("."), help="Carpeta destino."),
    simular: bool = typer.Option(False, "--simular", help="Simula la ejecución sin modificar archivos."),
    si: bool = typer.Option(False, "--si", "-y", help="Confirma automáticamente sin preguntar."),
    as_json: bool = typer.Option(False, "--json", help="Devuelve el resultado en JSON."),
) -> None:
    """Ejecuta una acción sobre la carpeta indicada."""
    try:
        cfg = Configuracion.desde_archivo(ctx.obj["config_path"])
        cfg.obtener(nombre_accion)

        if not simular and not si:
            if not typer.confirm(f"¿Ejecutar '{nombre_accion}' sobre '{carpeta}'?", default=False):
                err_console.print("Operación cancelada por el usuario.")
                raise typer.Exit(code=0)

        motor = Motor(cfg)
        informe = motor.ejecutar(nombre_accion, carpeta, simular=simular)

        for aviso in informe.avisos:
            err_console.print(f"[bold yellow]Aviso:[/bold yellow] {aviso}")

        if as_json:
            payload = {
                "avisos": informe.avisos,
                "operaciones": [
                    {"origen": op.origen, "destino": op.destino, "estado": op.estado}
                    for op in informe.operaciones
                ],
            }
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        if not informe.operaciones:
            console.print("[yellow]No había ficheros pendientes para esta acción.[/yellow]")
            return

        tabla = Table(title=f"Resultado: {nombre_accion} ({'SIMULACIÓN' if simular else 'REAL'})")
        tabla.add_column("Origen", style="cyan")
        tabla.add_column("Destino / Resultado", style="green")
        tabla.add_column("Estado", style="magenta")
        for op in informe.operaciones:
            tabla.add_row(op.origen, op.destino, op.estado)
        console.print(tabla)
    except ErrorCLI as err:
        _manejar_error(err)


if __name__ == "__main__":
    sys.exit(app())

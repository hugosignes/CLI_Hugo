# CLI `tareas` v1.0.0

Herramienta multiplataforma de línea de órdenes para automatizar tareas repetitivas sobre ficheros combinando operaciones del sistema operativo e IA local, configurada íntegramente desde `acciones.json`.

## Instalación en una sola orden

Con `uv` (recomendado):

```bash
uv tool install git+https://github.com/tu-usuario/cli-tareas.git
```

O en local tras clonar el repositorio:

```bash
uv sync
uv tool install --editable .
```

## Variables de entorno (IA y secretos)

Copia `.env.example` a `.env` (ignorado por Git):

```bash
cp .env.example .env
```

Variables soportadas:
- `TAREAS_MODELO`: Modelo de Ollama a utilizar (por defecto `llama3.2`).
- `TAREAS_OLLAMA_URL`: Endpoint HTTP del servicio de IA (por defecto `http://localhost:11434/api/generate`).
- `TAREAS_API_KEY`: Clave opcional si apuntas a un endpoint compatible que requiera autenticación Bearer.

> **Modo sin red:** Si el servidor de IA no está accesible, `tareas` muestra un aviso claro por `stderr` y continúa ejecutando todas las acciones que no dependen de IA sin perder ningún fichero.

## Uso y ejemplos

```bash
# Ver ayuda general o de un subcomando
tareas --help
tareas ejecutar --help

# Validar la sintaxis y tipos de acciones.json
tareas validar

# Listar las acciones configuradas (formato tabla o JSON)
tareas acciones
tareas acciones --json

# Listar ficheros de una carpeta
tareas listar ~/Descargas

# Simular una acción antes de tocar ficheros
tareas ejecutar ordenar-descargas ~/Descargas --simular

# Ejecutar sin pedir confirmación interactiva
tareas ejecutar limpieza-completa ~/Descargas --si

# Usar un fichero de configuración alternativo
tareas --config mis-acciones.json validar
```

## Esquema de `acciones.json`

El fichero `acciones.json` contiene un objeto raíz con una lista obligatoria `"acciones"`. Cada entrada admite los siguientes campos:

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :--- | :--- |
| `nombre` | `string` | Sí | Identificador único de la acción que se pasa a `tareas ejecutar <nombre>`. |
| `tipo` | `string` | Sí | Tipo de motor: `ordenar`, `renombrar_limpio`, `limpiar_temporales`, `duplicados`, `resumir_ia`, `renombrar_ia` o `encadenar`. |
| `descripcion` | `string` | No | Texto explicativo mostrado en `tareas acciones`. |
| `categorias` | `object` | Solo en `ordenar` | Diccionario `{"Carpeta": [".ext1", ".ext2"]}`. |
| `dias_antiguedad` | `int` | Solo en `limpiar_temporales` | Antigüedad mínima en días (`>= 0`) para eliminar ficheros temporales. |
| `extensiones` | `list[str]` | Opcional | Lista de extensiones permitidas (usado en `limpiar_temporales`, `resumir_ia` y `renombrar_ia`). |
| `eliminar` | `bool` | Solo en `duplicados` | Si es `true`, borra los duplicados tras la confirmación; si es `false` (por defecto), solo los informa. |
| `pasos` | `list[str]` | Solo en `encadenar` | Lista ordenada de al menos 2 nombres de acciones existentes a ejecutar en secuencia. |

## Códigos de salida

- `0`: Ejecución completada correctamente (o cancelada explícitamente por el usuario).
- `1`: Error durante la ejecución o fallo del proveedor IA.
- `2`: Error de uso o ruta de carpeta inexistente.
- `3`: Error de configuración (`acciones.json` inexistente, JSON mal formado o campo inválido).

## Pruebas

```bash
uv run pytest -v
```

## Configuración con la API del centro (IES Doctor Lluís Simarro)

1. Copia `.env.example` a `.env` y añade tu clave en `TAREAS_API_KEY`.
2. Descarga el certificado del centro (`ca-simarro.crt`) en la raíz del proyecto o en `~/.config/opencode/ca-simarro.crt`.
3. Ejecuta cualquier acción con IA (`resumir-documentos` o `renombrar-ia`).

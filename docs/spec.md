# Especificación — CLI `tareas`

- **Para quién:** Usuarios y desarrolladores que gestionan carpetas con gran volumen de archivos (descargas, apuntes, entregas) desde Linux, Windows o macOS.
- **Qué problema resuelve:** Automatiza tareas repetitivas de clasificación, normalización de nombres, limpieza de temporales/duplicados y resumen o renombrado semántico con IA.
- **Órdenes principales:** `tareas acciones`, `tareas validar`, `tareas listar <carpeta>`, `tareas ejecutar <accion> <carpeta> [--simular] [--si] [--json]`.
- **Configuración externa:** Todas las acciones se definen en `acciones.json` (o `--config`), permitiendo crear flujos nuevos sin modificar el código Python.
- **Qué NO hará:** No incluye interfaz gráfica (GUI), nunca almacena claves en el código ni modifica ficheros sin `--simular` o confirmación previa.

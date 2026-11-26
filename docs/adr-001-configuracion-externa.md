# ADR-001: Uso de configuración externa (`acciones.json`) frente a acciones codificadas

- **Estado:** Aceptado
- **Fecha:** 2026-11-26

## Contexto

La CLI `tareas` debe permitir que cada usuario adapte las reglas de clasificación, limpieza y procesamiento con IA a sus propias carpetas (por ejemplo, diferentes extensiones, umbrales de antigüedad o combinaciones de pasos) sin necesidad de editar el código fuente ni reinstalar el paquete.

## Decisión

Se adopta un fichero declarativo externo (`acciones.json`, configurable mediante `--config`) validado al arranque por una fábrica estática (`Accion.desde_dict`) con comprobación explícita de tipos, campos obligatorios e integridad referencial.

## Alternativas consideradas

1. **Definir las acciones en diccionarios o clases dentro del código Python:** Descartado porque obliga a tocar código y reempaquetar la herramienta ante cualquier cambio de carpeta o extensión.
2. **Pasar todas las reglas por flags en la línea de órdenes:** Descartado porque vuelve las órdenes largas, difíciles de recordar y propensas a errores al encadenar varios pasos.

## Consecuencias

- **Positivas:** Añadir o combinar acciones no requiere modificar Python; las configuraciones son reproducibles, versionables y fáciles de compartir.
- **Negativas:** Exige una capa estricta de validación de esquema (`Configuracion` y `Accion.desde_dict`) para informar con precisión al usuario cuando falta un campo o hay un error de sintaxis JSON antes de tocar el disco.

# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

## [1.0.0] - 2026-11-26

### Añadido
- Arquitectura modular separada en `cli`, `motor`, `configuracion`, `acciones`, `ia` y `errores`.
- Jerarquía orientada a objetos con fábrica estática `Accion.desde_dict()` y validación estricta de esquema.
- 7 acciones predefinidas configurables desde `acciones.json`: `ordenar-descargas`, `limpiar-nombres`, `limpiar-temporales`, `detectar-duplicados`, `resumir-documentos`, `renombrar-ia` y `limpieza-completa` (encadenada).
- Degradación elegante sin red: si el proveedor IA no responde, se informa al usuario y continúan las acciones locales.
- Modo seguro `--simular`, confirmación interactiva `--si`, salida estructurada `--json` y códigos de salida diferenciados (`0`, `1`, `2`, `3`).
- Suite completa de pruebas unitarias y de integración con `pytest` en carpetas temporales y flujo CI en GitHub Actions.
- ADR-001 justificando el uso de configuración externa frente a lógica acoplada en código.

# Informe de entrega — BrawlBot AI 0.5.0

## Resultado verificado

- Backend Python: compilación de sintaxis con `python -m compileall -q brawlbot tests` completada.
- Suite automatizada: **29 pruebas aprobadas** (`29 passed`).
- Cobertura añadida: selección dinámica desde catálogo, resolución de mapas/modos, filtros de Brawlers propios, exclusión de picks enemigos/aliados/bans, análisis de equipo y reporte de limitaciones estadísticas.
- Android: código fuente actualizado a `versionName 0.5.0`, con formulario de draft editable.

## No verificado en este entorno

- No se generó APK ni se ejecutó Gradle/Android Studio. La compilación Android queda para el equipo local del propietario.
- No se pudo hacer una sincronización real con BrawlAPI desde el entorno de construcción porque la conexión DNS/red de ejecución no estaba disponible. La integración se validó con respuestas HTTP simuladas en pruebas.
- No se realizó inferencia con un modelo PPO/ONNX entrenado ni se incluyeron pesos neuronales.
- No se integraron estadísticas reales de win rate/pick rate por mapa/rango. El catálogo público usado para brawlers/mapas/modos no contiene esas muestras; por eso el motor informa que sus puntuaciones son heurísticas y no estadísticas medidas.

## Importante

La versión 0.5.0 amplía el catálogo y la interfaz de draft, pero no debe describirse como un entrenador autónomo terminado ni como una IA de meta profesional. La conexión de estadísticas competitivas requiere un proveedor documentado y validado. La ejecución en Android Studio y la prueba en el dispositivo son pasos pendientes antes de declarar el producto listo para uso.

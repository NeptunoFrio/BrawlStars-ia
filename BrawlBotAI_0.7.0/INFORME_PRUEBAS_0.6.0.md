# Informe de entrega — BrawlBot AI 0.6.0

## Resultado verificado

- Suite automatizada: **32 pruebas aprobadas** (`32 passed`).
- Compilación de sintaxis Python: `python -m compileall -q brawlbot tests` completada.
- Añadidas pruebas del planificador táctico: disparo condicionado por visibilidad/línea de visión/munición, bloqueo de disparo sin condiciones y respuesta evasiva ante proyectiles reportados.
- Añadido `POST /api/v1/tactical/plan`.
- Versiones API y Android actualizadas a 0.6.0.

## Qué entrega el planificador

Genera un plan normalizado de movimiento, apuntado, disparo condicionado, esquiva y uso de súper a partir de una observación estructurada suministrada por otro componente.

## Lo que NO está implementado ni verificado

- No captura ni interpreta imágenes o vídeo del juego.
- No detecta automáticamente brawlers, obstáculos, proyectiles, salud o munición desde la pantalla.
- No envía toques, gestos ni entradas al cliente de Brawl Stars.
- No inicia, juega ni termina partidas reales.
- No hay calibración de coordenadas para controles reales ni prueba en dispositivo.
- La salida del endpoint está marcada `PLAN_ONLY` y `live_game_control=false`.
- No se compiló APK; Android Studio queda pendiente en el equipo local.

## Conclusión

0.6.0 amplía la arquitectura con una primera capa táctica comprobable, pero **no es todavía un bot autónomo para partidas reales**. No debe presentarse como tal.

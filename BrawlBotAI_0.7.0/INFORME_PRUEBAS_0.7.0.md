# Informe de pruebas — BrawlBot AI 0.7.0

## Cambios incluidos
- Servicio Android de captura con MediaProjection y consentimiento del sistema.
- Guardado local del último fotograma JPEG.
- Exportación manual del fotograma a Pictures/BrawlBotAI.
- Servicio de Accesibilidad opcional con una acción de gesto de prueba iniciada por el usuario.

## Verificación ejecutada en este entorno
- Backend: `PYTHONPATH=. pytest -q` → 32 pruebas aprobadas.
- No se pudo compilar el APK aquí: no hay instalación de Gradle ni Android SDK disponible en el entorno de construcción.
- No se probó en un teléfono físico ni dentro de Brawl Stars.

## Límites conocidos
- No hay detector visual entrenado ni lógica que identifique automáticamente Brawlers, salud, munición, proyectiles o geometría del mapa.
- No existe un bucle autónomo que convierta fotogramas en acciones tácticas.
- El gesto de Accesibilidad es una prueba manual, no un controlador de partida.
- El backend `/api/v1/tactical/plan` sigue siendo `PLAN_ONLY`.

## Primer ciclo de prueba en el teléfono
1. Abrir el proyecto Android en Android Studio y compilar/instalar la app.
2. Pulsar **Iniciar captura de pantalla** y aceptar el permiso de Android.
3. Abrir Brawl Stars; la notificación persistente de BrawlBot confirma que la captura sigue activa en segundo plano.
4. Pulsar **Guardar último fotograma en Galería** y comprobar `Pictures/BrawlBotAI`.
5. Activar BrawlBot AI en Ajustes → Accesibilidad y volver a la app.
6. Con el juego cerrado o en una pantalla segura, pulsar **Probar movimiento táctil**. También se puede usar la acción **Probar gesto** de la notificación mientras el juego está abierto, pero solo en entrenamiento o pantalla segura; no usarla en partidas competitivas.
7. Enviar el fotograma guardado y cualquier error para implementar y calibrar la siguiente fase de percepción.

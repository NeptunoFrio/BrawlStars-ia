# BrawlBot AI 0.7.0

BrawlBot AI es una plataforma de análisis estratégico y experimentación con agentes para Brawl Stars.

Esta versión incorpora un motor de recomendaciones basado en el catálogo remoto completo, además de consolidar la arquitectura de cerebros (Heuristic / ONNX / PPO), unifica el almacenamiento de modelos, mejora el simulador, añade métricas básicas y actualiza la aplicación Android.

## Novedades 0.7.0

- Añadida captura de pantalla Android mediante MediaProjection, siempre con consentimiento visible del sistema.
- Los fotogramas se guardan localmente en `filesDir/latest_frame.jpg`; no se suben automáticamente.
- Botón para exportar el último fotograma a `Pictures/BrawlBotAI` y poder compartirlo para depuración.
- Añadido servicio de Accesibilidad opcional y visible que permite enviar un gesto de prueba desde la app o desde una acción explícita de la notificación.
- No se implementan ocultación, evasión de protecciones ni automatización autónoma de partidas.
- La app muestra el estado de captura y del puente táctil.

## Estado real de integración en 0.7.0

La capa Android ahora puede solicitar permiso para capturar la pantalla y conservar fotogramas localmente. También permite comprobar un gesto táctil explícito, después de que el usuario active manualmente el servicio de Accesibilidad. Esto es una base de integración y diagnóstico, no un bot autónomo.

Siguen pendientes y no deben considerarse funcionales: reconocimiento automático de jugadores/Brawlers/obstáculos/proyectiles, estimación de salud y munición desde la imagen, calibración automática de coordenadas, bucle de decisión en tiempo real, ejecución autónoma de movimiento/apuntado/disparo/súper y pruebas dentro de partidas reales. El backend táctico continúa requiriendo observaciones estructuradas.

## Novedades 0.6.0

- Endpoint `POST /api/v1/tactical/plan` para generar un plan táctico estructurado: movimiento hacia objetivo, retirada, desplazamiento lateral, esquiva reportada, punto de mira, disparo condicionado y uso de súper.
- El planificador valida de forma conservadora visibilidad, línea de visión, munición, salud y proyectiles entrantes.
- Respuesta marcada `PLAN_ONLY`; no captura la pantalla ni inyecta controles en Brawl Stars.
- La observación debe proceder de un adaptador de percepción autorizado o de un entorno de pruebas.

Ejemplo:

```json
{
  "player_x": 0.3, "player_y": 0.5, "health": 0.8, "ammo": 3,
  "target": {"visible": true, "line_of_sight": true, "x": 0.75, "y": 0.5},
  "objective": {"x": 0.5, "y": 0.5},
  "incoming_projectiles": [], "super_ready": false
}
```

Consultar `POST /api/v1/tactical/plan`. El resultado es un plan y no ejecuta acciones.

## Qué funciona en esta versión

- API FastAPI con health check, análisis de draft, análisis de mapa/equipo y decisiones de agente.
- Motor de draft que consume el catálogo remoto completo de Brawlers, mapas y modos; filtra por Brawlers disponibles, excluye picks rivales y propone alternativas con explicación.
- Análisis de equipo basado en clases del catálogo remoto.
- Identificación del mapa y validación de su modo asociado cuando la fuente lo informa.
- **BrainInterface + BrainRuntime** con fallback automático a HeuristicBrain.
- **HeuristicBrain** completamente funcional.
- **ONNXBrain** y **PPOBrain**: carga, validación de contrato e inferencia reales cuando existe un modelo compatible.
- **Model Manager**: registro, almacenamiento, activación, eliminación y registro automático de modelos PPO entrenados.
- Simulador de arena 2D abstracto (movimientos corregidos).
- Entrenamiento PPO opcional (Stable-Baselines3 + Gymnasium) que registra el modelo en el Model Manager.
- App Android con conexión configurable, controles de Brain Status/Models/Metrics, sincronización del catálogo y formulario de draft con modo, mapa, Brawlers propios, picks enemigos, aliados, bans y rango.
- Logging básico y métricas en memoria (`/api/v1/metrics`).
- Pruebas automatizadas ampliadas.

## Qué NO afirma esta versión

- No incluye un modelo neuronal grande ya entrenado.
- El agente de simulación no juega partidas públicas ni controla el cliente de Brawl Stars.
- El draft dinámico usa heurísticas transparentes de clase y modo; no equivale a un modelo entrenado ni a estadísticas competitivas.
- Subir un modelo no lo convierte automáticamente en un cerebro compatible. Para ONNX se requiere el contrato documentado en `brains.py` / `onnx_brain.py`.
- ONNX y PPO requieren dependencias opcionales y un modelo compatible con el contrato `arena_obs8_act5_v1`.

## Requisitos

- Backend: Python 3.10+.
- Android: Android Studio reciente, JDK 17 y Android Gradle Plugin compatible.
- Para PPO: instalar `requirements-training.txt` adicionalmente.
- Para ONNX: instalar `requirements-onnx.txt` adicionalmente.

## Ejecutar backend local

```bash
cd server
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# Windows PowerShell:
$env:BRAWLBOT_API_KEY="cambia-esta-clave"
# Linux/macOS:
export BRAWLBOT_API_KEY="cambia-esta-clave"
uvicorn brawlbot.main:app --host 0.0.0.0 --port 8000
```

Documentación interactiva: `http://127.0.0.1:8000/docs`.

## Ejecutar pruebas

```bash
cd server
pip install -r requirements.txt
pytest -v
```

## Entrenar el agente PPO (opcional)

```bash
pip install -r requirements-training.txt
python -m brawlbot.training.train_ppo --timesteps 50000
# Opcional: activar automáticamente
python -m brawlbot.training.train_ppo --timesteps 50000 --activate
```

El modelo se registra automáticamente en el Model Manager (`data/models/` + `registry.json`).

## Android

1. Abre la carpeta `android` en Android Studio.
2. Espera la sincronización de Gradle.
3. En la app, escribe la URL del backend (emulador: `http://10.0.2.2:8000`).
4. En un teléfono físico, sustituye `10.0.2.2` por la IP local del PC que ejecuta el backend (ambos deben estar en la misma red). Configura la misma API key que pusiste en el backend.
5. Usa los botones **Brain Status** y **List Models** para ver el estado del Runtime y los modelos registrados.

La app usa HTTP solo para desarrollo local. Para publicar o exponer el backend en Internet, configura HTTPS, autenticación robusta, límites de carga y firewall.

## Estructura principal

```
server/
  brawlbot/
    brain_interface.py   # Interfaz común de cerebros
    brains.py            # HeuristicBrain, ONNXBrain, PPOBrain
    runtime.py           # BrainRuntime + fallback
    contracts.py         # Contrato obs8 / act5
    models.py            # Model Manager (+ register_trained_model)
    main.py              # API FastAPI + métricas
    simulator.py         # Arena abstracta
    strategy.py          # Fallback heurístico local
    intelligence.py      # Draft dinámico y análisis de equipo por catálogo
    training/train_ppo.py
  tests/
  data/                  # registry.json + models/
android/                 # App Kotlin + Compose
```

## Contrato de observación / acción

- Observación (8 floats normalizados 0-1):  
  `x, y, health, enemy_x, enemy_y, objective_x, objective_y, step_fraction`
- Acciones (5):  
  `hold, move_to_objective, retreat, approach_enemy, strafe`
- Versión de contrato: `arena_obs8_act5_v1`

## Changelog 0.7.0

- Añadidas captura autorizada de pantalla y prueba manual de gesto táctil en Android.
- Exportación de fotograma a la galería para diagnóstico.
- Se documentan explícitamente las funciones de percepción y autonomía que siguen pendientes.

## Changelog 0.6.0

- Añadido planificador táctico experimental para movimiento, apuntado, disparo condicionado, esquiva y súper.
- Añadido endpoint `/api/v1/tactical/plan` y esquema de observación.
- Actualizadas las versiones de API y Android a 0.6.0.
- Se mantiene explícito que no existe integración de captura/control del cliente real.

## Changelog 0.5.0

- Nuevo motor dinámico basado en el catálogo completo de BrawlAPI, en lugar de limitar las recomendaciones al listado local de 14 Brawlers.
- Recomendaciones por clase y modo, exclusión de picks rivales/bans/aliados, diversidad de clases y alternativas.
- Recibe rango competitivo y picks aliados; el rango queda registrado en la respuesta, pero no modifica el scoring porque no hay estadísticas segmentadas verificadas por rango.
- Análisis de equipos con Brawlers obtenidos del catálogo remoto.
- Respuesta incluye fuente, antigüedad de catálogo, validación de mapa/modo y limitaciones estadísticas.
- CORS deja de aceptar cualquier origen por defecto; se configura mediante `BRAWLBOT_CORS_ORIGINS`.
- App Android y API actualizadas a 0.5.0.
- Pruebas añadidas para scoring dinámico y selección desde catálogo.

## Changelog 0.4.2

- Unificación de almacenamiento de modelos (entrenamiento PPO → Model Manager).
- Limpieza de código legacy (`agent.py` y `onnx_brain.py` convertidos en wrappers de compatibilidad).
- Versiones sincronizadas a 0.4.2.
- Corrección de la lógica de movimiento del simulador.
- Logging básico + endpoint `/api/v1/metrics`.
- App Android con visualización de Brain Status, Models y Metrics.
- Pruebas ampliadas (API, contracts, runtime, models).
- Fallback y validación de modelos reforzados.

## Licencia y uso

Proyecto de experimentación. La versión 0.7.0 incorpora captura de pantalla consentida y gestos manuales de diagnóstico, pero no juega partidas por sí sola. No incluye evasión de protecciones ni control autónomo del cliente de Brawl Stars. El planificador táctico entrega decisiones estructuradas para pruebas; no es todavía un controlador en vivo.


## 0.4.2 — Catálogo remoto de conocimiento

Esta versión incorpora sincronización del catálogo público de Brawl Stars mediante BrawlAPI:

- `GET /api/v1/knowledge/status`: estado de caché, origen, fecha y recuentos.
- `POST /api/v1/knowledge/refresh?force=true`: actualiza brawlers, mapas y modos.
- `GET /api/v1/knowledge/search?category=brawlers&q=shelly`: búsqueda local en el catálogo sincronizado. Categorías: `brawlers`, `maps`, `gamemodes`.
- La sincronización se intenta al iniciar el backend y mantiene una caché local en `server/data/knowledge.json`.
- No necesita API key externa para BrawlAPI. Si Internet falla, conserva los datos locales.

**Límite importante:** BrawlAPI proporciona catálogo y metadatos del juego, no muestras estadísticas actuales de win rate/pick rate por mapa (los arrays `stats` y `teamStats` del dataset público están vacíos). El motor 0.5.0 deja de depender del pequeño catálogo estático, pero sus puntuaciones son heurísticas por clase/modo, no resultados medidos. No se inventan win rates, counters profesionales ni sinergias estadísticamente validadas.

La integración de estadísticas competitivas por mapa/rango sigue pendiente de un proveedor con API documentada, permisos de uso y muestras/fechas verificables. Brawlify publica estadísticas en su web, pero no se ha añadido scraping ni se ha supuesto que su web pública sea una API estable. Para mostrar recomendaciones competitivas reales, esa conexión debe validarse antes de activarse.

La aplicación Android incluye controles para consultar el estado y solicitar actualización del catálogo, y llamadas de prueba para draft/análisis. No se compila APK desde este proyecto; el usuario compila desde Android Studio.

## Seguridad y configuración

- `BRAWLBOT_API_KEY`: si se define, las rutas de API protegidas requieren `X-API-Key`. Mantener el backend solo en red local mientras se use HTTP.
- `BRAWLBOT_CORS_ORIGINS`: lista separada por comas de orígenes autorizados. Por defecto solo `http://localhost,http://127.0.0.1`.
- No exponer el backend directamente a Internet sin HTTPS, autenticación fuerte, límites de carga y reglas de firewall.
- La app Android mantiene HTTP cleartext para desarrollo local; antes de publicar debe migrarse a HTTPS.

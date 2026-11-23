package com.brawlbot.ai

import android.os.Bundle
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.provider.Settings
import android.content.ContentValues
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.FileInputStream
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONArray
import org.json.JSONObject

private val Bg = Color(0xFF0B0D14)
private val Panel = Color(0xFF171B28)
private val Accent = Color(0xFF8B72FF)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { BrawlBotApp() }
    }
}

@Composable
fun BrawlBotApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(ScreenCaptureService.PREFS, Context.MODE_PRIVATE) }
    var captureStatus by remember { mutableStateOf(prefs.getString("capture_status", "No iniciada") ?: "No iniciada") }
    var controlStatus by remember { mutableStateOf(prefs.getString("control_status", "Sin probar") ?: "Sin probar") }
    var accessibilityReady by remember { mutableStateOf(prefs.getBoolean("accessibility_ready", false)) }
    val captureLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val serviceIntent = Intent(context, ScreenCaptureService::class.java).apply {
                action = ScreenCaptureService.ACTION_START
                putExtra(ScreenCaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(ScreenCaptureService.EXTRA_DATA, result.data)
            }
            if (android.os.Build.VERSION.SDK_INT >= 26) context.startForegroundService(serviceIntent) else context.startService(serviceIntent)
            captureStatus = "Solicitando captura..."
        } else captureStatus = "Permiso de captura cancelado"
    }
    var baseUrl by remember { mutableStateOf("http://10.0.2.2:8000") }
    var apiKey by remember { mutableStateOf("") }
    var output by remember { mutableStateOf("Conecta tu backend para comenzar.") }
    var modeInput by remember { mutableStateOf("Gem Grab") }
    var mapInput by remember { mutableStateOf("Hard Rock Mine") }
    var ownedInput by remember { mutableStateOf("Poco, Piper, Shelly") }
    var enemyInput by remember { mutableStateOf("Bull") }
    var allyInput by remember { mutableStateOf("") }
    var bansInput by remember { mutableStateOf("") }
    var rankInput by remember { mutableStateOf("Mythic") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun call(path: String, body: String? = null) {
        if (busy) return
        busy = true
        scope.launch {
            output = try {
                withContext(Dispatchers.IO) {
                    val conn = (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection)
                    conn.requestMethod = if (body == null) "GET" else "POST"
                    conn.connectTimeout = 8000
                    conn.readTimeout = 15000
                    conn.setRequestProperty("Content-Type", "application/json")
                    if (apiKey.isNotBlank()) conn.setRequestProperty("X-API-Key", apiKey)
                    if (body != null) {
                        conn.doOutput = true
                        conn.outputStream.use { it.write(body.toByteArray()) }
                    }
                    val code = conn.responseCode
                    val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                    val text = stream?.bufferedReader()?.use { it.readText() } ?: "HTTP $code"
                    conn.disconnect()
                    "HTTP $code\n$text"
                }
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
            busy = false
        }
    }

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Accent,
            background = Bg,
            surface = Panel,
            onBackground = Color.White,
            onSurface = Color.White
        )
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .background(Bg)
                .verticalScroll(rememberScrollState())
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("BRAWLBOT AI", fontSize = 26.sp, color = Color.White)
            Text("STRATEGY CORE  •  BUILD 0.7.0", color = Accent, fontSize = 11.sp)

            Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(18.dp)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("PRUEBA EN TELÉFONO", color = Accent, fontSize = 12.sp)
                    Text("Captura: $captureStatus", fontSize = 12.sp)
                    Button(onClick = {
                        val manager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                        captureLauncher.launch(manager.createScreenCaptureIntent())
                    }, modifier = Modifier.fillMaxWidth()) { Text("Iniciar captura de pantalla") }
                    OutlinedButton(onClick = {
                        context.startService(Intent(context, ScreenCaptureService::class.java).setAction(ScreenCaptureService.ACTION_STOP))
                        captureStatus = "Captura detenida"
                    }, modifier = Modifier.fillMaxWidth()) { Text("Detener captura") }
                    Text("Control táctil: ${if (accessibilityReady) "Servicio activado" else "No activado"}", fontSize = 12.sp)
                    OutlinedButton(onClick = { context.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }, modifier = Modifier.fillMaxWidth()) {
                        Text("Abrir ajustes de Accesibilidad")
                    }
                    OutlinedButton(onClick = {
                        try {
                            val source = File(context.filesDir, "latest_frame.jpg")
                            if (!source.exists()) throw IllegalStateException("Aún no hay fotograma capturado")
                            val values = ContentValues().apply {
                                put(MediaStore.Images.Media.DISPLAY_NAME, "BrawlBot_frame_${System.currentTimeMillis()}.jpg")
                                put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                                put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/BrawlBotAI")
                            }
                            val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                                ?: throw IllegalStateException("No se pudo crear el archivo en Galería")
                            context.contentResolver.openOutputStream(uri)?.use { out -> FileInputStream(source).use { it.copyTo(out) } }
                                ?: throw IllegalStateException("No se pudo guardar el fotograma")
                            output = "Fotograma guardado en Galería: Pictures/BrawlBotAI"
                        } catch (e: Exception) { output = "No se pudo guardar: ${e.message}" }
                    }, modifier = Modifier.fillMaxWidth()) { Text("Guardar último fotograma en Galería") }
                    OutlinedButton(onClick = {
                        accessibilityReady = prefs.getBoolean("accessibility_ready", false)
                        captureStatus = prefs.getString("capture_status", "No iniciada") ?: "No iniciada"
                        controlStatus = prefs.getString("control_status", "Sin probar") ?: "Sin probar"
                    }, modifier = Modifier.fillMaxWidth()) { Text("Actualizar estado") }
                    OutlinedButton(onClick = {
                        val test = Intent(GameControlService.ACTION_TEST_SWIPE).setPackage(context.packageName)
                            .putExtra("x1", .18f).putExtra("y1", .78f).putExtra("x2", .18f).putExtra("y2", .60f)
                        context.sendBroadcast(test)
                        controlStatus = "Prueba enviada; revisa el resultado"
                    }, enabled = accessibilityReady, modifier = Modifier.fillMaxWidth()) { Text("Probar movimiento táctil (solo cuando tú lo pulses)") }
                    Text("Control: $controlStatus", fontSize = 11.sp, color = Color.LightGray)
                    Text("La captura requiere permiso explícito. El servicio táctil se activa manualmente en Ajustes. No hay automatización autónoma todavía.", fontSize = 10.sp, color = Color.LightGray)
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = Panel),
                shape = RoundedCornerShape(18.dp)
            ) {
                Column(
                    Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Conexión al servidor", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(
                        baseUrl,
                        { baseUrl = it },
                        label = { Text("URL del backend") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        apiKey,
                        { apiKey = it },
                        label = { Text("API key (si está configurada)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    Button(
                        onClick = { call("/health") },
                        enabled = !busy,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (busy) "Consultando..." else "Comprobar conexión")
                    }
                }
            }

            Text("CEREBROS Y MODELOS", color = Accent, fontSize = 12.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ActionButton("Brain Status", Modifier.weight(1f)) {
                    call("/api/v1/brains/status")
                }
                ActionButton("List Models", Modifier.weight(1f)) {
                    call("/api/v1/models")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ActionButton("Metrics", Modifier.weight(1f)) {
                    call("/api/v1/metrics")
                }
                ActionButton("Catalog", Modifier.weight(1f)) {
                    call("/api/v1/catalog")
                }
            }

            Text("CONOCIMIENTO EN INTERNET", color = Accent, fontSize = 12.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ActionButton("Knowledge Status", Modifier.weight(1f)) {
                    call("/api/v1/knowledge/status")
                }
                ActionButton("Actualizar datos", Modifier.weight(1f)) {
                    call("/api/v1/knowledge/refresh?force=true", "{}")
                }
            }

            Text("CENTRO DE ANÁLISIS", color = Accent, fontSize = 12.sp)
            OutlinedTextField(
                modeInput, { modeInput = it }, label = { Text("Modo de juego") },
                modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            OutlinedTextField(
                mapInput, { mapInput = it }, label = { Text("Mapa") },
                modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            OutlinedTextField(
                ownedInput, { ownedInput = it }, label = { Text("Tus Brawlers (separados por coma; vacío = todos)") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                enemyInput, { enemyInput = it }, label = { Text("Picks enemigos (separados por coma)") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                allyInput, { allyInput = it }, label = { Text("Aliados ya elegidos (separados por coma)") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                bansInput, { bansInput = it }, label = { Text("Bans (separados por coma)") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                rankInput, { rankInput = it }, label = { Text("Rango competitivo (opcional)") },
                modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            val ownedList = ownedInput.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            val enemyList = enemyInput.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            val allyList = allyInput.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            val bansList = bansInput.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ActionButton("Smart Draft", Modifier.weight(1f)) {
                    val request = JSONObject()
                        .put("mode", modeInput)
                        .put("map_name", mapInput)
                        .put("owned_brawlers", JSONArray(ownedList))
                        .put("enemy_picks", JSONArray(enemyList))
                        .put("ally_picks", JSONArray(allyList))
                        .put("bans", JSONArray(bansList))
                        .put("ranked_tier", if (rankInput.isBlank()) JSONObject.NULL else rankInput)
                        .put("team_size", 3)
                    call("/api/v1/draft", request.toString())
                }
                ActionButton("Team Analysis", Modifier.weight(1f)) {
                    val team = ownedList.take(3)
                    if (team.isEmpty()) {
                        output = "Escribe al menos un Brawler en Tus Brawlers para analizar el equipo."
                    } else {
                        val request = JSONObject()
                            .put("mode", modeInput)
                            .put("map_name", mapInput)
                            .put("team", JSONArray(team))
                        call("/api/v1/team/analyze", request.toString())
                    }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ActionButton("Agent Decision", Modifier.weight(1f)) {
                    call(
                        "/api/v1/agent/decide",
                        """{"x":0.3,"y":0.5,"health":0.8,"ammo":3,"enemy_x":0.8,"enemy_y":0.5,"objective_x":0.5,"objective_y":0.5,"mode":"gem_grab","under_pressure":false}"""
                    )
                }
                ActionButton("Run Simulation", Modifier.weight(1f)) {
                    call("/api/v1/simulator/episode")
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = Panel),
                shape = RoundedCornerShape(18.dp)
            ) {
                Column(
                    Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Respuesta del sistema", style = MaterialTheme.typography.titleMedium)
                    Text(output, color = Color(0xFFD8D9E2), fontSize = 12.sp)
                }
            }

            Text(
                "La capa 0.7.0 añade captura autorizada de pantalla y un puente de gestos explícito para pruebas. La interpretación automática de Brawlers y la conducción autónoma de partidas siguen pendientes de calibración y validación.",
                color = Color.LightGray,
                fontSize = 11.sp
            )
        }
    }
}

@Composable
fun ActionButton(label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = modifier.height(54.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        Text(label, fontSize = 12.sp)
    }
}

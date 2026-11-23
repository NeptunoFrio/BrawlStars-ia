package com.brawlbot.ai

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.app.PendingIntent
import android.util.DisplayMetrics
import android.view.WindowManager
import java.io.File
import java.io.FileOutputStream

/** User-approved screen capture. Frames are stored locally; nothing is uploaded automatically. */
class ScreenCaptureService : Service() {
    private var projection: MediaProjection? = null
    private var reader: ImageReader? = null
    private var display: VirtualDisplay? = null
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var frameCount = 0
    private var stopping = false
    private var lastSavedAt = 0L

    override fun onBind(intent: Intent?) = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) { stopCapture(); return START_NOT_STICKY }
        startForeground(NOTIFICATION_ID, notification())
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, Activity.RESULT_CANCELED) ?: Activity.RESULT_CANCELED
        @Suppress("DEPRECATION")
        val data = intent?.getParcelableExtra<Intent>(EXTRA_DATA)
        if (resultCode != Activity.RESULT_OK || data == null) {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("capture_status", "Permiso de captura no concedido").apply()
            stopSelf(); return START_NOT_STICKY
        }
        startCapture(resultCode, data)
        return START_STICKY
    }

    private fun startCapture(resultCode: Int, data: Intent) {
        try {
            val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            projection = manager.getMediaProjection(resultCode, data)
            val metrics = DisplayMetrics()
            @Suppress("DEPRECATION")
            (getSystemService(Context.WINDOW_SERVICE) as WindowManager).defaultDisplay.getRealMetrics(metrics)
            val width = metrics.widthPixels
            val height = metrics.heightPixels
            val density = metrics.densityDpi
            thread = HandlerThread("BrawlBotFrameCapture").also { it.start() }
            handler = Handler(thread!!.looper)
            reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            reader!!.setOnImageAvailableListener({ source ->
                val image = source.acquireLatestImage() ?: return@setOnImageAvailableListener
                try { saveFrame(image) } catch (_: Exception) { }
                finally { image.close() }
            }, handler)
            projection!!.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() { stopCapture() }
            }, handler)
            display = projection!!.createVirtualDisplay("BrawlBotScreen", width, height, density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, reader!!.surface, null, handler)
            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString("capture_status", "Capturando pantalla")
                .putInt("capture_width", width).putInt("capture_height", height).apply()
        } catch (e: Exception) {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("capture_status", "Error: ${e.message}").apply()
            stopCapture()
        }
    }

    private fun saveFrame(image: Image) {
        val now = SystemClock.elapsedRealtime()
        if (now - lastSavedAt < 500L) return // Limit diagnostic writes to 2 frames/second.
        lastSavedAt = now
        val plane = image.planes[0]
        val buffer = plane.buffer
        val pixelStride = plane.pixelStride
        val rowStride = plane.rowStride
        val rowPadding = rowStride - pixelStride * image.width
        val paddedWidth = image.width + rowPadding / pixelStride
        val padded = Bitmap.createBitmap(paddedWidth, image.height, Bitmap.Config.ARGB_8888)
        buffer.rewind()
        padded.copyPixelsFromBuffer(buffer)
        val bitmap = Bitmap.createBitmap(padded, 0, 0, image.width, image.height)
        padded.recycle()
        val file = File(filesDir, "latest_frame.jpg")
        FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.JPEG, 75, it) }
        bitmap.recycle()
        frameCount++
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
            .putString("capture_status", "Capturando pantalla · $frameCount fotogramas")
            .putLong("last_frame_at", System.currentTimeMillis())
            .putLong("last_frame_bytes", file.length()).apply()
    }

    private fun notification(): Notification {
        val channelId = "brawlbot_capture"
        if (Build.VERSION.SDK_INT >= 26) {
            val channel = NotificationChannel(channelId, "Captura de pantalla BrawlBot", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
        val testIntent = Intent(this, GestureCommandReceiver::class.java).setAction(GameControlService.ACTION_TEST_SWIPE)
        val testPending = PendingIntent.getBroadcast(this, 742, testIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, channelId)
            .setContentTitle("BrawlBot AI")
            .setContentText("Captura activa. Acción manual disponible desde esta notificación.")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .addAction(Notification.Action.Builder(android.R.drawable.ic_media_play, "Probar gesto", testPending).build())
            .setOngoing(true).build()
    }

    private fun stopCapture() {
        if (stopping) return
        stopping = true
        try { display?.release() } catch (_: Exception) { }
        display = null
        try { reader?.close() } catch (_: Exception) { }
        reader = null
        val activeProjection = projection
        projection = null
        try { activeProjection?.stop() } catch (_: Exception) { }
        thread?.quitSafely(); thread = null; handler = null
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("capture_status", "Captura detenida").apply()
        if (Build.VERSION.SDK_INT >= 24) stopForeground(STOP_FOREGROUND_REMOVE) else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
        stopping = false
    }

    override fun onDestroy() { if (projection != null || reader != null) stopCapture(); super.onDestroy() }

    companion object {
        const val ACTION_START = "com.brawlbot.ai.CAPTURE_START"
        const val ACTION_STOP = "com.brawlbot.ai.CAPTURE_STOP"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_DATA = "projection_data"
        const val PREFS = "brawlbot_runtime"
        private const val NOTIFICATION_ID = 741
    }
}

package com.brawlbot.ai

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.*
import android.graphics.Path
import android.os.Build
import android.view.accessibility.AccessibilityEvent

/** Explicit, user-enabled accessibility bridge. It does not hide itself or bypass game protections. */
class GameControlService : AccessibilityService() {
    private val actionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != ACTION_TEST_SWIPE) return
            val x1 = intent.getFloatExtra("x1", .5f).coerceIn(0f, 1f)
            val y1 = intent.getFloatExtra("y1", .75f).coerceIn(0f, 1f)
            val x2 = intent.getFloatExtra("x2", .5f).coerceIn(0f, 1f)
            val y2 = intent.getFloatExtra("y2", .55f).coerceIn(0f, 1f)
            val dm = resources.displayMetrics
            val path = Path().apply { moveTo(x1 * dm.widthPixels, y1 * dm.heightPixels); lineTo(x2 * dm.widthPixels, y2 * dm.heightPixels) }
            val gesture = GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, 350)).build()
            val accepted = dispatchGesture(gesture, null, null)
            getSharedPreferences(ScreenCaptureService.PREFS, MODE_PRIVATE).edit()
                .putString("control_status", if (accepted) "Gesto enviado" else "Android rechazó el gesto").apply()
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        val filter = IntentFilter(ACTION_TEST_SWIPE)
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(actionReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        else {
            @Suppress("DEPRECATION")
            registerReceiver(actionReceiver, filter)
        }
        getSharedPreferences(ScreenCaptureService.PREFS, MODE_PRIVATE).edit().putBoolean("accessibility_ready", true).apply()
    }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) { }
    override fun onInterrupt() { }
    override fun onDestroy() {
        try { unregisterReceiver(actionReceiver) } catch (_: Exception) { }
        getSharedPreferences(ScreenCaptureService.PREFS, MODE_PRIVATE).edit().putBoolean("accessibility_ready", false).apply()
        super.onDestroy()
    }

    companion object { const val ACTION_TEST_SWIPE = "com.brawlbot.ai.TEST_SWIPE" }
}

package com.brawlbot.ai

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Notification action bridge; only runs after the user taps the notification action. */
class GestureCommandReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != GameControlService.ACTION_TEST_SWIPE) return
        val command = Intent(GameControlService.ACTION_TEST_SWIPE).setPackage(context.packageName)
            .putExtra("x1", .18f).putExtra("y1", .78f).putExtra("x2", .18f).putExtra("y2", .60f)
        context.sendBroadcast(command)
    }
}

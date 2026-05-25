package com.voicebutton

import android.content.Context
import android.os.Build
import java.io.PrintWriter
import java.io.StringWriter
import java.net.HttpURLConnection
import java.net.URL

class CrashReporter(private val context: Context) {

    companion object {
        private var savedServerUrl: String? = null

        fun getServerUrl(context: Context): String {
            savedServerUrl?.let { return it }
            val url = context.getSharedPreferences("crash_prefs", Context.MODE_PRIVATE)
                .getString("server_url", null)
            if (url != null) {
                savedServerUrl = url
                return url
            }
            val fallback = "http://100.102.52.59:9099"
            setServerUrl(context, fallback)
            return fallback
        }

        fun setServerUrl(context: Context, url: String) {
            savedServerUrl = url
            context.getSharedPreferences("crash_prefs", Context.MODE_PRIVATE)
                .edit().putString("server_url", url).apply()
        }
    }

    /** Sends crash report synchronously (blocking). Call from exception handler. */
    fun sendCrashReportSync(thread: Thread, throwable: Throwable): Boolean {
        val sw = StringWriter()
        throwable.printStackTrace(PrintWriter(sw))
        val stacktrace = sw.toString()
        val message = throwable.message ?: "Unknown"
        val detail = "${throwable.javaClass.name}: $message"

        val data = mapOf(
            "type" to "crash",
            "message" to message,
            "detail" to detail,
            "stacktrace" to stacktrace,
            "device" to getDeviceInfo(),
            "app_version" to "1.0"
        )
        return sendToServerSync(data)
    }

    fun sendFeatureRequest(description: String) {
        val data = mapOf(
            "type" to "feature",
            "message" to description,
            "detail" to "Feature request / improvement",
            "device" to getDeviceInfo(),
            "app_version" to "1.0"
        )
        Thread {
            sendToServerSync(data)
        }.apply { isDaemon = false }.start()
    }

    fun sendManualErrorReport(description: String, detail: String = "") {
        val data = mapOf(
            "type" to "manual",
            "message" to description,
            "detail" to detail,
            "device" to getDeviceInfo(),
            "app_version" to "1.0"
        )
        Thread {
            sendToServerSync(data)
        }.apply { isDaemon = false }.start()
    }

    private fun sendToServerSync(data: Map<String, String>): Boolean {
        return try {
            val urlStr = getServerUrl(context)
            val url = URL("$urlStr/report")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.connectTimeout = 3000
            conn.readTimeout = 3000
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            val json = buildJson(data)
            conn.outputStream.write(json.toByteArray(Charsets.UTF_8))
            conn.outputStream.flush()
            val ok = conn.responseCode in 200..299
            conn.disconnect()
            ok
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    private fun buildJson(map: Map<String, String>): String {
        val sb = StringBuilder("{")
        var first = true
        for ((k, v) in map) {
            if (!first) sb.append(",")
            first = false
            sb.append("\"${escape(k)}\":\"${escape(v)}\"")
        }
        sb.append("}")
        return sb.toString()
    }

    private fun escape(s: String): String {
        return s.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    }

    private fun getDeviceInfo(): String {
        return "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}), " +
                "${Build.MANUFACTURER} ${Build.MODEL}, ${Build.BRAND}"
    }
}

class VoiceButtonsExceptionHandler(private val reporter: CrashReporter) :
    Thread.UncaughtExceptionHandler {

    private val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()

    override fun uncaughtException(thread: Thread, throwable: Throwable) {
        // Synchronous crash report before the app dies
        reporter.sendCrashReportSync(thread, throwable)
        try {
            Thread.sleep(800) // Give time for network
        } catch (_: InterruptedException) {}
        defaultHandler?.uncaughtException(thread, throwable) ?: kotlin.system.exitProcess(1)
    }
}

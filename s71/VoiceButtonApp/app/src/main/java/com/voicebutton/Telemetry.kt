package com.voicebutton

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import java.net.HttpURLConnection
import java.net.URL

class Telemetry(private val context: Context) {

    fun evento(desc: String) {
        send("evento", desc, "", "")
    }

    fun estado(elemento: String, valor: String) {
        val v = if (valor.length > 10) valor.take(10) + "..." else valor
        send("estado", elemento, v, "")
    }

    fun resultado(elemento: String, cambio: String) {
        send("resultado", elemento, cambio, "")
    }

    fun destroy() {}

    private fun send(type: String, msg: String, detail: String, extra: String) {
        Thread {
            try {
                val urlStr = CrashReporter.getServerUrl(context)
                val conn = URL("$urlStr/report").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"; conn.doOutput = true
                conn.connectTimeout = 3000; conn.readTimeout = 3000
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                val data = """{"type":"$type","message":"${jsonEsc(msg)}","detail":"${jsonEsc(detail)}","extra":"${jsonEsc(extra)}","device":"${jsonEsc(getDeviceInfo())}","app_version":"1.0"}"""
                conn.outputStream.write(data.toByteArray(Charsets.UTF_8))
                conn.outputStream.flush(); conn.disconnect()
            } catch (e: Exception) {
                android.util.Log.e("Telemetry", "send $type failed", e)
            }
        }.apply { isDaemon = false }.start()
    }

    private fun jsonEsc(s: String) = s.replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")

    private fun getDeviceInfo() = "Android ${android.os.Build.VERSION.RELEASE}, ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"
}

package com.voicebutton

import android.animation.ValueAnimator
import android.app.*
import android.content.*
import android.graphics.PixelFormat
import android.os.*
import android.speech.*
import android.view.*
import android.widget.*
import androidx.core.app.NotificationCompat
import java.io.PrintWriter
import java.io.StringWriter

class FloatingButtonService : Service() {

    private lateinit var windowManager: WindowManager
    private var overlayView: View? = null
    private lateinit var storage: ButtonStorage
    private lateinit var telemetry: Telemetry
    private var isExpanded = false

    private var isDragging = false
    private var dragStartX = 0f
    private var dragStartY = 0f
    private var offsetX = 0f
    private var offsetY = 0f

    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    private var voiceAnimator: ValueAnimator? = null
    private var voiceBaseText = ""
    private var voiceSuffixText = ""

    companion object {
        const val CHANNEL_ID = "floating_service"
        const val NOTIF_ID = 1001
        var accessibilityService: ActionAccessibilityService? = null
        var refreshCallback: (() -> Unit)? = null
        val logBuffer = java.util.Collections.synchronizedList(mutableListOf<String>())
        private var serviceInstance: FloatingButtonService? = null

        fun voiceDone() {
            serviceInstance?.apply { isListening = false; showVoiceFeedback(false) }
        }

        fun addLog(msg: String) {
            val entry = "${java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date())} $msg"
            logBuffer.add(entry)
            if (logBuffer.size > 100) logBuffer.removeAt(0)
            Thread {
                try {
                    val c = java.net.URL("http://100.102.52.59:9099/report").openConnection() as java.net.HttpURLConnection
                    c.requestMethod = "POST"; c.doOutput = true
                    c.connectTimeout = 2000; c.readTimeout = 2000
                    c.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    c.outputStream.write(("""{"type":"evento","message":"${entry.replace("\"","\\\"").replace("\n","\\n")}","detail":"log","device":"Android"}""").toByteArray(Charsets.UTF_8))
                    c.outputStream.flush(); c.disconnect()
                } catch (_: Exception) {}
            }.apply { isDaemon = false }.start()
        }
    }

    override fun onCreate() {
        super.onCreate()
        serviceInstance = this
        try {
            storage = ButtonStorage(this); telemetry = Telemetry(this)
            windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
            createNotificationChannel(); startForeground(NOTIF_ID, createNotification())
        } catch (_: Exception) {}
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (overlayView == null || overlayView!!.parent == null) {
            try { showOverlay(); addLog("Panel iniciado") }
            catch (e: Exception) { sendCrashToServer("showOverlay", e); stopSelf() }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopListening()
        try { overlayView?.let { if (it.parent != null) windowManager.removeView(it) } } catch (_: Exception) {}
        overlayView = null; super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) try {
            val ch = NotificationChannel(CHANNEL_ID, "Panel", NotificationManager.IMPORTANCE_LOW)
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(ch)
        } catch (_: Exception) {}
    }

    private fun createNotification(): Notification {
        val pi = PendingIntent.getActivity(this, 0,
            packageManager.getLaunchIntentForPackage(packageName),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("VoiceButtons").setContentText("Panel activo")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pi).setOngoing(true).build()
    }

    private fun showOverlay() {
        val view = (getSystemService(LAYOUT_INFLATER_SERVICE) as LayoutInflater).inflate(R.layout.overlay_buttons, null)
        val prefs = getSharedPreferences("overlay", MODE_PRIVATE)
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT)
        params.gravity = Gravity.TOP or Gravity.START
        params.x = prefs.getInt("pos_x", 50); params.y = prefs.getInt("pos_y", 200)
        windowManager.addView(view, params); overlayView = view; setupOverlay(view, params)
    }

    private fun setupOverlay(view: View, params: WindowManager.LayoutParams) {
        val toggle = view.findViewById<TextView>(R.id.btnToggle)
        val container = view.findViewById<LinearLayout>(R.id.buttonContainer)
        val dp = resources.displayMetrics.density; val ts = (44 * dp).toInt()
        toggle.layoutParams = FrameLayout.LayoutParams(ts, ts); toggle.gravity = Gravity.CENTER
        val s = android.graphics.drawable.GradientDrawable().apply {
            setShape(android.graphics.drawable.GradientDrawable.OVAL); setColor(0xFF444444.toInt()) }
        toggle.background = s; toggle.clipToOutline = true
        // Restaurar estado expandido
        val prefs = getSharedPreferences("overlay", MODE_PRIVATE)
        isExpanded = prefs.getBoolean("is_expanded", false)
        container.visibility = if (isExpanded) View.VISIBLE else View.GONE
        toggle.text = if (isExpanded) "\u25BC" else "\u25B2"
        if (isExpanded) refreshButtons(container)
        view.setOnTouchListener { v, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> { isDragging = false; dragStartX = event.rawX; dragStartY = event.rawY; offsetX = event.rawX - params.x; offsetY = event.rawY - params.y; true }
                MotionEvent.ACTION_MOVE -> { if (Math.abs(event.rawX - dragStartX) > 12 || Math.abs(event.rawY - dragStartY) > 12) { isDragging = true; params.x = (event.rawX - offsetX).toInt(); params.y = (event.rawY - offsetY).toInt(); windowManager.updateViewLayout(v, params); getSharedPreferences("overlay", MODE_PRIVATE).edit().putInt("pos_x", params.x).putInt("pos_y", params.y).apply() }; true }
                MotionEvent.ACTION_UP -> { if (!isDragging) { isExpanded = !isExpanded; container.visibility = if (isExpanded) View.VISIBLE else View.GONE; toggle.text = if (isExpanded) "\u25BC" else "\u25B2"; getSharedPreferences("overlay", MODE_PRIVATE).edit().putBoolean("is_expanded", isExpanded).apply(); if (isExpanded) refreshButtons(container) }; isDragging = false; true }
                MotionEvent.ACTION_CANCEL -> { isDragging = false; true }; else -> true
            }
        }
        refreshCallback = { if (isExpanded) refreshButtons(container) }
    }

    private fun refreshButtons(c: LinearLayout) {
        while (c.childCount > 0) c.removeViewAt(0)
        val dp = resources.displayMetrics.density; val sz = (44 * dp).toInt()
        for (b in storage.loadButtons()) {
            val btn = Button(this).apply {
                text = iconFor(b); textSize = 17f; setAllCaps(false); gravity = Gravity.CENTER
                layoutParams = LinearLayout.LayoutParams(sz, sz).apply { setMargins(0, 0, 0, (4 * dp).toInt()) }
                setOnClickListener { executeAction(b) }; setOnLongClickListener { showDeleteOption(b); true }
                val sh = android.graphics.drawable.GradientDrawable().apply { setShape(android.graphics.drawable.GradientDrawable.OVAL); setColor(0xFF444444.toInt()); setStroke(2, 0xFF777777.toInt()) }
                background = sh; clipToOutline = true; setPadding(0, 0, 0, 0)
            }
            c.addView(btn)
        }
    }

    private fun iconFor(c: ButtonConfig): String {
        val first = c.label.codePointAt(0)
        if (first > 0x00FF) return String(Character.toChars(first))
        return when (c.actionType) { "voice" -> "\uD83C\uDFA4"; "enter" -> "\u23CE"; "text" -> "\uD83D\uDCDD"; "key" -> "\uD83D\uDD11"; else -> c.label.take(1) }
    }

    private fun executeAction(c: ButtonConfig) {
        addLog("Ejecutando: ${c.label}")
        when (c.actionType) {
            "text" -> accessibilityService?.injectText(c.action)
            "key" -> { for (p in c.action.split(" ", "+")) { parseKeyCode(p.trim())?.let { accessibilityService?.injectKeyEvent(it) } } }
            "voice" -> startListening(c)
            "enter" -> accessibilityService?.injectEnter()
            else -> accessibilityService?.injectText(c.action)
        }
    }

    private fun parseKeyCode(s: String): Int? = when (s.uppercase()) {
        "ENTER" -> KeyEvent.KEYCODE_ENTER; "BACK" -> KeyEvent.KEYCODE_BACK; "HOME" -> KeyEvent.KEYCODE_HOME
        "TAB" -> KeyEvent.KEYCODE_TAB; "UP" -> KeyEvent.KEYCODE_DPAD_UP; "DOWN" -> KeyEvent.KEYCODE_DPAD_DOWN
        "LEFT" -> KeyEvent.KEYCODE_DPAD_LEFT; "RIGHT" -> KeyEvent.KEYCODE_DPAD_RIGHT
        "DELETE", "DEL" -> KeyEvent.KEYCODE_DEL; "SPACE" -> KeyEvent.KEYCODE_SPACE
        "ESC" -> KeyEvent.KEYCODE_ESCAPE; "F5" -> KeyEvent.KEYCODE_F5; else -> s.toIntOrNull()
    }

    /* Voz directa con SpeechRecognizer */
    private fun startListening(config: ButtonConfig? = null) {
        if (isListening) { stopListening(); return }
        try {
            addLog("Iniciando SpeechRecognizer...")
            // Capturar texto y posici�n del cursor al inicio
            val state = accessibilityService?.getFieldState()
            // Si cursorStart/End son -1 el campo est� vac�o (solo hint), ignorar texto
            if (state != null && (state.cursorStart < 0 || state.cursorEnd < 0)) {
                voiceBaseText = ""; voiceSuffixText = ""
                addLog("campo vac�o (solo hint)")
            } else
            if (state != null) {
                voiceBaseText = state.text.substring(0, state.cursorStart.coerceIn(0, state.text.length))
                voiceSuffixText = state.text.substring(state.cursorEnd.coerceIn(0, state.text.length))
                // Espacio entre grabaciones si el texto base no termina con espacio
                if (voiceBaseText.isNotEmpty() && !voiceBaseText.endsWith(" ") && !voiceBaseText.endsWith("\n")) {
                    voiceBaseText += " "
                }
                addLog("base='${voiceBaseText}' suffix='${voiceSuffixText}'")
            } else {
                voiceBaseText = ""; voiceSuffixText = ""
            }
            if (speechRecognizer != null) speechRecognizer?.destroy()
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
            if (speechRecognizer == null) { addLog("ERROR: SpeechRecognizer null"); return }
            speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(p: Bundle?) { addLog("onReadyForSpeech"); isListening = true }
                override fun onBeginningOfSpeech() { addLog("onBeginningOfSpeech") }
                override fun onRmsChanged(v: Float) {}
                override fun onBufferReceived(b: ByteArray?) {}
                override fun onEndOfSpeech() { addLog("onEndOfSpeech") }
                override fun onError(code: Int) {
                    addLog("onError: $code"); isListening = false; showVoiceFeedback(false)
                    voiceBaseText = ""; voiceSuffixText = ""
                    Toast.makeText(this@FloatingButtonService, when (code) { SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Permiso denegado"; SpeechRecognizer.ERROR_NETWORK -> "Error de red"; SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Sin voz"; else -> "Error $code" }, Toast.LENGTH_SHORT).show()
                }
                override fun onPartialResults(partial: Bundle?) {
                    addLog("onPartialResults")
                    val text = partial?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                    if (text != null && text.isNotEmpty()) {
                        addLog("parcial='$text'")
                        // Reemplazar completo (base + hip�tesis + suffix) sin duplicar
                        val full = voiceBaseText + text + voiceSuffixText
                        if (!(accessibilityService?.setFieldText(full) ?: false)) {
                            // Fallback: clipboard+paste cuando setFieldText no funciona
                            accessibilityService?.pasteText("$text ")
                        }
                        addLog("campo ahora='${full.take(60)}'")
                    }
                }
                override fun onEvent(t: Int, b: Bundle?) {}
                override fun onResults(results: Bundle?) {
                    addLog("onResults")
                    isListening = false; showVoiceFeedback(false)
                    val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                    if (text != null && text.isNotEmpty()) {
                        addLog("final: \"$text\"")
                        val full = voiceBaseText + text + voiceSuffixText
                        if (!(accessibilityService?.setFieldText(full) ?: false)) {
                            accessibilityService?.pasteText(text)
                        }
                    }
                    voiceBaseText = ""; voiceSuffixText = ""
                }
            })
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 5000L)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 500L)
                config?.let { putExtra(RecognizerIntent.EXTRA_LANGUAGE, it.language) }
            }
            speechRecognizer?.startListening(intent)
            addLog("startListening enviado"); showVoiceFeedback(true)
        } catch (e: Exception) { addLog("EXCEPCION: ${e.message}"); isListening = false; showVoiceFeedback(false) }
    }

    private fun stopListening() {
        addLog("stopListening")
        try { speechRecognizer?.stopListening(); speechRecognizer?.destroy() } catch (_: Exception) {}
        speechRecognizer = null; isListening = false; showVoiceFeedback(false)
    }

    private fun showVoiceFeedback(on: Boolean) {
        val container = overlayView?.findViewById<LinearLayout>(R.id.buttonContainer) ?: return
        voiceAnimator?.cancel()
        var target: Button? = null
        for (i in 0 until container.childCount) {
            val b = container.getChildAt(i) as? Button
            if ((b?.text?.toString() ?: "").contains("\uD83C\uDFA4")) { target = b; break }
        }
        if (on && target != null) {
            val bg = target.background as? android.graphics.drawable.GradientDrawable
            voiceAnimator = ValueAnimator.ofInt(0x44, 0xCC).apply {
                duration = 600; repeatMode = ValueAnimator.REVERSE; repeatCount = ValueAnimator.INFINITE
                addUpdateListener { a -> bg?.setColor(android.graphics.Color.argb(a.animatedValue as Int, 0x33, 0x99, 0xFF)) }
                start()
            }
        } else {
            for (i in 0 until container.childCount) {
                val b = container.getChildAt(i) as? Button
                (b?.background as? android.graphics.drawable.GradientDrawable)?.setColor(0xFF444444.toInt())
            }
            voiceAnimator = null
        }
    }

    private fun showDeleteOption(config: ButtonConfig) {
        try { AlertDialog.Builder(this).setTitle("Eliminar?").setMessage(config.label).setPositiveButton("Eliminar") { _, _ -> storage.removeButton(config.id); overlayView?.findViewById<LinearLayout>(R.id.buttonContainer)?.let { refreshButtons(it) } }.setNegativeButton("Cancelar", null).show() } catch (_: Exception) {}
    }

    private fun sendCrashToServer(ctx: String, err: Throwable) {
        val sw = StringWriter(); err.printStackTrace(PrintWriter(sw))
        val url = try { CrashReporter.getServerUrl(this) } catch (_: Exception) { "http://100.102.52.59:9099" }
        try {
            val c = java.net.URL("$url/report").openConnection() as java.net.HttpURLConnection
            c.requestMethod = "POST"; c.doOutput = true; c.connectTimeout = 3000; c.readTimeout = 3000
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            c.outputStream.write(("""{"type":"crash","message":"${err.message?.replace("\"","\\\"") ?: "null"}","detail":"$ctx","stacktrace":"${sw.toString().replace("\"","\\\"").replace("\n","\\n")}","device":"Android ${Build.VERSION.RELEASE} ${Build.MANUFACTURER} ${Build.MODEL}","app_version":"1.0"}""").toByteArray(Charsets.UTF_8))
            c.outputStream.flush(); c.disconnect()
        } catch (_: Exception) {}
    }
}

package com.voicebutton

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognizerIntent
import android.view.MotionEvent
import android.view.View
import android.view.LayoutInflater
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class MainActivity : AppCompatActivity() {

    private lateinit var storage: ButtonStorage
    private lateinit var adapter: ButtonAdapter
    private lateinit var crashReporter: CrashReporter
    private lateinit var telemetry: Telemetry
    private var isServiceRunning = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        storage = ButtonStorage(this)
        crashReporter = CrashReporter(this)
        telemetry = Telemetry(this)

        Thread.setDefaultUncaughtExceptionHandler(VoiceButtonsExceptionHandler(crashReporter))
        telemetry.evento("App abierta")

        // Solicitar permiso de micr├│fono si no est├í concedido
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
            checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
                android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 2001)
        }

        if (intent?.getStringExtra("action") == "speech") {
            startVoiceRecognition()
            return
        }
        if (intent?.getStringExtra("action") == "request_mic") {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
                checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
                    android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 2001)
            }
            return
        }

        val btnToggle = findViewById<Button>(R.id.btnToggleOverlay)
        val btnAccessibility = findViewById<Button>(R.id.btnOpenAccessibility)
        val btnAdd = findViewById<Button>(R.id.btnAddButton)
        val btnReport = findViewById<Button>(R.id.btnReport)
        val recycler = findViewById<RecyclerView>(R.id.recyclerButtons)
        val tvStatus = findViewById<TextView>(R.id.tvStatus)

        adapter = ButtonAdapter(
            storage.loadButtons().toMutableList(),
            onEdit = { showButtonDialog(it) },
            onDelete = {
                storage.removeButton(it.id)
                telemetry.evento("Bot\u00f3n eliminado desde lista: ${it.label}")
                refreshList()
            },
            onMoveUp = { idx ->
                val list = storage.loadButtons().toMutableList()
                if (idx > 0) {
                    val item = list.removeAt(idx)
                    list.add(idx - 1, item)
                    storage.saveButtons(list)
                    refreshList()
                }
            },
            onMoveDown = { idx ->
                val list = storage.loadButtons().toMutableList()
                if (idx < list.size - 1) {
                    val item = list.removeAt(idx)
                    list.add(idx + 1, item)
                    storage.saveButtons(list)
                    refreshList()
                }
            }
        )

        recycler.layoutManager = LinearLayoutManager(this)
        recycler.adapter = adapter
        updateStatus(tvStatus)

        btnToggle.setOnClickListener {
            if (!isServiceRunning) {
                if (!checkOverlayPermission()) {
                    requestOverlayPermission()
                    return@setOnClickListener
                }
                startOverlayService()
            } else {
                stopOverlayService()
            }
        }

        // Restaurar estado del panel si estaba activo
        if (!isServiceRunning && getSharedPreferences("overlay", MODE_PRIVATE)
                .getBoolean("service_active", false)) {
            if (checkOverlayPermission()) startOverlayService()
        }

        btnAccessibility.setOnClickListener {
            telemetry.evento("Abriendo ajustes de accesibilidad")
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            Toast.makeText(this, "Activa 'VoiceButtons' en Accesibilidad", Toast.LENGTH_LONG).show()
        }

        btnAdd.setOnClickListener { showButtonDialog(null) }
        btnReport.setOnClickListener { showSuggestionDialog() }
        findViewById<Button>(R.id.btnConfigServer).setOnClickListener { showServerConfigDialog() }
        findViewById<Button>(R.id.btnLogs).setOnClickListener { showLogsDialog() }

        // Campo de prueba Enter: mostrar Toast cuando se dispara IME action
        findViewById<EditText>(R.id.etTestEnter).setOnEditorActionListener { _, actionId, _ ->
            telemetry.evento("Enter detectado en campo de prueba (action=$actionId)")
            Toast.makeText(this, "¡Enter detectado! actionId=$actionId", Toast.LENGTH_SHORT).show()
            true
        }

        // Redimensionar cajas de prueba con el asa
        val testContainer = findViewById<LinearLayout>(R.id.testContainer)
        val testPrefs = getSharedPreferences("test_area", MODE_PRIVATE)
        val savedH = testPrefs.getInt("height", 80)
        testContainer.layoutParams = testContainer.layoutParams.apply { height = savedH.coerceAtLeast(40) }
        findViewById<View>(R.id.dragHandle).setOnTouchListener(object : View.OnTouchListener {
            private var startY = 0f
            private var startH = 0
            override fun onTouch(v: View, event: MotionEvent): Boolean {
                return when (event.actionMasked) {
                    MotionEvent.ACTION_DOWN -> { startY = event.rawY; startH = testContainer.layoutParams.height; true }
                    MotionEvent.ACTION_MOVE -> {
                        val newH = (startH + (event.rawY - startY)).toInt()
                        testContainer.layoutParams = testContainer.layoutParams.apply { height = newH.coerceAtLeast(40) }
                        testContainer.requestLayout()
                        true
                    }
                    MotionEvent.ACTION_UP -> {
                        testPrefs.edit().putInt("height", testContainer.layoutParams.height).apply()
                        true
                    }
                    else -> false
                }
            }
        })
    }

    override fun onResume() {
        super.onResume()
        refreshList()
        // Re-verificar estado del panel al volver a la app
        if (!isServiceRunning && getSharedPreferences("overlay", MODE_PRIVATE)
                .getBoolean("service_active", false)) {
            if (checkOverlayPermission()) startOverlayService()
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        when (intent.getStringExtra("action")) {
            "speech" -> startVoiceRecognition()
            "request_mic" -> {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
                    checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
                        android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 2001)
                }
            }
        }
    }

    /* ─── Permisos ─── */

    private fun checkOverlayPermission() =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this)

    private fun requestOverlayPermission() {
        try {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
            Toast.makeText(this, "Activa \"Mostrar sobre otras apps\"", Toast.LENGTH_LONG).show()
        } catch (_: Exception) {
            try {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.parse("package:$packageName")
                })
            } catch (_: Exception) {
                Toast.makeText(this, "Ajustes > Apps > VoiceButtons > Mostrar sobre otras apps", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun startOverlayService() {
        try {
            startService(Intent(this, FloatingButtonService::class.java))
            isServiceRunning = true
            getSharedPreferences("overlay", MODE_PRIVATE).edit()
                .putBoolean("service_active", true).commit()
            telemetry.evento("Panel flotante iniciado desde MainActivity")
            findViewById<Button>(R.id.btnToggleOverlay).text = "Panel ON"
        } catch (e: Exception) {
            crashReporter.sendManualErrorReport("Error al iniciar panel", e.message ?: "")
            Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun stopOverlayService() {
        try {
            stopService(Intent(this, FloatingButtonService::class.java))
            isServiceRunning = false
            getSharedPreferences("overlay", MODE_PRIVATE).edit()
                .putBoolean("service_active", false).commit()
            telemetry.evento("Panel flotante detenido desde MainActivity")
            findViewById<Button>(R.id.btnToggleOverlay).text = "Panel OFF"
        } catch (_: Exception) {}
    }

    /* ─── Voz ─── */

    private fun startVoiceRecognition() {
        telemetry.evento("Voz iniciada desde MainActivity")
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Habla ahora...")
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        try {
            startActivityForResult(intent, 1001)
        } catch (e: Exception) {
            FloatingButtonService.voiceDone()
            Toast.makeText(this, "Reconocimiento de voz no disponible", Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 1001 && resultCode == RESULT_OK && data != null) {
            val results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            if (!results.isNullOrEmpty()) {
                val text = results[0]
                FloatingButtonService.accessibilityService?.injectText(text)
                telemetry.evento("Voz reconocida: \"${text.take(30)}\"")
                telemetry.resultado("voz", text.take(20))
                Toast.makeText(this, "Dictado: $text", Toast.LENGTH_SHORT).show()
            }
        }
        FloatingButtonService.voiceDone()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 2001 && grantResults.isNotEmpty() &&
            grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            telemetry.evento("Permiso de micr\u00F3fono concedido")
        }
    }

    /* ─── Lista de botones ─── */

    private fun refreshList() {
        val list = storage.loadButtons()
        adapter.update(list)
        val status = if (list.isEmpty()) "Sin botones" else "${list.size} botones"
        findViewById<TextView>(R.id.tvStatus).text = status
        try { FloatingButtonService.refreshCallback?.invoke() } catch (_: Exception) {}
    }

    private fun updateStatus(tv: TextView) {
        val list = storage.loadButtons()
        tv.text = if (list.isEmpty()) "Sin botones" else "${list.size} botones"
    }

    /* ─── Di├ílogo simplificado con iconos ─── */

    private data class IconPreset(
        val emoji: String, val label: String,
        val actionType: String, val action: String = ""
    )

    private val presets = listOf(
        IconPreset("\uD83C\uDFA4", "\uD83C\uDFA4 Voz", "voice"),
        IconPreset("\u23CE", "\u23CE Enter", "enter"),
        IconPreset("\u232B", "\u232B Delete", "key", "DEL"),
        IconPreset("\u2B05\uFE0F", "\u2B05\uFE0F Atr\u00e1s", "key", "BACK"),
        IconPreset("\uD83C\uDFE0", "\uD83C\uDFE0 Home", "key", "HOME"),
        IconPreset("\u21B9", "\u21B9 Tabulador", "key", "TAB"),
        IconPreset("\u2B06\uFE0F", "\u2B06\uFE0F Arriba", "key", "UP"),
        IconPreset("\u2B07\uFE0F", "\u2B07\uFE0F Abajo", "key", "DOWN"),
        IconPreset("\u23F5", "\u23F5 Reproducir", "key", "ENTER"),
        IconPreset("\u23F8\uFE0F", "\u23F8\uFE0F Pausa", "key", "SPACE"),
        IconPreset("\uD83D\uDCDD", "\uD83D\uDCDD Texto", "text", ""),
        IconPreset("\uD83D\uDD11", "\uD83D\uDD11 Tecla", "key", ""),
        IconPreset("\uD83D\uDD04", "\uD83D\uDD04 Recargar", "key", "F5"),
        IconPreset("\uD83C\uDFAF", "\uD83C\uDFAF Seleccionar", "key", "TAB"),
        IconPreset("\u274C", "\u274C Cerrar", "key", "ESC"),
    )

    private val keySuggestions = listOf(
        "ENTER", "TAB", "BACK", "HOME", "DEL", "SPACE", "ESC", "F5",
        "UP", "DOWN", "LEFT", "RIGHT", "PAGE_UP", "PAGE_DOWN",
        "CTRL+C", "CTRL+V", "CTRL+X", "CTRL+A", "CTRL+Z",
        "ALT+TAB", "ALT+F4"
    )

    private val languageOptions = listOf(
        "es" to "Español",
        "en" to "English",
        "fr" to "Français",
        "de" to "Deutsch",
        "it" to "Italiano",
        "pt" to "Português",
        "ja" to "日本語",
        "zh" to "中文",
        "ko" to "한국어",
        "ru" to "Русский",
        "ar" to "العربية",
        "nl" to "Nederlands",
        "sv" to "Svenska",
        "pl" to "Polski"
    )

    private fun showButtonDialog(existing: ButtonConfig?) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_button_config, null)
        val iconContainer = dialogView.findViewById<LinearLayout>(R.id.iconContainer)
        val spinner = dialogView.findViewById<Spinner>(R.id.spinnerActionType)
        val etAction = dialogView.findViewById<AutoCompleteTextView>(R.id.etAction)
        val langSpinner = dialogView.findViewById<Spinner>(R.id.spinnerLanguage)

        val actionTypes = arrayOf("text", "key", "voice", "enter")
        val actionLabels = arrayOf("Escribir texto", "Presionar tecla", "Dictado", "Enter")
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, actionLabels)

        // ── Language selector ──
        val langLabels = languageOptions.map { it.second }.toTypedArray()
        val langCodes = languageOptions.map { it.first }.toTypedArray()
        langSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, langLabels)
        langSpinner.setSelection(langCodes.indexOf("es")) // default español

        fun updateLangVisibility(type: String) {
            langSpinner.visibility = if (type == "voice") android.view.View.VISIBLE else android.view.View.GONE
        }

        // ── Iconos circulares ──
        val dp = resources.displayMetrics.density
        val iconSize = (40 * dp).toInt()
        var selectedIcon = -1

        presets.forEachIndexed { idx, p ->
            val btn = Button(this).apply {
                text = p.emoji
                textSize = 16f
                gravity = android.view.Gravity.CENTER
                layoutParams = LinearLayout.LayoutParams(iconSize, iconSize).apply {
                    setMargins(0, 0, (6 * dp).toInt(), 0)
                }
                setOnClickListener {
                    selectedIcon = idx
                    // Update visual selection: borde blanco si seleccionado
                    for (i in 0 until iconContainer.childCount) {
                        val b = iconContainer.getChildAt(i) as? Button
                        val g = b?.background as? android.graphics.drawable.GradientDrawable
                        g?.setStroke(2, 0xFF888888.toInt())
                    }
                    val g = background as? android.graphics.drawable.GradientDrawable
                    g?.setStroke(2, 0xFFFFFFFF.toInt())
                    // Fill in values
                    val typeIdx = actionTypes.indexOf(p.actionType)
                    if (typeIdx >= 0) spinner.setSelection(typeIdx)
                    etAction.setText(p.action)
                    updateActionHint(actionTypes[if (typeIdx >= 0) typeIdx else 0], etAction)
                }
                val shape = android.graphics.drawable.GradientDrawable().apply {
                    setShape(android.graphics.drawable.GradientDrawable.OVAL)
                    setColor(0xFF444444.toInt())
                    setStroke(2, 0xFF888888.toInt())
                }
                background = shape
                clipToOutline = true
                setPadding(0, 0, 0, 0)
            }
            iconContainer.addView(btn)
        }

        // ── Autocomplete ──
        val keyAdapter = ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, keySuggestions)
        etAction.setAdapter(keyAdapter)
        etAction.threshold = 1

        // ── Si editando, preseleccionar ──
        if (existing != null) {
            val idx = presets.indexOfFirst { it.actionType == existing.actionType && it.action == existing.action }
            if (idx >= 0) {
                selectedIcon = idx
                val btn = iconContainer.getChildAt(idx)
                val g = btn.background as? android.graphics.drawable.GradientDrawable
                g?.setStroke(2, 0xFFFFFFFF.toInt())
            }
            val typeIdx = actionTypes.indexOf(existing.actionType)
            if (typeIdx >= 0) spinner.setSelection(typeIdx)
            etAction.setText(existing.action)
            etAction.setSelection(etAction.text?.length ?: 0)
            val langIdx = langCodes.indexOf(existing.language)
            if (langIdx >= 0) langSpinner.setSelection(langIdx)
            updateLangVisibility(existing.actionType)
        }

        spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: android.view.View?, pos: Int, id: Long) {
                updateActionHint(actionTypes[pos], etAction)
                updateLangVisibility(actionTypes[pos])
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        updateActionHint(actionTypes[spinner.selectedItemPosition], etAction)
        updateLangVisibility(actionTypes[spinner.selectedItemPosition])

        // ── Dialog ──
        val dialog = AlertDialog.Builder(this)
            .setTitle(if (existing == null) "Agregar Bot\u00f3n" else "Editar Bot\u00f3n")
            .setView(dialogView)
            .setPositiveButton("Guardar", null)
            .setNegativeButton("Cancelar", null)
            .create()

        dialog.show()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val typeIdx = spinner.selectedItemPosition
            val actionType = actionTypes[typeIdx]
            val action = etAction.text.toString().trim()

            val label = if (selectedIcon >= 0) presets[selectedIcon].label
                       else if (actionType == "voice") "Voz"
                       else if (actionType == "enter") "Enter"
                       else action.take(8)

            if (actionType == "text" && action.isEmpty()) {
                etAction.error = "Requerido"; return@setOnClickListener
            }

            val config = (existing ?: ButtonConfig()).copy(
                label = label,
                actionType = actionType,
                action = action,
                language = if (actionType == "voice") langCodes[langSpinner.selectedItemPosition] else (existing?.language ?: "es")
            )
            if (existing != null) {
                storage.updateButton(config)
                telemetry.evento("Bot\u00f3n editado: $label ($actionType)")
            } else {
                storage.addButton(config)
                telemetry.evento("Bot\u00f3n agregado: $label ($actionType)")
            }
            refreshList()
            dialog.dismiss()
            // Refrescar panel sin cerrarlo
            try { FloatingButtonService.refreshCallback?.invoke() } catch (_: Exception) {}
    }
    }

    private fun updateActionHint(type: String, et: AutoCompleteTextView) {
        when (type) {
            "text" -> { et.hint = "Texto a escribir"; et.setAdapter(null); et.inputType = android.text.InputType.TYPE_CLASS_TEXT }
            "key" -> { et.hint = "Tecla: ENTER, BACK, TAB, DEL..."; et.setAdapter(ArrayAdapter(this, android.R.layout.simple_dropdown_item_1line, keySuggestions)); et.threshold = 1 }
            "voice" -> { et.hint = "(se activar\u00e1 dictado)"; et.isEnabled = false }
            "enter" -> { et.hint = "(presiona Enter)"; et.isEnabled = false }
        }
    }

    /* ─── Sugerencia y servidor ─── */

    private fun showSuggestionDialog() {
        val input = EditText(this).apply {
            hint = "Describe tu sugerencia..."
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT)
            setLines(4)
        }
        AlertDialog.Builder(this)
            .setTitle("Sugerir mejora").setView(input)
            .setPositiveButton("Enviar") { _, _ ->
                val text = input.text.toString().trim()
                if (text.isNotEmpty()) {
                    crashReporter.sendFeatureRequest(text)
                    telemetry.evento("Sugerencia enviada")
                    Toast.makeText(this, "Enviada. Gracias!", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun showServerConfigDialog() {
        val input = EditText(this).apply {
            setText(CrashReporter.getServerUrl(this@MainActivity))
            hint = "http://IP:9099"
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT)
        }
        AlertDialog.Builder(this)
            .setTitle("URL del servidor")
            .setMessage("Direcci\u00f3n para enviar reportes")
            .setView(input)
            .setPositiveButton("Guardar") { _, _ ->
                val url = input.text.toString().trim()
                if (url.isNotEmpty()) {
                    CrashReporter.setServerUrl(this, url)
                    telemetry.evento("Servidor configurado: $url")
                    Toast.makeText(this, "Servidor actualizado", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancelar", null).show()
    }

    private fun showLogsDialog() {
        val logs = FloatingButtonService.logBuffer.toList()
        val msg = if (logs.isEmpty()) "No hay logs a\u00fan" else logs.joinToString("\n")
        AlertDialog.Builder(this)
            .setTitle("Logs de la aplicaci\u00f3n")
            .setMessage(msg)
            .setPositiveButton("OK", null)
            .setNeutralButton("Copiar") { _, _ ->
                val cm = getSystemService(android.content.ClipboardManager::class.java)
                cm?.setPrimaryClip(android.content.ClipData.newPlainText("logs", msg))
                Toast.makeText(this, "Logs copiados", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Borrar") { _, _ ->
                FloatingButtonService.logBuffer.clear()
                Toast.makeText(this, "Logs borrados", Toast.LENGTH_SHORT).show()
            }
            .show()
    }
}

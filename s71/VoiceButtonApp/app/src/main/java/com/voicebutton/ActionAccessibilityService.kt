package com.voicebutton

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.ClipData
import android.content.ClipboardManager
import android.os.Bundle
import android.util.Log
import android.view.KeyEvent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo
import android.view.inputmethod.EditorInfo

class ActionAccessibilityService : AccessibilityService() {

    data class FieldState(val text: String, val cursorStart: Int, val cursorEnd: Int)

    override fun onServiceConnected() {
        super.onServiceConnected()
        val info = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPES_ALL_MASK
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }
        serviceInfo = info
        FloatingButtonService.accessibilityService = this
        Log.i("VoiceButtons", "Servicio de accesibilidad conectado")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}

    override fun onDestroy() {
        FloatingButtonService.accessibilityService = null
        super.onDestroy()
    }

    /** Inserta texto. Primero intenta ACTION_SET_TEXT, luego clipboard+paste. */
    fun injectText(text: String) {
        try {
            val focused = findFocusedNode()
            if (focused != null) {
                // Intento 1: ACTION_SET_TEXT
                if (setTextDirect(focused, text)) return
                // Intento 2: clipboard + paste
                pasteFromClipboard(text)
            } else {
                // Intento 3: no hay campo enfocado → pegar igual
                pasteFromClipboard(text)
            }
        } catch (e: Exception) {
            Log.e("VoiceButtons", "injectText error", e)
        }
    }

    /** Intenta ACTION_SET_TEXT en el nodo. Retorna true si tuvo �xito. */
    private fun setTextDirect(node: AccessibilityNodeInfo, text: String): Boolean {
        try {
            val prev = node.text?.toString() ?: ""
            val start = node.textSelectionStart
            val end = node.textSelectionEnd

            val newText = when {
                start >= 0 && end > start -> prev.substring(0, start) + text + prev.substring(end)
                start > 0 && start <= prev.length -> prev.substring(0, start) + text + prev.substring(start)
                else -> prev + text
            }
            val args = Bundle().apply {
                putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, newText)
            }
            return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
        } catch (_: Exception) { return false }
    }

    /** Pone texto en clipboard y hace ACTION_PASTE. */
    private fun pasteFromClipboard(text: String) {
        try {
            val cm = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("voicebutton", text)
            cm.setPrimaryClip(clip)
            // Buscar nodo enfocado para pegar
            val focused = findFocusedNode()
            focused?.performAction(AccessibilityNodeInfo.ACTION_PASTE)
        } catch (e: Exception) {
            Log.e("VoiceButtons", "paste error", e)
        }
    }

    /** Reemplaza TODO el contenido del campo enfocado con el texto dado. */
    fun setFieldText(text: String): Boolean {
        return try {
            val node = findFocusedNode() ?: return false
            val args = Bundle().apply {
                putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
            }
            node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
        } catch (e: Exception) {
            Log.e("VoiceButtons", "setFieldText error", e)
            false
        }
    }

    /** Devuelve el texto y posici�n del cursor del campo enfocado. */
    fun getFieldState(): FieldState? {
        return try {
            val node = findFocusedNode() ?: return null
            FieldState(
                text = node.text?.toString() ?: "",
                cursorStart = node.textSelectionStart,
                cursorEnd = node.textSelectionEnd
            )
        } catch (e: Exception) {
            Log.e("VoiceButtons", "getFieldState error", e)
            null
        }
    }

    /** Pega texto desde el portapapeles (fallback cuando setFieldText falla). */
    fun pasteText(text: String) {
        pasteFromClipboard(text)
    }

    /** Ejecuta acciones globales (BACK, HOME, etc.) */
    fun injectKeyEvent(keyCode: Int) {
        try {
            when (keyCode) {
                KeyEvent.KEYCODE_BACK -> performGlobalAction(GLOBAL_ACTION_BACK)
                KeyEvent.KEYCODE_HOME -> performGlobalAction(GLOBAL_ACTION_HOME)
                KeyEvent.KEYCODE_DPAD_DOWN -> performGlobalAction(GLOBAL_ACTION_RECENTS)
                KeyEvent.KEYCODE_DPAD_UP -> performGlobalAction(GLOBAL_ACTION_RECENTS)
            }
        } catch (e: Exception) {
            Log.e("VoiceButtons", "injectKeyEvent error", e)
        }
    }

    /** Dispara la acci�n Enter en el campo enfocado. */
    fun injectEnter() {
        try {
            val focused = findFocusedNode()
            if (focused == null) {
                FloatingButtonService.addLog("Enter: sin campo enfocado")
                return
            }
            val currentText = focused.text?.toString() ?: ""
            FloatingButtonService.addLog("Enter: texto='${currentText.take(30)}'")

            // 1. Intentar IME action via accessibility (no funciona en EditText standard)
            val args = Bundle()
            val imeActions = listOf(
                EditorInfo.IME_ACTION_DONE to "DONE",
                EditorInfo.IME_ACTION_SEND to "SEND",
                EditorInfo.IME_ACTION_SEARCH to "SEARCH",
                EditorInfo.IME_ACTION_GO to "GO",
                EditorInfo.IME_ACTION_NEXT to "NEXT"
            )
            for ((actionId, actionName) in imeActions) {
                args.putInt("android.view.accessibility.action.ARGUMENT_IME_ACTION_ID", actionId)
                if (focused.performAction(0x10001000, args)) {
                    FloatingButtonService.addLog("Enter: IME $actionName ok")
                    return
                }
            }

            // 2. Buscar bot�n "Enter/Send/Enviar" en la ventana del teclado (IME)
            try {
                for (win in getWindows()) {
                    if (win.type == AccessibilityWindowInfo.TYPE_INPUT_METHOD) {
                        val root = win.root
                        if (root != null) {
                            val btn = findButtonInNode(root, listOf("Send", "Enviar", "Buscar", "Search", "Go", "Done", "Listo", "Siguiente", "Next", "\u23CE", "Enter"))
                            if (btn != null) {
                                btn.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                                FloatingButtonService.addLog("Enter: click en boton IME")
                                return
                            }
                        }
                    }
                }
            } catch (_: Exception) {}

            // 3. Fallback: clipboard + paste de newline
            FloatingButtonService.addLog("Enter: paste newline")
            pasteFromClipboard("\n")
        } catch (e: Exception) {
            Log.e("VoiceButtons", "injectEnter error", e)
        }
    }

    /** Busca recursivamente un bot�n en el �rbol de accesibilidad cuyo texto o contentDescription est� en la lista. */
    private fun findButtonInNode(node: AccessibilityNodeInfo, labels: List<String>): AccessibilityNodeInfo? {
        if (node.isClickable) {
            val text = node.text?.toString() ?: ""
            val desc = node.contentDescription?.toString() ?: ""
            val full = "$text $desc"
            if (labels.any { full.contains(it, ignoreCase = true) }) return node
        }
        for (i in 0 until node.childCount) {
            node.getChild(i)?.let { child ->
                val found = findButtonInNode(child, labels)
                if (found != null) { child.recycle(); return found }
                child.recycle()
            }
        }
        return null
    }

    /** Devuelve el texto del campo enfocado (para telemetr�a) */
    fun getFocusedText(): String? {
        return try {
            findFocusedNode()?.text?.toString()
        } catch (_: Exception) { null }
    }

    private fun findFocusedNode(): AccessibilityNodeInfo? {
        return try {
            val root = rootInActiveWindow ?: return null
            val focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
            if (focused != null) return focused
            val queue = ArrayDeque<AccessibilityNodeInfo>()
            queue.add(root)
            while (queue.isNotEmpty()) {
                val node = queue.removeFirst()
                if (node.isFocused && node.isEditable) return node
                for (i in 0 until node.childCount) {
                    node.getChild(i)?.let { queue.add(it) }
                }
            }
            null
        } catch (e: Exception) {
            Log.e("VoiceButtons", "findFocusedNode error", e)
            null
        }
    }
}

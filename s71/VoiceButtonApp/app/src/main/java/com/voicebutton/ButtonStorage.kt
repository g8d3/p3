package com.voicebutton

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

class ButtonStorage(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("buttons", Context.MODE_PRIVATE)

    init {
        // Add default buttons on first run
        if (!prefs.getBoolean("initialized", false)) {
            val defaults = listOf(
                ButtonConfig(id = 1, label = "\uD83C\uDFA4 Voz", actionType = "voice", action = ""),
                ButtonConfig(id = 2, label = "\u23CE Enter", actionType = "enter", action = "")
            )
            saveButtons(defaults)
            prefs.edit().putBoolean("initialized", true).apply()
        }
    }

    fun loadButtons(): List<ButtonConfig> {
        val json = prefs.getString("list", "[]") ?: "[]"
        val arr = JSONArray(json)
        val list = mutableListOf<ButtonConfig>()
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            list.add(
                ButtonConfig(
                    id = obj.optLong("id", System.currentTimeMillis()),
                    label = obj.optString("label", ""),
                    actionType = obj.optString("actionType", "text"),
                    action = obj.optString("action", ""),
                    language = obj.optString("language", "es")
                )
            )
        }
        return list
    }

    fun saveButtons(buttons: List<ButtonConfig>) {
        val arr = JSONArray()
        for (b in buttons) {
            val obj = JSONObject()
            obj.put("id", b.id)
            obj.put("label", b.label)
            obj.put("actionType", b.actionType)
            obj.put("action", b.action)
            obj.put("language", b.language)
            arr.put(obj)
        }
        prefs.edit().putString("list", arr.toString()).apply()
    }

    fun addButton(button: ButtonConfig) {
        val list = loadButtons().toMutableList()
        list.add(button)
        saveButtons(list)
    }

    fun removeButton(id: Long) {
        val list = loadButtons().toMutableList()
        list.removeAll { it.id == id }
        saveButtons(list)
    }

    fun updateButton(button: ButtonConfig) {
        val list = loadButtons().toMutableList()
        val idx = list.indexOfFirst { it.id == button.id }
        if (idx >= 0) {
            list[idx] = button
            saveButtons(list)
        }
    }
}

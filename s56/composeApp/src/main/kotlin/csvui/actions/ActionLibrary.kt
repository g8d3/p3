package csvui.actions

import csvui.model.*
import java.io.File

/**
 * Manages the library of saved custom action definitions.
 * Actions are stored as JSON in a file alongside the app.
 */
object ActionLibrary {

    private val libraryFile: File by lazy {
        val appDir = File(System.getProperty("user.home"), ".csv-tabulator")
        appDir.mkdirs()
        File(appDir, "action-library.json")
    }

    private var definitions: MutableList<ActionDefinition> = mutableListOf()

    fun load(): List<ActionDefinition> {
        return try {
            if (libraryFile.exists()) {
                val text = libraryFile.readText()
                definitions = parseJsonArray(text).toMutableList()
                definitions.toList()
            } else {
                definitions = getDefaults().toMutableList()
                save()
                definitions.toList()
            }
        } catch (e: Exception) {
            System.err.println("Failed to load action library: ${e.message}")
            definitions = getDefaults().toMutableList()
            definitions.toList()
        }
    }

    fun save() {
        try {
            libraryFile.writeText(toJsonArray(definitions))
        } catch (e: Exception) {
            System.err.println("Failed to save action library: ${e.message}")
        }
    }

    fun getAll(): List<ActionDefinition> = definitions.toList()

    fun add(def: ActionDefinition) {
        definitions.add(def)
        save()
    }

    fun update(def: ActionDefinition) {
        val idx = definitions.indexOfFirst { it.id == def.id }
        if (idx >= 0) {
            definitions[idx] = def
            save()
        }
    }

    fun remove(id: String) {
        definitions.removeAll { it.id == id }
        save()
    }

    fun getAction(name: String): DataAction? {
        val def = definitions.find { it.name == name } ?: return null
        return BuiltinActions.createFromDefinition(def)
    }

    fun toDataAction(def: ActionDefinition): DataAction? {
        return BuiltinActions.createFromDefinition(def)
    }

    private fun getDefaults(): List<ActionDefinition> = listOf(
        ActionDefinition(
            name = "Reverse Text",
            description = "Reverses the text in each selected cell",
            type = ActionType.TRANSFORM,
            transformExpression = "reverse"
        ),
        ActionDefinition(
            name = "Get Length",
            description = "Replaces cell content with its character length",
            type = ActionType.TRANSFORM,
            transformExpression = "length"
        ),
        ActionDefinition(
            name = "Count Words (wc)",
            description = "Counts words in each cell using wc command",
            type = ActionType.SHELL_COMMAND,
            commandTemplate = "echo {cell} | wc -w"
        ),
        ActionDefinition(
            name = "To SHA256",
            description = "Computes SHA256 hash of cell content",
            type = ActionType.SHELL_COMMAND,
            commandTemplate = "echo -n {cell} | sha256sum | cut -d' ' -f1"
        ),
        ActionDefinition(
            name = "URL Encode",
            description = "URL-encodes cell content using Python",
            type = ActionType.SHELL_COMMAND,
            commandTemplate = """python3 -c "import urllib.parse; print(urllib.parse.quote('{cell}'))" """
        ),
    )

    // Simple JSON serialization (no external dependencies)
    private fun parseJsonArray(text: String): List<ActionDefinition> {
        val trimmed = text.trim()
        if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) return emptyList()
        val inner = trimmed.substring(1, trimmed.length - 1).trim()
        if (inner.isEmpty()) return emptyList()

        val objects = mutableListOf<ActionDefinition>()
        var depth = 0
        var start = 0
        var i = 0
        while (i < inner.length) {
            when (inner[i]) {
                '{' -> { if (depth == 0) start = i; depth++ }
                '}' -> { depth--; if (depth == 0) {
                    val objStr = inner.substring(start, i + 1)
                    parseJsonObject(objStr)?.let { objects.add(it) }
                }}
            }
            i++
        }
        return objects
    }

    private fun parseJsonObject(text: String): ActionDefinition? {
        val trimmed = text.trim()
        if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) return null
        val map = mutableMapOf<String, String>()
        val inner = trimmed.substring(1, trimmed.length - 1).trim()

        // Simple key-value parsing
        var i = 0
        while (i < inner.length) {
            // Skip whitespace
            while (i < inner.length && inner[i].isWhitespace()) i++
            if (i >= inner.length) break

            // Parse key
            if (inner[i] != '"') break
            i++
            val key = StringBuilder()
            while (i < inner.length && inner[i] != '"') {
                if (inner[i] == '\\') { i++; if (i < inner.length) key.append(inner[i]) }
                else key.append(inner[i])
                i++
            }
            if (i >= inner.length) break
            i++ // skip closing quote

            // Skip colon
            while (i < inner.length && inner[i] != ':') i++
            i++
            while (i < inner.length && inner[i].isWhitespace()) i++

            // Parse value
            if (i < inner.length && inner[i] == '"') {
                i++
                val value = StringBuilder()
                while (i < inner.length && inner[i] != '"') {
                    if (inner[i] == '\\') { i++; if (i < inner.length) value.append(inner[i]) }
                    else value.append(inner[i])
                    i++
                }
                i++ // skip closing quote
                map[key.toString()] = value.toString()
            } else {
                // Non-string value (boolean, number)
                val valStart = i
                while (i < inner.length && inner[i] != ',' && inner[i] != '}') i++
                map[key.toString()] = inner.substring(valStart, i).trim()
            }

            // Skip comma
            while (i < inner.length && (inner[i] == ',' || inner[i].isWhitespace())) i++
        }

        return try {
            ActionDefinition(
                id = map["id"] ?: java.util.UUID.randomUUID().toString().take(8),
                name = map["name"] ?: "Unnamed",
                description = map["description"] ?: "",
                type = map["type"]?.let { ActionType.valueOf(it) } ?: ActionType.TO_UPPER,
                commandTemplate = map["commandTemplate"] ?: "",
                findText = map["findText"] ?: "",
                replaceText = map["replaceText"] ?: "",
                transformExpression = map["transformExpression"] ?: "",
                includeHeader = map["includeHeader"]?.toBoolean() ?: false
            )
        } catch (e: Exception) {
            null
        }
    }

    private fun toJsonArray(defs: List<ActionDefinition>): String {
        val sb = StringBuilder()
        sb.appendLine("[")
        defs.forEachIndexed { idx, def ->
            sb.append("  ")
            toJsonObject(def, sb)
            if (idx < defs.size - 1) sb.append(",")
            sb.appendLine()
        }
        sb.appendLine("]")
        return sb.toString()
    }

    private fun toJsonObject(def: ActionDefinition, sb: StringBuilder) {
        sb.append("{")
        sb.append("\"id\":\"${escapeJson(def.id)}\",")
        sb.append("\"name\":\"${escapeJson(def.name)}\",")
        sb.append("\"description\":\"${escapeJson(def.description)}\",")
        sb.append("\"type\":\"${def.type.name}\",")
        sb.append("\"commandTemplate\":\"${escapeJson(def.commandTemplate)}\",")
        sb.append("\"findText\":\"${escapeJson(def.findText)}\",")
        sb.append("\"replaceText\":\"${escapeJson(def.replaceText)}\",")
        sb.append("\"transformExpression\":\"${escapeJson(def.transformExpression)}\",")
        sb.append("\"includeHeader\":${def.includeHeader}")
        sb.append("}")
    }

    private fun escapeJson(s: String): String {
        return s.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    }
}

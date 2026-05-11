package webserver

import csvui.actions.ActionExecutor
import csvui.actions.ActionLibrary
import csvui.actions.BuiltinActions
import csvui.csv.CsvHandler
import csvui.model.*
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.*
import java.io.File

/**
 * Server-side application state. Single-user, mutable.
 * @param dataDir The directory where CSV files are read/written.
 */
class AppState(private val dataDir: File) {
    private var csvData = CsvData(
        headers = listOf("Column 1", "Column 2", "Column 3"),
        rows = listOf(
            listOf("", "", ""),
            listOf("", "", ""),
            listOf("", "", "")
        )
    )
    private var currentFile: File? = null
    private var selection = Selection.empty()
    private var statusMessage = "Ready"
    private var customActions = ActionLibrary.load()

    // ── API Handlers ──────────────────────────────────────────────

    suspend fun handleGetData(call: ApplicationCall) {
        call.respondText(toJson(), ContentType.Application.Json)
    }

    suspend fun handleGetInfo(call: ApplicationCall) {
        val info = buildJsonObject {
            put("status", statusMessage)
            put("fileName", currentFile?.name ?: "")
            put("filePath", currentFile?.absolutePath ?: "")
            put("rowCount", csvData.rowCount)
            put("colCount", csvData.columnCount)
        }
        call.respondText(json.encodeToString(info), ContentType.Application.Json)
    }

    suspend fun handleUpdateCell(call: ApplicationCall) {
        val body = call.receiveText()
        val obj = json.parseToJsonElement(body).jsonObject
        val row = obj["row"]!!.jsonPrimitive.int
        val col = obj["col"]!!.jsonPrimitive.int
        val value = obj["value"]!!.jsonPrimitive.content
        csvData = csvData.setCell(row, col, value)
        statusMessage = "Cell updated"
        call.respondText(toJson(), ContentType.Application.Json)
    }

    suspend fun handleRowOp(call: ApplicationCall) {
        val body = call.receiveText()
        val obj = json.parseToJsonElement(body).jsonObject
        val action = obj["action"]!!.jsonPrimitive.content
        when (action) {
            "add" -> {
                csvData = csvData.addRow(List(csvData.columnCount) { "" })
                statusMessage = "Row added"
            }
            "delete" -> {
                val index = obj["index"]?.jsonPrimitive?.int ?: -1
                if (index >= 0 && index < csvData.rowCount) {
                    csvData = csvData.deleteRow(index)
                    selection = Selection.empty()
                    statusMessage = "Row deleted"
                }
            }
        }
        call.respondText(toJson(), ContentType.Application.Json)
    }

    suspend fun handleColumnOp(call: ApplicationCall) {
        val body = call.receiveText()
        val obj = json.parseToJsonElement(body).jsonObject
        val action = obj["action"]!!.jsonPrimitive.content
        when (action) {
            "add" -> {
                val header = obj["header"]?.jsonPrimitive?.content
                    ?: "Column ${csvData.columnCount + 1}"
                csvData = csvData.addColumn(header)
                statusMessage = "Column added"
            }
            "delete" -> {
                val index = obj["index"]?.jsonPrimitive?.int ?: -1
                if (index >= 0 && index < csvData.columnCount) {
                    csvData = csvData.deleteColumn(index)
                    selection = Selection.empty()
                    statusMessage = "Column deleted"
                }
            }
        }
        call.respondText(toJson(), ContentType.Application.Json)
    }

    suspend fun handleFileOp(call: ApplicationCall) {
        val body = call.receiveText()
        val obj = json.parseToJsonElement(body).jsonObject
        val action = obj["action"]!!.jsonPrimitive.content

        when (action) {
            "new" -> {
                csvData = CsvData(
                    headers = listOf("Column 1", "Column 2", "Column 3"),
                    rows = listOf(
                        listOf("", "", ""),
                        listOf("", "", ""),
                        listOf("", "", "")
                    )
                )
                currentFile = null
                selection = Selection.empty()
                statusMessage = "New file"
            }
            "open" -> {
                val path = obj["path"]?.jsonPrimitive?.content
                if (path != null) {
                    val file = File(path)
                    if (file.exists()) {
                        csvData = CsvHandler.readFile(file)
                        currentFile = file
                        selection = Selection.empty()
                        statusMessage = "Opened: ${file.name}"
                    } else {
                        statusMessage = "File not found: $path"
                    }
                }
            }
        }
        call.respondText(toJson(), ContentType.Application.Json)
    }

    suspend fun handleSave(call: ApplicationCall) {
        val body = call.receiveText()
        val path = if (body.isNotBlank()) {
            json.parseToJsonElement(body).jsonObject["path"]?.jsonPrimitive?.content
        } else null

        val file = if (path != null) File(path) else currentFile
        if (file != null) {
            CsvHandler.writeToFile(csvData, file)
            currentFile = file
            statusMessage = "Saved: ${file.name}"
            call.respondText(toJson(), ContentType.Application.Json)
        } else {
            // Auto-save to data/ directory with generated name
            val dataDir = getDataDir()
            val autoFile = File(dataDir, "untitled.csv")
            CsvHandler.writeToFile(csvData, autoFile)
            currentFile = autoFile
            statusMessage = "Saved: ${autoFile.name}"
            call.respondText(toJson(), ContentType.Application.Json)
        }
    }

    suspend fun handleExecuteAction(call: ApplicationCall) {
        val body = call.receiveText()
        val obj = json.parseToJsonElement(body).jsonObject

        val defObj = obj["action"]!!.jsonObject
        val selObj = obj["selection"]!!.jsonObject

        val sel = parseSelection(selObj)
        val actionDef = ActionDefinition(
            id = defObj["id"]?.jsonPrimitive?.contentOrNull ?: "",
            name = defObj["name"]?.jsonPrimitive?.contentOrNull ?: "Action",
            description = defObj["description"]?.jsonPrimitive?.contentOrNull ?: "",
            type = defObj["type"]?.jsonPrimitive?.contentOrNull?.let {
                try { ActionType.valueOf(it) } catch (_: Exception) { ActionType.TO_UPPER }
            } ?: ActionType.TO_UPPER,
            commandTemplate = defObj["commandTemplate"]?.jsonPrimitive?.contentOrNull ?: "",
            findText = defObj["findText"]?.jsonPrimitive?.contentOrNull ?: "",
            replaceText = defObj["replaceText"]?.jsonPrimitive?.contentOrNull ?: "",
            transformExpression = defObj["transformExpression"]?.jsonPrimitive?.contentOrNull ?: "",
            includeHeader = defObj["includeHeader"]?.jsonPrimitive?.booleanOrNull ?: false
        )

        val action = BuiltinActions.createFromDefinition(actionDef)
        if (action != null && sel.type != SelectionType.NONE) {
            csvData = ActionExecutor.execute(csvData, sel, action)
            statusMessage = "Action '${actionDef.name}' applied"
        }
        call.respondText(toJson(), ContentType.Application.Json)
    }

    suspend fun handleListFiles(call: ApplicationCall) {
        val dataDir = getDataDir()
        dataDir.mkdirs()
        val files = dataDir.listFiles { f -> f.name.endsWith(".csv") }?.map { it.name }?.sorted() ?: emptyList()
        val sb = StringBuilder()
        sb.appendLine("[")
        files.forEachIndexed { idx, name ->
            sb.append("  \"${name.replace("\"", "\\\"")}\"")
            if (idx < files.size - 1) sb.append(",")
            sb.appendLine()
        }
        sb.appendLine("]")
        call.respondText(sb.toString(), ContentType.Application.Json)
    }

    suspend fun handleListActions(call: ApplicationCall) {
        call.respondText(actionsToJson(customActions), ContentType.Application.Json)
    }

    suspend fun handleCreateAction(call: ApplicationCall) {
        val def = parseActionDef(call.receiveText())
        ActionLibrary.add(def)
        customActions = ActionLibrary.getAll()
        statusMessage = "Action '${def.name}' created"
        call.respondText(actionsToJson(customActions), ContentType.Application.Json)
    }

    suspend fun handleUpdateAction(call: ApplicationCall) {
        val id = call.parameters["id"] ?: return
        val def = parseActionDef(call.receiveText()).copy(id = id)
        ActionLibrary.update(def)
        customActions = ActionLibrary.getAll()
        call.respondText(actionsToJson(customActions), ContentType.Application.Json)
    }

    suspend fun handleDeleteAction(call: ApplicationCall) {
        val id = call.parameters["id"] ?: return
        ActionLibrary.remove(id)
        customActions = ActionLibrary.getAll()
        call.respondText(actionsToJson(customActions), ContentType.Application.Json)
    }

    // ── JSON helpers ──────────────────────────────────────────────

    private fun toJson(): String {
        val sb = StringBuilder()
        sb.appendLine("{")
        sb.appendLine("  \"headers\": ${jsonArray(csvData.headers)},")
        sb.appendLine("  \"rows\": [")
        csvData.rows.forEachIndexed { idx, row ->
            sb.append("    ${jsonArray(row)}")
            if (idx < csvData.rows.size - 1) sb.append(",")
            sb.appendLine()
        }
        sb.appendLine("  ],")
        sb.appendLine("  \"selection\": ${selectionToJson(selection)},")
        sb.appendLine("  \"status\": ${jsonString(statusMessage)},")
        sb.appendLine("  \"filePath\": ${jsonString(currentFile?.absolutePath ?: "")},")
        sb.appendLine("  \"fileName\": ${jsonString(currentFile?.name ?: "")},")
        sb.append("  \"rowCount\": ${csvData.rowCount},")
        sb.appendLine()
        sb.append("  \"colCount\": ${csvData.columnCount}")
        sb.appendLine()
        sb.appendLine("}")
        return sb.toString()
    }

    private fun jsonArray(list: List<String>): String {
        return "[" + list.joinToString(",") { jsonString(it) } + "]"
    }

    private fun jsonString(s: String): String {
        return "\"" + s.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t") + "\""
    }

    private fun selectionToJson(sel: Selection): String {
        return buildString {
            append("{")
            append("\"type\":\"${sel.type.name}\",")
            append("\"indices\":[${sel.indices.joinToString(",")}],")
            append("\"cells\":[")
            append(sel.cellPositions.joinToString(",") { "{\"row\":${it.row},\"col\":${it.col}}" })
            append("]")
            append("}")
        }
    }

    private fun parseSelection(obj: JsonObject): Selection {
        val type = try { SelectionType.valueOf(obj["type"]?.jsonPrimitive?.contentOrNull ?: "NONE") }
        catch (_: Exception) { SelectionType.NONE }
        val indices = obj["indices"]?.jsonArray?.map { it.jsonPrimitive.int } ?: emptyList()
        val cells = obj["cells"]?.jsonArray?.map {
            val o = it.jsonObject
            CellPosition(o["row"]!!.jsonPrimitive.int, o["col"]!!.jsonPrimitive.int)
        }?.toSet() ?: emptySet()
        return when (type) {
            SelectionType.ROWS -> Selection.rows(indices)
            SelectionType.COLUMNS -> Selection.columns(indices)
            SelectionType.CELLS -> Selection.cells(cells)
            SelectionType.NONE -> Selection.empty()
        }
    }

    private fun parseActionDef(body: String): ActionDefinition {
        val obj = json.parseToJsonElement(body).jsonObject
        return ActionDefinition(
            id = obj["id"]?.jsonPrimitive?.contentOrNull
                ?: java.util.UUID.randomUUID().toString().take(8),
            name = obj["name"]?.jsonPrimitive?.contentOrNull ?: "Unnamed",
            description = obj["description"]?.jsonPrimitive?.contentOrNull ?: "",
            type = obj["type"]?.jsonPrimitive?.contentOrNull?.let {
                try { ActionType.valueOf(it) } catch (_: Exception) { ActionType.TO_UPPER }
            } ?: ActionType.TO_UPPER,
            commandTemplate = obj["commandTemplate"]?.jsonPrimitive?.contentOrNull ?: "",
            findText = obj["findText"]?.jsonPrimitive?.contentOrNull ?: "",
            replaceText = obj["replaceText"]?.jsonPrimitive?.contentOrNull ?: "",
            transformExpression = obj["transformExpression"]?.jsonPrimitive?.contentOrNull ?: "",
            includeHeader = obj["includeHeader"]?.jsonPrimitive?.booleanOrNull ?: false
        )
    }

    /** Directory for storing CSV files — the directory the user specified. */
    private fun getDataDir(): File {
        return dataDir.also { it.mkdirs() }
    }

    private fun actionsToJson(actions: List<ActionDefinition>): String {
        val sb = StringBuilder()
        sb.appendLine("[")
        actions.forEachIndexed { idx, def ->
            sb.append("  {")
            sb.append("\"id\":${jsonString(def.id)},")
            sb.append("\"name\":${jsonString(def.name)},")
            sb.append("\"description\":${jsonString(def.description)},")
            sb.append("\"type\":\"${def.type.name}\",")
            sb.append("\"commandTemplate\":${jsonString(def.commandTemplate)},")
            sb.append("\"findText\":${jsonString(def.findText)},")
            sb.append("\"replaceText\":${jsonString(def.replaceText)},")
            sb.append("\"transformExpression\":${jsonString(def.transformExpression)},")
            sb.append("\"includeHeader\":${def.includeHeader}")
            sb.append("}")
            if (idx < actions.size - 1) sb.append(",")
            sb.appendLine()
        }
        sb.appendLine("]")
        return sb.toString()
    }
}

package csvui.android.ui

import android.content.Context
import csvui.actions.ActionExecutor
import csvui.actions.ActionLibrary
import csvui.actions.BuiltinActions
import csvui.android.termux.CrashReporter
import csvui.android.termux.ShellExecutor
import csvui.android.termux.ShellResult
import csvui.csv.CsvHandler
import csvui.model.*
import java.io.File

/**
 * State holder for the Android app.
 */
class AppViewModel(private val context: Context) {
    var csvData = CsvData(
        headers = listOf("Column 1", "Column 2", "Column 3"),
        rows = listOf(listOf("", "", ""), listOf("", "", ""), listOf("", "", ""))
    )
    var selection = Selection.empty()
    var currentFile: File? = null
    var statusMessage = "Ready"
    var customActionDefs = ActionLibrary.load()
    var showActionEditor = false
    var editingActionDef: ActionDefinition? = null

    val builtinActions = BuiltinActions.getAll()

    private fun getStorageDir(): File {
        val dir = File(context.filesDir, "csv-data")
        dir.mkdirs()
        return dir
    }

    fun getCsvFiles(): List<File> {
        return getStorageDir().listFiles { f -> f.name.endsWith(".csv") }?.toList() ?: emptyList()
    }

    fun newFile() {
        csvData = CsvData(
            headers = listOf("Column 1", "Column 2", "Column 3"),
            rows = listOf(listOf("", "", ""), listOf("", "", ""), listOf("", "", ""))
        )
        currentFile = null
        selection = Selection.empty()
        statusMessage = "New file"
    }

    fun openFile(file: File) {
        try {
            csvData = CsvHandler.readFile(file)
            currentFile = file
            selection = Selection.empty()
            statusMessage = "Opened: ${file.name}"
            CrashReporter.logInfo("FILE", "Opened: ${file.absolutePath} (${file.length()} bytes)")
        } catch (e: Exception) {
            statusMessage = "Error: ${e.message}"
            CrashReporter.logError("FILE", "Failed to open: ${file.name}", e)
        }
    }

    fun saveFile(name: String): File {
        try {
            val file = File(getStorageDir(), name)
            CsvHandler.writeToFile(csvData, file)
            currentFile = file
            statusMessage = "Saved: ${file.name}"
            CrashReporter.logInfo("FILE", "Saved: ${file.absolutePath}")
            return file
        } catch (e: Exception) {
            statusMessage = "Error saving: ${e.message}"
            CrashReporter.logError("FILE", "Save failed: $name", e)
            throw e
        }
    }

    fun saveExisting() {
        if (currentFile != null) {
            try {
                CsvHandler.writeToFile(csvData, currentFile!!)
                statusMessage = "Saved: ${currentFile!!.name}"
                CrashReporter.logInfo("FILE", "Saved existing: ${currentFile!!.absolutePath}")
            } catch (e: Exception) {
                statusMessage = "Error saving: ${e.message}"
                CrashReporter.logError("FILE", "Save existing failed", e)
            }
        }
    }

    fun addRow() {
        csvData = csvData.addRow(List(csvData.columnCount) { "" })
        statusMessage = "Row added"
    }

    fun deleteSelectedRows() {
        if (selection.type != SelectionType.ROWS) return
        var data = csvData
        selection.indices.sortedDescending().forEach { row ->
            data = data.deleteRow(row)
        }
        csvData = data
        selection = Selection.empty()
        statusMessage = "Row(s) deleted"
    }

    fun addColumn() {
        csvData = csvData.addColumn("Column ${csvData.columnCount + 1}")
        statusMessage = "Column added"
    }

    fun deleteSelectedColumns() {
        if (selection.type != SelectionType.COLUMNS) return
        var data = csvData
        selection.indices.sortedDescending().forEach { col ->
            data = data.deleteColumn(col)
        }
        csvData = data
        selection = Selection.empty()
        statusMessage = "Column(s) deleted"
    }

    fun updateCell(row: Int, col: Int, value: String) {
        csvData = csvData.setCell(row, col, value)
    }

    fun executeBuiltinAction(action: DataAction) {
        if (selection.type == SelectionType.NONE) return
        try {
            csvData = ActionExecutor.execute(csvData, selection, action)
            statusMessage = "Action '${action.name}' applied"
            CrashReporter.logInfo("ACTION", "Executed builtin: ${action.name}")
        } catch (e: Exception) {
            statusMessage = "Error: ${e.message}"
            CrashReporter.logError("ACTION", "Failed builtin: ${action.name}", e)
        }
    }

    fun executeCustomAction(def: ActionDefinition) {
        val action = BuiltinActions.createFromDefinition(def)
        if (action == null || selection.type == SelectionType.NONE) return

        try {
            if (def.type == ActionType.SHELL_COMMAND) {
                executeShellAction(def, action)
            } else {
                csvData = ActionExecutor.execute(csvData, selection, action)
                statusMessage = "Action '${def.name}' applied"
            }
            CrashReporter.logInfo("ACTION", "Executed custom: ${def.name} (${def.type})")
        } catch (e: Exception) {
            statusMessage = "Error: ${e.message}"
            CrashReporter.logError("ACTION", "Failed custom: ${def.name}", e)
        }
    }

    private fun executeShellAction(def: ActionDefinition, action: DataAction) {
        // For shell commands, we need to run them via Termux or sh
        val cells = ActionExecutor.getApplicableCells(csvData, selection)
        if (cells.isEmpty()) return

        val template = def.commandTemplate

        if (ShellExecutor.isTermuxInstalled(context) && cells.size <= 3) {
            // Open Termux for small selections so user sees output
            val firstCell = csvData.getCell(cells[0].row, cells[0].col)
            val cmd = if (template.contains("{cell}")) {
                template.replace("{cell}", firstCell)
            } else template
            ShellExecutor.openTermuxWithCommand(context, cmd)
            statusMessage = "Opened Termux for execution"
        } else {
            // Run in background for many cells or no Termux
            var result = csvData
            for (cell in cells) {
                val cellValue = csvData.getCell(cell.row, cell.col)
                val shellResult = ShellExecutor.execute(context, template, cellValue)
                result = result.setCell(cell.row, cell.col, shellResult.formatted)
            }
            csvData = result
            statusMessage = "Shell action '${def.name}' applied"
        }
    }

    fun createAction(def: ActionDefinition) {
        ActionLibrary.add(def)
        customActionDefs = ActionLibrary.getAll()
        showActionEditor = false
        statusMessage = "Action '${def.name}' created"
    }

    fun updateAction(def: ActionDefinition) {
        ActionLibrary.update(def)
        customActionDefs = ActionLibrary.getAll()
        editingActionDef = null
        showActionEditor = false
        statusMessage = "Action '${def.name}' updated"
    }

    fun deleteAction(id: String) {
        ActionLibrary.remove(id)
        customActionDefs = ActionLibrary.getAll()
        statusMessage = "Action deleted"
    }
}

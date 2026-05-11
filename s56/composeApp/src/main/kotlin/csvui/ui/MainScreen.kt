package csvui.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import csvui.actions.ActionExecutor
import csvui.actions.ActionLibrary
import csvui.actions.BuiltinActions
import csvui.csv.CsvHandler
import csvui.model.*
import java.io.File

class MainViewModel {
    var csvData by mutableStateOf(CsvData())
    var selection by mutableStateOf(Selection.empty())
    var currentFile by mutableStateOf<File?>(null)
    var hasUnsavedChanges by mutableStateOf(false)
    var statusMessage by mutableStateOf("Ready")
    var showActionEditor by mutableStateOf(false)
    var editingActionDef by mutableStateOf<ActionDefinition?>(null)
    var customActionDefs by mutableStateOf<List<ActionDefinition>>(emptyList())
    var showMessageDialog by mutableStateOf(false)
    var messageDialogText by mutableStateOf("")

    val builtinActions: List<DataAction> = BuiltinActions.getAll()

    init {
        customActionDefs = ActionLibrary.load()
    }

    fun openFile(file: File) {
        try {
            val data = CsvHandler.readFile(file)
            csvData = data
            currentFile = file
            selection = Selection.empty()
            hasUnsavedChanges = false
            statusMessage = "Opened: ${file.name} (${data.rowCount} rows, ${data.columnCount} cols)"
        } catch (e: Exception) {
            statusMessage = "Error opening file: ${e.message}"
        }
    }

    fun newFile() {
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
        hasUnsavedChanges = false
        statusMessage = "New file created"
    }

    fun saveFile(file: File? = null) {
        val targetFile = file ?: currentFile ?: return
        try {
            CsvHandler.writeToFile(csvData, targetFile)
            currentFile = targetFile
            hasUnsavedChanges = false
            statusMessage = "Saved: ${targetFile.name}"
        } catch (e: Exception) {
            statusMessage = "Error saving: ${e.message}"
        }
    }

    fun addRow() {
        val newRow = List(csvData.columnCount) { "" }
        csvData = csvData.addRow(newRow)
        hasUnsavedChanges = true
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
        hasUnsavedChanges = true
        statusMessage = "Row(s) deleted"
    }

    fun addColumn() {
        csvData = csvData.addColumn("Column ${csvData.columnCount + 1}")
        hasUnsavedChanges = true
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
        hasUnsavedChanges = true
        statusMessage = "Column(s) deleted"
    }

    fun onCellEdit(row: Int, col: Int, value: String) {
        csvData = csvData.setCell(row, col, value)
        hasUnsavedChanges = true
    }

    fun executeBuiltinAction(action: DataAction) {
        if (selection.type == SelectionType.NONE) return
        try {
            csvData = ActionExecutor.execute(csvData, selection, action)
            hasUnsavedChanges = true
            statusMessage = "Action '${action.name}' applied"
        } catch (e: Exception) {
            statusMessage = "Action error: ${e.message}"
        }
    }

    fun executeCustomAction(def: ActionDefinition) {
        val action = BuiltinActions.createFromDefinition(def)
        if (action == null) {
            statusMessage = "Invalid action definition"
            return
        }
        if (selection.type == SelectionType.NONE) return
        try {
            csvData = ActionExecutor.execute(csvData, selection, action)
            hasUnsavedChanges = true
            statusMessage = "Action '${def.name}' applied"
        } catch (e: Exception) {
            statusMessage = "Action error: ${e.message}"
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

@Composable
fun MainScreen() {
    val viewModel = remember { MainViewModel() }

    MaterialTheme(
        colorScheme = lightColorScheme()
    ) {
        Surface(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Toolbar
                Toolbar(
                    currentFile = viewModel.currentFile,
                    hasUnsavedChanges = viewModel.hasUnsavedChanges,
                    onNew = { viewModel.newFile() },
                    onOpen = {
                        val file = showOpenCsvDialog()
                        if (file != null) viewModel.openFile(file)
                    },
                    onSave = {
                        if (viewModel.currentFile != null) {
                            viewModel.saveFile()
                        } else {
                            val file = showSaveCsvDialog()
                            if (file != null) viewModel.saveFile(file)
                        }
                    },
                    onSaveAs = {
                        val file = showSaveCsvDialog()
                        if (file != null) viewModel.saveFile(file)
                    },
                    onAddRow = { viewModel.addRow() },
                    onDeleteRow = {
                        if (viewModel.selection.type == SelectionType.ROWS) {
                            viewModel.deleteSelectedRows()
                        }
                    },
                    onAddColumn = { viewModel.addColumn() },
                    onDeleteColumn = {
                        if (viewModel.selection.type == SelectionType.COLUMNS) {
                            viewModel.deleteSelectedColumns()
                        }
                    },
                    canDeleteRow = viewModel.selection.type == SelectionType.ROWS &&
                            viewModel.selection.indices.isNotEmpty(),
                    canDeleteColumn = viewModel.selection.type == SelectionType.COLUMNS &&
                            viewModel.selection.indices.isNotEmpty()
                )

                // Main content
                Row(modifier = Modifier.weight(1f)) {
                    // Data table (main area)
                    DataTable(
                        data = viewModel.csvData,
                        selection = viewModel.selection,
                        onSelectionChange = { viewModel.selection = it },
                        onCellEdit = { row, col, value ->
                            viewModel.onCellEdit(row, col, value)
                        },
                        modifier = Modifier.weight(1f)
                    )

                    // Divider
                    VerticalDivider()

                    // Action panel (sidebar)
                    ActionPanel(
                        builtinActions = viewModel.builtinActions,
                        customActions = viewModel.customActionDefs,
                        currentSelection = viewModel.selection,
                        onExecuteBuiltin = { viewModel.executeBuiltinAction(it) },
                        onExecuteCustom = { viewModel.executeCustomAction(it) },
                        onCreateAction = { viewModel.editingActionDef = null; viewModel.showActionEditor = true },
                        onEditAction = { viewModel.editingActionDef = it; viewModel.showActionEditor = true },
                        onDeleteAction = { viewModel.deleteAction(it) },
                        modifier = Modifier.width(280.dp)
                    )
                }

                // Status bar
                StatusBar(
                    text = viewModel.statusMessage,
                    rowCount = viewModel.csvData.rowCount,
                    colCount = viewModel.csvData.columnCount,
                    currentFile = viewModel.currentFile
                )
            }
        }
    }

    // Action editor dialog
    if (viewModel.showActionEditor) {
        ActionEditorDialog(
            existingDef = viewModel.editingActionDef,
            onSave = { def ->
                if (viewModel.editingActionDef != null) {
                    viewModel.updateAction(def)
                } else {
                    viewModel.createAction(def)
                }
            },
            onDismiss = {
                viewModel.showActionEditor = false
                viewModel.editingActionDef = null
            }
        )
    }

    // Message dialog
    if (viewModel.showMessageDialog) {
        MessageDialog(
            title = "Notice",
            message = viewModel.messageDialogText,
            onDismiss = {
                viewModel.showMessageDialog = false
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Toolbar(
    currentFile: File?,
    hasUnsavedChanges: Boolean,
    onNew: () -> Unit,
    onOpen: () -> Unit,
    onSave: () -> Unit,
    onSaveAs: () -> Unit,
    onAddRow: () -> Unit,
    onDeleteRow: () -> Unit,
    onAddColumn: () -> Unit,
    onDeleteColumn: () -> Unit,
    canDeleteRow: Boolean,
    canDeleteColumn: Boolean
) {
    TopAppBar(
        title = {
            val title = currentFile?.name ?: "Untitled"
            Text(
                text = if (hasUnsavedChanges) "$title *" else title,
                fontSize = 14.sp
            )
        },
        navigationIcon = {},
        actions = {
            // File operations
            ToolbarButton("New", "New file", onNew)
            ToolbarButton("Open", "Open CSV", onOpen)
            ToolbarButton("Save", "Save CSV", onSave)
            ToolbarButton("Save As", "Save as...", onSaveAs)

            VerticalDivider(modifier = Modifier.height(24.dp).padding(horizontal = 4.dp))

            // Row operations
            ToolbarButton("+ Row", "Add row", onAddRow)
            ToolbarButton("- Row", "Delete selected row(s)", onDeleteRow, canDeleteRow)

            VerticalDivider(modifier = Modifier.height(24.dp).padding(horizontal = 4.dp))

            // Column operations
            ToolbarButton("+ Col", "Add column", onAddColumn)
            ToolbarButton("- Col", "Delete selected column(s)", onDeleteColumn, canDeleteColumn)
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = Color(0xFF2C3E50),
            titleContentColor = Color.White,
            actionIconContentColor = Color.White
        )
    )
}

@Composable
private fun ToolbarButton(
    text: String,
    tooltip: String,
    onClick: () -> Unit,
    enabled: Boolean = true
) {
    TextButton(
        onClick = onClick,
        enabled = enabled,
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
        colors = ButtonDefaults.textButtonColors(
            contentColor = Color.White,
            disabledContentColor = Color.Gray
        )
    ) {
        Text(text = text, fontSize = 11.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun StatusBar(
    text: String,
    rowCount: Int,
    colCount: Int,
    currentFile: File?
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = Color(0xFFF8F9FA),
        tonalElevation = 2.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = text,
                fontSize = 11.sp,
                color = Color.DarkGray
            )
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Text(
                    text = "Rows: $rowCount",
                    fontSize = 11.sp,
                    color = Color.Gray
                )
                Text(
                    text = "Cols: $colCount",
                    fontSize = 11.sp,
                    color = Color.Gray
                )
                Text(
                    text = currentFile?.parentFile?.absolutePath ?: "",
                    fontSize = 11.sp,
                    color = Color.LightGray
                )
            }
        }
    }
}

package csvui.android.ui

import android.content.Context
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import csvui.actions.ActionLibrary
import csvui.actions.BuiltinActions
import csvui.model.*
import java.io.File

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun MainScreen(context: Context, onReportError: () -> Unit = {}) {
    val vm = remember { AppViewModel(context) }
    var showFileDialog by remember { mutableStateOf(false) }
    var showActionSheet by remember { mutableStateOf(false) }
    var editingCell by remember { mutableStateOf<CellPosition?>(null) }
    var editText by remember { mutableStateOf(TextFieldValue("")) }
    var editingActionDef by remember { mutableStateOf<ActionDefinition?>(null) }
    var showActionEditor by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = vm.currentFile?.name ?: "CSV Tabulator",
                        fontSize = 16.sp
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF2C3E50),
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                ),
                actions = {
                    IconButton(onClick = { showFileDialog = true }) {
                        Icon(Icons.Default.Folder, "Files")
                    }
                    IconButton(onClick = { vm.newFile() }) {
                        Icon(Icons.Default.NoteAdd, "New")
                    }
                    IconButton(onClick = { vm.saveExisting() }) {
                        Icon(Icons.Default.Save, "Save")
                    }
                    IconButton(onClick = { showActionSheet = true }) {
                        Icon(Icons.Default.Build, "Actions")
                    }
                    IconButton(onClick = onReportError) {
                        Icon(Icons.Default.BugReport, "Report error")
                    }
                }
            )
        },
        bottomBar = {
            BottomAppBar(
                containerColor = Color(0xFFF8F9FA),
                tonalElevation = 2.dp
            ) {
                Text(
                    text = vm.statusMessage,
                    fontSize = 11.sp,
                    color = Color.Gray,
                    modifier = Modifier.weight(1f).padding(horizontal = 12.dp)
                )
                Text(
                    text = "${vm.csvData.rowCount}r ${vm.csvData.columnCount}c",
                    fontSize = 11.sp,
                    color = Color.Gray,
                    modifier = Modifier.padding(end = 12.dp)
                )
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Selection info + quick actions
            SelectionBar(
                selection = vm.selection,
                onAddRow = { vm.addRow() },
                onDeleteRow = {
                    if (vm.selection.type == SelectionType.ROWS) vm.deleteSelectedRows()
                },
                onAddCol = { vm.addColumn() },
                onDeleteCol = {
                    if (vm.selection.type == SelectionType.COLUMNS) vm.deleteSelectedColumns()
                },
                canDelRow = vm.selection.type == SelectionType.ROWS && vm.selection.indices.isNotEmpty(),
                canDelCol = vm.selection.type == SelectionType.COLUMNS && vm.selection.indices.isNotEmpty()
            )

            // Data table (scrollable)
            DataTable(
                data = vm.csvData,
                selection = vm.selection,
                onSelectionChange = { vm.selection = it },
                onCellEdit = { row, col, value -> vm.updateCell(row, col, value) },
                editingCell = editingCell,
                editText = editText,
                onEditingChange = { editingCell = it; editText = it?.let { TextFieldValue(vm.csvData.getCell(it.row, it.col)) } ?: TextFieldValue("") },
                onEditTextChange = { editText = it },
                modifier = Modifier.weight(1f)
            )
        }
    }

    // File dialog
    if (showFileDialog) {
        FileDialog(
            currentFile = vm.currentFile,
            files = vm.getCsvFiles(),
            onOpen = { vm.openFile(it); showFileDialog = false },
            onSave = { name -> vm.saveFile(name); showFileDialog = false },
            onDismiss = { showFileDialog = false }
        )
    }

    // Action sheet (bottom sheet)
    if (showActionSheet) {
        ActionSheet(
            builtinActions = vm.builtinActions,
            customActions = vm.customActionDefs,
            selection = vm.selection,
            onExecuteBuiltin = { vm.executeBuiltinAction(it); showActionSheet = false },
            onExecuteCustom = { vm.executeCustomAction(it); showActionSheet = false },
            onCreateAction = { editingActionDef = null; showActionEditor = true; showActionSheet = false },
            onEditAction = { editingActionDef = it; showActionEditor = true; showActionSheet = false },
            onDeleteAction = { vm.deleteAction(it) },
            onDismiss = { showActionSheet = false }
        )
    }

    // Action editor dialog
    if (showActionEditor) {
        ActionEditorDialog(
            existingDef = editingActionDef,
            onSave = { def ->
                if (editingActionDef != null) vm.updateAction(def) else vm.createAction(def)
                showActionEditor = false
            },
            onDismiss = { showActionEditor = false; editingActionDef = null }
        )
    }
}

@Composable
private fun SelectionBar(
    selection: Selection,
    onAddRow: () -> Unit,
    onDeleteRow: () -> Unit,
    onAddCol: () -> Unit,
    onDeleteCol: () -> Unit,
    canDelRow: Boolean,
    canDelCol: Boolean
) {
    Surface(
        tonalElevation = 1.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = when (selection.type) {
                    SelectionType.NONE -> "Tap cells to select"
                    SelectionType.ROWS -> "${selection.indices.size} row(s)"
                    SelectionType.COLUMNS -> "${selection.indices.size} column(s)"
                    SelectionType.CELLS -> "${selection.cellPositions.size} cell(s)"
                },
                fontSize = 12.sp,
                color = Color.Gray,
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = onAddRow) {
                Icon(Icons.Default.TableRows, "Add row")
            }
            IconButton(onClick = onDeleteRow, enabled = canDelRow) {
                Icon(Icons.Default.RemoveCircleOutline, "Del row")
            }
            Spacer(Modifier.width(4.dp))
            IconButton(onClick = onAddCol) {
                Icon(Icons.Default.ViewColumn, "Add col")
            }
            IconButton(onClick = onDeleteCol, enabled = canDelCol) {
                Icon(Icons.Default.RemoveCircleOutline, "Del col")
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun DataTable(
    data: CsvData,
    selection: Selection,
    onSelectionChange: (Selection) -> Unit,
    onCellEdit: (row: Int, col: Int, value: String) -> Unit,
    editingCell: CellPosition?,
    editText: TextFieldValue,
    onEditingChange: (CellPosition?) -> Unit,
    onEditTextChange: (TextFieldValue) -> Unit,
    modifier: Modifier = Modifier
) {
    val hScrollState = rememberScrollState()
    val focusManager = LocalFocusManager.current

    Box(
        modifier = modifier
            .fillMaxWidth()
            .horizontalScroll(hScrollState)
    ) {
        Column {
            // Header row
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .width(40.dp)
                        .height(32.dp)
                        .background(Color(0xFFF0F0F0))
                        .border(0.5.dp, Color(0xFFD0D0D0)),
                    contentAlignment = Alignment.Center
                ) {
                    Text("#", fontSize = 10.sp, color = Color.Gray)
                }
                data.headers.forEachIndexed { col, header ->
                    val isSelected = selection.type == SelectionType.COLUMNS && col in selection.indices
                    Box(
                        modifier = Modifier
                            .width(120.dp)
                            .height(32.dp)
                            .background(if (isSelected) Color(0xFF99C2FF) else Color(0xFFF0F0F0))
                            .border(0.5.dp, Color(0xFFD0D0D0))
                            .clickable {
                                onSelectionChange(
                                    if (isSelected) Selection.columns(selection.indices - col)
                                    else Selection.columns(selection.indices + col)
                                )
                            },
                        contentAlignment = Alignment.CenterStart
                    ) {
                        Text(
                            header,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.padding(horizontal = 4.dp)
                        )
                    }
                }
            }

            // Data rows
            LazyColumn {
                itemsIndexed(data.rows, key = { idx, _ -> idx }) { rowIdx, row ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // Row header
                        val isRowSel = selection.type == SelectionType.ROWS && rowIdx in selection.indices
                        Box(
                            modifier = Modifier
                                .width(40.dp)
                                .height(34.dp)
                                .background(if (isRowSel) Color(0xFF99C2FF) else Color(0xFFF0F0F0))
                                .border(0.5.dp, Color(0xFFD0D0D0))
                                .clickable {
                                    onSelectionChange(
                                        if (isRowSel) Selection.rows(selection.indices - rowIdx)
                                        else Selection.rows(selection.indices + rowIdx)
                                    )
                                },
                            contentAlignment = Alignment.Center
                        ) {
                            Text("${rowIdx + 1}", fontSize = 10.sp, color = Color.DarkGray)
                        }

                        row.forEachIndexed { colIdx, value ->
                            val isEditing = editingCell?.row == rowIdx && editingCell?.col == colIdx
                            val isSelected = when (selection.type) {
                                SelectionType.CELLS -> CellPosition(rowIdx, colIdx) in selection.cellPositions
                                SelectionType.ROWS -> rowIdx in selection.indices
                                SelectionType.COLUMNS -> colIdx in selection.indices
                                else -> false
                            }

                            if (isEditing) {
                                Box(
                                    modifier = Modifier
                                        .width(120.dp)
                                        .height(34.dp)
                                        .background(Color.White)
                                        .border(1.dp, Color(0xFF4A90D9))
                                ) {
                                    BasicTextField(
                                        value = editText,
                                        onValueChange = onEditTextChange,
                                        textStyle = TextStyle(fontSize = 13.sp),
                                        keyboardOptions = KeyboardOptions.Default.copy(
                                            imeAction = ImeAction.Done
                                        ),
                                        keyboardActions = KeyboardActions(
                                            onDone = {
                                                onCellEdit(rowIdx, colIdx, editText.text)
                                                onEditingChange(null)
                                                focusManager.clearFocus()
                                            }
                                        ),
                                        modifier = Modifier
                                            .fillMaxSize()
                                            .padding(horizontal = 4.dp)
                                    )
                                }
                            } else {
                                Box(
                                    modifier = Modifier
                                        .width(120.dp)
                                        .height(34.dp)
                                        .background(if (isSelected) Color(0xFFCCE0FF) else Color.Transparent)
                                        .border(0.5.dp, Color(0xFFD0D0D0))
                                        .combinedClickable(
                                            onClick = {
                                                val pos = CellPosition(rowIdx, colIdx)
                                                val cells = if (pos in selection.cellPositions) {
                                                    selection.cellPositions - pos
                                                } else {
                                                    selection.cellPositions + pos
                                                }
                                                onSelectionChange(Selection.cells(cells))
                                            },
                                            onLongClick = {
                                                onEditingChange(CellPosition(rowIdx, colIdx))
                                            }
                                        ),
                                    contentAlignment = Alignment.CenterStart
                                ) {
                                    Text(
                                        value,
                                        fontSize = 13.sp,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.padding(horizontal = 4.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ActionSheet(
    builtinActions: List<DataAction>,
    customActions: List<ActionDefinition>,
    selection: Selection,
    onExecuteBuiltin: (DataAction) -> Unit,
    onExecuteCustom: (ActionDefinition) -> Unit,
    onCreateAction: () -> Unit,
    onEditAction: (ActionDefinition) -> Unit,
    onDeleteAction: (String) -> Unit,
    onDismiss: () -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
                .padding(bottom = 32.dp)
        ) {
            Text("Actions", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(4.dp))
            Text(
                when (selection.type) {
                    SelectionType.NONE -> "Select cells/rows/columns first"
                    SelectionType.ROWS -> "${selection.indices.size} row(s) selected"
                    SelectionType.COLUMNS -> "${selection.indices.size} column(s) selected"
                    SelectionType.CELLS -> "${selection.cellPositions.size} cell(s) selected"
                },
                fontSize = 12.sp,
                color = Color.Gray
            )

            Spacer(Modifier.height(12.dp))
            Text("Built-in", style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.height(4.dp))

            builtinActions.forEach { action ->
                Button(
                    onClick = { onExecuteBuiltin(action) },
                    enabled = selection.type != SelectionType.NONE,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp),
                    contentPadding = PaddingValues(8.dp)
                ) {
                    Text(action.name, fontSize = 13.sp)
                }
            }

            Spacer(Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Custom Actions", style = MaterialTheme.typography.labelLarge)
                TextButton(onClick = onCreateAction) { Text("+ New", fontSize = 12.sp) }
            }

            if (customActions.isEmpty()) {
                Text(
                    "No custom actions",
                    fontSize = 12.sp,
                    color = Color.Gray,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            customActions.forEach { def ->
                val canExec = selection.type != SelectionType.NONE
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(def.name, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                            Text(def.type.label, fontSize = 10.sp, color = Color.Gray)
                        }
                        IconButton(onClick = { onExecuteCustom(def) }, enabled = canExec) {
                            Icon(Icons.Default.PlayArrow, "Run", tint = if (canExec) Color.Unspecified else Color.Gray)
                        }
                        IconButton(onClick = { onEditAction(def) }) {
                            Icon(Icons.Default.Edit, "Edit", modifier = Modifier.size(18.dp))
                        }
                        IconButton(onClick = { onDeleteAction(def.id) }) {
                            Icon(Icons.Default.Delete, "Delete", tint = Color.Red, modifier = Modifier.size(18.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FileDialog(
    currentFile: File?,
    files: List<File>,
    onOpen: (File) -> Unit,
    onSave: (String) -> Unit,
    onDismiss: () -> Unit
) {
    var fileName by remember { mutableStateOf(currentFile?.name ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Files") },
        text = {
            Column {
                Text("Saved files:", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                Spacer(Modifier.height(4.dp))

                if (files.isEmpty()) {
                    Text("No saved files", fontSize = 12.sp, color = Color.Gray)
                }

                files.forEach { file ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onOpen(file) }
                            .padding(vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Description, null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp))
                        Column {
                            Text(file.name, fontSize = 13.sp)
                            Text(
                                "${file.length()} bytes",
                                fontSize = 10.sp,
                                color = Color.Gray
                            )
                        }
                    }
                }

                Spacer(Modifier.height(12.dp))
                HorizontalDivider()
                Spacer(Modifier.height(8.dp))

                OutlinedTextField(
                    value = fileName,
                    onValueChange = { fileName = it },
                    label = { Text("Save as...") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Row {
                TextButton(onClick = onDismiss) { Text("Cancel") }
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = { onSave(fileName) },
                    enabled = fileName.isNotBlank()
                ) { Text("Save") }
            }
        }
    )
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun ActionEditorDialog(
    existingDef: ActionDefinition? = null,
    onSave: (ActionDefinition) -> Unit,
    onDismiss: () -> Unit
) {
    var name by remember { mutableStateOf(existingDef?.name ?: "") }
    var description by remember { mutableStateOf(existingDef?.description ?: "") }
    var type by remember { mutableStateOf(existingDef?.type ?: ActionType.SHELL_COMMAND) }
    var commandTemplate by remember { mutableStateOf(existingDef?.commandTemplate ?: "") }
    var findText by remember { mutableStateOf(existingDef?.findText ?: "") }
    var replaceText by remember { mutableStateOf(existingDef?.replaceText ?: "") }
    var transformExpression by remember { mutableStateOf(existingDef?.transformExpression ?: "") }
    var includeHeader by remember { mutableStateOf(existingDef?.includeHeader ?: false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (existingDef != null) "Edit Action" else "New Action") },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Name") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))

                // Type selector
                var expanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(
                    expanded = expanded,
                    onExpandedChange = { expanded = it }
                ) {
                    OutlinedTextField(
                        value = type.label,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Type") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        ActionType.entries.forEach { t ->
                            DropdownMenuItem(
                                text = { Text(t.label) },
                                onClick = { type = t; expanded = false }
                            )
                        }
                    }
                }

                Spacer(Modifier.height(8.dp))

                when (type) {
                    ActionType.SHELL_COMMAND -> {
                        Text("Use {cell} as placeholder", fontSize = 11.sp, color = Color.Gray)
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(
                            value = commandTemplate,
                            onValueChange = { commandTemplate = it },
                            label = { Text("Command") },
                            placeholder = { Text("echo {cell} | wc -w") },
                            minLines = 2,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(checked = includeHeader, onCheckedChange = { includeHeader = it })
                            Text("Include header", fontSize = 12.sp)
                        }
                    }
                    ActionType.FIND_REPLACE -> {
                        OutlinedTextField(value = findText, onValueChange = { findText = it }, label = { Text("Find") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(value = replaceText, onValueChange = { replaceText = it }, label = { Text("Replace") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    }
                    ActionType.TRANSFORM -> {
                        OutlinedTextField(value = transformExpression, onValueChange = { transformExpression = it }, label = { Text("Expression") }, placeholder = { Text("reverse") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                        Text("reverse, length, substr(0,3), padLeft(10,\"0\")", fontSize = 10.sp, color = Color.Gray)
                    }
                    ActionType.PREFIX -> {
                        OutlinedTextField(value = findText, onValueChange = { findText = it }, label = { Text("Prefix") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    }
                    ActionType.SUFFIX -> {
                        OutlinedTextField(value = findText, onValueChange = { findText = it }, label = { Text("Suffix") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    }
                    else -> Text("No additional config needed", fontSize = 12.sp, color = Color.Gray)
                }
            }
        },
        confirmButton = {
            Row {
                TextButton(onClick = onDismiss) { Text("Cancel") }
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = {
                        if (name.isBlank()) return@Button
                        val def = ActionDefinition(
                            id = existingDef?.id ?: java.util.UUID.randomUUID().toString().take(8),
                            name = name.trim(),
                            description = description.trim(),
                            type = type,
                            commandTemplate = commandTemplate.trim(),
                            findText = findText.trim(),
                            replaceText = replaceText.trim(),
                            transformExpression = transformExpression.trim(),
                            includeHeader = includeHeader
                        )
                        onSave(def)
                    }
                ) { Text(if (existingDef != null) "Save" else "Create") }
            }
        }
    )
}

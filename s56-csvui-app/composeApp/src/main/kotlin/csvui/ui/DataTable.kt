package csvui.ui

import androidx.compose.foundation.*
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsHoveredAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.key.*
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import csvui.model.*

private val CellMinWidth = 120.dp
private val RowHeaderWidth = 50.dp
private val HeaderBg = Color(0xFFF0F0F0)
private val SelectedBg = Color(0xFFCCE0FF)
private val SelectedHeaderBg = Color(0xFF99C2FF)
private val EditingBg = Color(0xFFFFFFFF)
private val BorderColor = Color(0xFFD0D0D0)
private val HoverBg = Color(0xFFF5F5F5)

data class SortConfig(val column: Int, val ascending: Boolean)

@Composable
fun DataTable(
    data: CsvData,
    selection: Selection,
    onSelectionChange: (Selection) -> Unit,
    onCellEdit: (row: Int, col: Int, value: String) -> Unit,
    modifier: Modifier = Modifier
) {
    var sortConfig by remember { mutableStateOf<SortConfig?>(null) }
    var editingCell by remember { mutableStateOf<CellPosition?>(null) }
    var editText by remember { mutableStateOf(TextFieldValue("")) }
    val hScrollState = rememberScrollState()
    var hoveredRow by remember { mutableStateOf(-1) }

    val sortedData = remember(data, sortConfig) {
        if (sortConfig == null) data
        else {
            val sc = sortConfig!!
            val sortedRows = data.rows.sortedWith(
                Comparator { a, b ->
                    val va = a.getOrElse(sc.column) { "" }
                    val vb = b.getOrElse(sc.column) { "" }
                    val numA = va.toDoubleOrNull()
                    val numB = vb.toDoubleOrNull()
                    val cmp = if (numA != null && numB != null) {
                        numA.compareTo(numB)
                    } else {
                        va.compareTo(vb, ignoreCase = true)
                    }
                    if (sc.ascending) cmp else -cmp
                }
            )
            data.copy(rows = sortedRows)
        }
    }

    Box(modifier = modifier.border(1.dp, BorderColor)) {
        Column {
            // Column headers
            Row(
                modifier = Modifier
                    .horizontalScroll(hScrollState)
                    .background(HeaderBg)
            ) {
                // Corner cell (row header space)
                Box(
                    modifier = Modifier
                        .width(RowHeaderWidth)
                        .height(32.dp)
                        .border(0.5.dp, BorderColor)
                        .background(if (selection.type == SelectionType.NONE) HeaderBg else SelectedHeaderBg),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        "${data.rowCount} rows",
                        fontSize = 10.sp,
                        color = Color.Gray
                    )
                }

                sortedData.headers.forEachIndexed { col, header ->
                    val isSelected = selection.type == SelectionType.COLUMNS && col in selection.indices
                    ColumnHeaderCell(
                        header = header,
                        col = col,
                        isSelected = isSelected,
                        isSorted = sortConfig?.column == col,
                        sortAscending = sortConfig?.ascending ?: true,
                        onClick = {
                            onSelectionChange(
                                if (isSelected) {
                                    Selection.columns(selection.indices - col)
                                } else {
                                    Selection.columns(selection.indices + col)
                                }
                            )
                        },
                        onSortClick = {
                            if (sortConfig?.column == col) {
                                sortConfig = if (sortConfig?.ascending == true) {
                                    SortConfig(col, false)
                                } else null
                            } else {
                                sortConfig = SortConfig(col, true)
                            }
                        },
                        modifier = Modifier.width(CellMinWidth)
                    )
                }
            }

            // Data rows
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(hScrollState)
            ) {
                itemsIndexed(sortedData.rows, key = { idx, _ -> idx }) { rowIdx, row ->
                    val actualRow = data.rows.indexOf(row)

                    Row(
                        modifier = Modifier
                            .background(
                                when {
                                    selection.type == SelectionType.ROWS && actualRow in selection.indices -> SelectedBg
                                    hoveredRow == actualRow -> HoverBg
                                    else -> Color.Transparent
                                }
                            )
                    ) {
                        // Row header
                        RowHeaderCell(
                            index = actualRow,
                            isSelected = selection.type == SelectionType.ROWS && actualRow in selection.indices,
                            onClick = {
                                onSelectionChange(
                                    if (actualRow in selection.indices) {
                                        Selection.rows(selection.indices - actualRow)
                                    } else {
                                        Selection.rows(selection.indices + actualRow)
                                    }
                                )
                            }
                        )

                        row.forEachIndexed { colIdx, cellValue ->
                            val cellPos = CellPosition(actualRow, colIdx)
                            val isCellSelected = selection.type == SelectionType.CELLS &&
                                    cellPos in selection.cellPositions
                            val isEditing = editingCell == cellPos

                            if (isEditing) {
                                EditingCell(
                                    value = editText,
                                    onValueChange = { editText = it },
                                    onDone = {
                                        onCellEdit(actualRow, colIdx, editText.text)
                                        editingCell = null
                                    },
                                    onCancel = { editingCell = null },
                                    modifier = Modifier.width(CellMinWidth)
                                )
                            } else {
                                DataCell(
                                    value = cellValue,
                                    isSelected = isCellSelected,
                                    onClick = {
                                        val newCells = if (cellPos in selection.cellPositions) {
                                            selection.cellPositions - cellPos
                                        } else {
                                            selection.cellPositions + cellPos
                                        }
                                        onSelectionChange(Selection.cells(newCells))
                                    },
                                    onDoubleClick = {
                                        editingCell = CellPosition(actualRow, colIdx)
                                        editText = TextFieldValue(cellValue)
                                    },
                                    onHover = { hovering ->
                                        if (hovering) hoveredRow = actualRow
                                        else if (hoveredRow == actualRow) hoveredRow = -1
                                    },
                                    modifier = Modifier.width(CellMinWidth)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ColumnHeaderCell(
    header: String,
    col: Int,
    isSelected: Boolean,
    isSorted: Boolean,
    sortAscending: Boolean,
    onClick: () -> Unit,
    onSortClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .height(32.dp)
            .border(0.5.dp, BorderColor)
            .background(if (isSelected) SelectedHeaderBg else HeaderBg)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { onClick() },
        contentAlignment = Alignment.CenterStart
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = header,
                fontSize = 12.sp,
                fontWeight = if (isSelected) androidx.compose.ui.text.font.FontWeight.Bold
                    else androidx.compose.ui.text.font.FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            if (isSorted) {
                Text(
                    text = if (sortAscending) " ▲" else " ▼",
                    fontSize = 10.sp,
                    color = Color.Gray
                )
            }
        }
    }
}

@Composable
private fun RowHeaderCell(
    index: Int,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .width(RowHeaderWidth)
            .height(28.dp)
            .border(0.5.dp, BorderColor)
            .background(if (isSelected) SelectedHeaderBg else HeaderBg)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = (index + 1).toString(),
            fontSize = 11.sp,
            color = Color.DarkGray
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun DataCell(
    value: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    onDoubleClick: () -> Unit,
    onHover: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isHovered by interactionSource.collectIsHoveredAsState()

    LaunchedEffect(isHovered) {
        onHover(isHovered)
    }

    val bgColor = when {
        isSelected -> SelectedBg
        isHovered -> HoverBg
        else -> Color.Transparent
    }

    Box(
        modifier = modifier
            .height(28.dp)
            .border(0.5.dp, BorderColor)
            .background(bgColor)
            .combinedClickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick,
                onDoubleClick = onDoubleClick
            ),
        contentAlignment = Alignment.CenterStart
    ) {
        Text(
            text = value,
            fontSize = 13.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(horizontal = 6.dp)
        )
    }
}

@Composable
private fun EditingCell(
    value: TextFieldValue,
    onValueChange: (TextFieldValue) -> Unit,
    onDone: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier
) {
    val focusReq = remember { FocusRequester() }

    Box(
        modifier = modifier
            .height(28.dp)
            .background(EditingBg)
            .border(0.5.dp, Color(0xFF4A90D9))
            .focusRequester(focusReq)
            .onFocusChanged { state ->
                if (!state.isFocused) {
                    onDone()
                }
            },
        contentAlignment = Alignment.CenterStart
    ) {
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            textStyle = TextStyle(fontSize = 13.sp),
            keyboardOptions = KeyboardOptions.Default.copy(
                imeAction = ImeAction.Done
            ),
            keyboardActions = KeyboardActions(
                onDone = { onDone() }
            ),
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 4.dp)
                .onKeyEvent { event ->
                    if (event.type == KeyEventType.KeyUp &&
                        event.key == Key.Escape
                    ) {
                        onCancel()
                        true
                    } else false
                }
        )
    }

    LaunchedEffect(Unit) {
        focusReq.requestFocus()
    }
}

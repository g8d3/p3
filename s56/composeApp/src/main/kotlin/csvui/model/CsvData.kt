package csvui.model

data class CsvData(
    val headers: List<String> = emptyList(),
    val rows: List<List<String>> = emptyList()
) {
    val columnCount: Int get() = headers.size
    val rowCount: Int get() = rows.size

    fun getCell(row: Int, col: Int): String =
        rows.getOrNull(row)?.getOrNull(col) ?: ""

    fun setCell(row: Int, col: Int, value: String): CsvData {
        val newRows = rows.toMutableList()
        if (row in newRows.indices) {
            val newRow = newRows[row].toMutableList()
            if (col in newRow.indices) {
                newRow[col] = value
            }
            newRows[row] = newRow
        }
        return copy(rows = newRows)
    }

    fun addRow(row: List<String>): CsvData {
        val padded = if (row.size < columnCount) {
            row + List(columnCount - row.size) { "" }
        } else if (row.size > columnCount) {
            row.take(columnCount)
        } else row
        return copy(rows = rows + listOf(padded))
    }

    fun addColumn(header: String, defaultValue: String = ""): CsvData {
        val newHeaders = headers + header
        val newRows = rows.map { it + defaultValue }
        return CsvData(newHeaders, newRows)
    }

    fun deleteRow(index: Int): CsvData {
        if (index !in rows.indices) return this
        val newRows = rows.toMutableList().apply { removeAt(index) }
        return copy(rows = newRows)
    }

    fun deleteColumn(index: Int): CsvData {
        if (index !in headers.indices) return this
        val newHeaders = headers.toMutableList().apply { removeAt(index) }
        val newRows = rows.map { row ->
            row.toMutableList().apply { removeAt(index) }
        }
        return CsvData(newHeaders, newRows)
    }
}

data class CellPosition(val row: Int, val col: Int)

data class Selection(
    val type: SelectionType,
    val indices: List<Int>,
    val cellPositions: Set<CellPosition> = emptySet()
) {
    companion object {
        fun empty() = Selection(SelectionType.NONE, emptyList(), emptySet())
        fun rows(indices: List<Int>) = Selection(SelectionType.ROWS, indices)
        fun columns(indices: List<Int>) = Selection(SelectionType.COLUMNS, indices)
        fun cells(positions: Set<CellPosition>) = Selection(
            SelectionType.CELLS,
            positions.map { it.row }.distinct(),
            positions
        )
    }
}

enum class SelectionType {
    NONE, ROWS, COLUMNS, CELLS
}

enum class ApplyTarget(val label: String) {
    CELL("Each Cell"),
    ROW("Each Row"),
    COLUMN("Each Column"),
    ALL("All Cells")
}

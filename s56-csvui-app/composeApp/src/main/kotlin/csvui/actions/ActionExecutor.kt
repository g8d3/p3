package csvui.actions

import csvui.model.*

/**
 * Executes a DataAction on CsvData with the given selection.
 */
object ActionExecutor {

    fun execute(data: CsvData, selection: Selection, action: DataAction): CsvData {
        return action.apply(data, selection)
    }

    /** Gets the applicable cells for a given selection */
    fun getApplicableCells(data: CsvData, selection: Selection): List<CellPosition> {
        return when (selection.type) {
            SelectionType.NONE -> emptyList()
            SelectionType.ROWS -> {
                selection.indices.filter { it in data.rows.indices }.flatMap { row ->
                    (0 until data.columnCount).map { col -> CellPosition(row, col) }
                }
            }
            SelectionType.COLUMNS -> {
                selection.indices.filter { it in data.headers.indices }.flatMap { col ->
                    (0 until data.rowCount).map { row -> CellPosition(row, col) }
                }
            }
            SelectionType.CELLS -> {
                selection.cellPositions.filter { it.row in data.rows.indices && it.col in data.headers.indices }
            }
        }
    }
}

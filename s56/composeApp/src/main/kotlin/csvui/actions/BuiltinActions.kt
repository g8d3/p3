package csvui.actions

import csvui.model.*

/**
 * Registry of built-in actions (no shell required).
 */
object BuiltinActions {

    fun getAll(): List<DataAction> = listOf(
        ToUpperCaseAction,
        ToLowerCaseAction,
        TrimAction,
    )

    fun createFromDefinition(def: ActionDefinition): DataAction? {
        return when (def.type) {
            ActionType.SHELL_COMMAND -> ShellCommandAction.fromDefinition(def)
            ActionType.FIND_REPLACE -> FindReplaceAction(def)
            ActionType.TRANSFORM -> TransformAction(def)
            ActionType.TO_UPPER -> ToUpperCaseAction
            ActionType.TO_LOWER -> ToLowerCaseAction
            ActionType.TRIM -> TrimAction
            ActionType.PREFIX -> PrefixAction(def)
            ActionType.SUFFIX -> SuffixAction(def)
        }
    }

    object ToUpperCaseAction : DataAction {
        override val name = "To Uppercase"
        override val description = "Convert selected cells to uppercase"

        override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

        override fun apply(data: CsvData, selection: Selection): CsvData {
            val cells = ActionExecutor.getApplicableCells(data, selection)
            var result = data
            for (cell in cells) {
                result = result.setCell(cell.row, cell.col, result.getCell(cell.row, cell.col).uppercase())
            }
            return result
        }
    }

    object ToLowerCaseAction : DataAction {
        override val name = "To Lowercase"
        override val description = "Convert selected cells to lowercase"

        override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

        override fun apply(data: CsvData, selection: Selection): CsvData {
            val cells = ActionExecutor.getApplicableCells(data, selection)
            var result = data
            for (cell in cells) {
                result = result.setCell(cell.row, cell.col, result.getCell(cell.row, cell.col).lowercase())
            }
            return result
        }
    }

    object TrimAction : DataAction {
        override val name = "Trim Whitespace"
        override val description = "Trim leading and trailing whitespace from selected cells"

        override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

        override fun apply(data: CsvData, selection: Selection): CsvData {
            val cells = ActionExecutor.getApplicableCells(data, selection)
            var result = data
            for (cell in cells) {
                result = result.setCell(cell.row, cell.col, result.getCell(cell.row, cell.col).trim())
            }
            return result
        }
    }
}

class FindReplaceAction(private val def: ActionDefinition) : DataAction {
    override val name = def.name
    override val description = def.description

    override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

    override fun apply(data: CsvData, selection: Selection): CsvData {
        val cells = ActionExecutor.getApplicableCells(data, selection)
        var result = data
        for (cell in cells) {
            val value = result.getCell(cell.row, cell.col)
            result = result.setCell(cell.row, cell.col, value.replace(def.findText, def.replaceText))
        }
        return result
    }
}

class TransformAction(private val def: ActionDefinition) : DataAction {
    override val name = def.name
    override val description = def.description

    override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

    override fun apply(data: CsvData, selection: Selection): CsvData {
        val cells = ActionExecutor.getApplicableCells(data, selection)
        var result = data
        for (cell in cells) {
            val value = result.getCell(cell.row, cell.col)
            result = result.setCell(cell.row, cell.col, transformValue(value))
        }
        return result
    }

    private fun transformValue(value: String): String {
        // Simple built-in transform expressions
        val expr = def.transformExpression.trim()
        return when {
            expr.startsWith("substr(") -> {
                // substr(start,length) or substr(start)
                val args = expr.removePrefix("substr(").removeSuffix(")")
                    .split(",").map { it.trim() }
                val start = args.getOrNull(0)?.toIntOrNull() ?: 0
                if (args.size >= 2) {
                    val length = args[1].toIntOrNull() ?: value.length
                    value.substring(start, (start + length).coerceAtMost(value.length))
                } else {
                    value.substring(start)
                }
            }
            expr.startsWith("replace(") -> {
                val args = expr.removePrefix("replace(").removeSuffix(")")
                    .split(",").map { it.trim().removeSurrounding("\"") }
                if (args.size >= 2) value.replace(args[0], args[1]) else value
            }
            expr == "reverse" -> value.reversed()
            expr.startsWith("repeat(") -> {
                val count = expr.removePrefix("repeat(").removeSuffix(")").trim().toIntOrNull() ?: 1
                value.repeat(count.coerceAtLeast(0))
            }
            expr == "length" -> value.length.toString()
            expr.startsWith("padLeft(") -> {
                val args = expr.removePrefix("padLeft(").removeSuffix(")")
                    .split(",").map { it.trim() }
                val len = args.getOrNull(0)?.toIntOrNull() ?: value.length
                val char = args.getOrNull(1)?.removeSurrounding("\"")?.firstOrNull() ?: ' '
                value.padStart(len, char)
            }
            expr.startsWith("padRight(") -> {
                val args = expr.removePrefix("padRight(").removeSuffix(")")
                    .split(",").map { it.trim() }
                val len = args.getOrNull(0)?.toIntOrNull() ?: value.length
                val char = args.getOrNull(1)?.removeSurrounding("\"")?.firstOrNull() ?: ' '
                value.padEnd(len, char)
            }
            else -> value // unknown expression, return as-is
        }
    }
}

class PrefixAction(private val def: ActionDefinition) : DataAction {
    override val name = def.name
    override val description = def.description

    override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

    override fun apply(data: CsvData, selection: Selection): CsvData {
        val cells = ActionExecutor.getApplicableCells(data, selection)
        val prefix = def.findText // reuse findText field for prefix
        var result = data
        for (cell in cells) {
            result = result.setCell(cell.row, cell.col, prefix + result.getCell(cell.row, cell.col))
        }
        return result
    }
}

class SuffixAction(private val def: ActionDefinition) : DataAction {
    override val name = def.name
    override val description = def.description

    override fun isApplicable(selection: Selection) = selection.type != SelectionType.NONE

    override fun apply(data: CsvData, selection: Selection): CsvData {
        val cells = ActionExecutor.getApplicableCells(data, selection)
        val suffix = def.findText // reuse findText field for suffix
        var result = data
        for (cell in cells) {
            result = result.setCell(cell.row, cell.col, result.getCell(cell.row, cell.col) + suffix)
        }
        return result
    }
}

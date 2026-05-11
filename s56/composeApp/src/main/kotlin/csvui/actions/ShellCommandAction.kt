package csvui.actions

import csvui.model.*

/**
 * Action that runs a shell command for each selected cell, passing the cell
 * value via stdin or as a command argument using {cell} placeholder.
 *
 * Command template examples:
 *   "echo {cell}"           -> replaces {cell} with the value and runs it
 *   "python -c \"print('{cell}'.upper())\""
 *   "wc -c"                 -> pipes cell value to stdin
 *
 * If the template contains {cell}, it's replaced and the result is the command.
 * If not, the cell value is piped to stdin.
 */
class ShellCommandAction(
    override val name: String,
    override val description: String,
    private val commandTemplate: String,
    private val includeHeader: Boolean = false
) : DataAction {

    override fun isApplicable(selection: Selection): Boolean {
        return selection.type != SelectionType.NONE
    }

    override fun apply(data: CsvData, selection: Selection): CsvData {
        val executor = ActionExecutor
        val cells = executor.getApplicableCells(data, selection)
            .filter { includeHeader || it.row in data.rows.indices }

        var result = data
        // Process cells in sequence
        for (cell in cells) {
            val currentValue = result.getCell(cell.row, cell.col)
            val newValue = try {
                executeShell(currentValue)
            } catch (e: Exception) {
                "[Error: ${e.message}]"
            }
            result = result.setCell(cell.row, cell.col, newValue)
        }
        return result
    }

    /**
     * Properly escapes a string for safe insertion into a shell command.
     * 
     * Uses single-quote wrapping which prevents ALL shell expansions
     * (variables, globs, command substitution, etc.) and preserves
     * all characters including spaces, quotes, and special chars.
     * 
     * The only special case is single quotes inside the value, which
     * are handled by: close quote → add escaped quote → reopen quote:
     *   "it's" → 'it'\''s'
     */
    private fun escapeShell(s: String): String {
        return "'" + s.replace("'", "'\\''") + "'"
    }

    private fun executeShell(input: String): String {
        val escapedInput = escapeShell(input)
        val command = if (commandTemplate.contains("{cell}")) {
            // Replace {cell} with the properly escaped value
            commandTemplate.replace("{cell}", escapedInput)
        } else {
            // Pipe input to stdin — input is already single-quote escaped
            "echo $escapedInput | $commandTemplate"
        }

        val builder = ProcessBuilder()
        builder.command("sh", "-c", command)

        builder.redirectErrorStream(true)
        val process = builder.start()
        val output = process.inputStream.bufferedReader().readText().trim()
        val exitCode = process.waitFor()

        return if (exitCode == 0) {
            output
        } else {
            "[Exit $exitCode] $output"
        }
    }

    companion object {
        fun fromDefinition(def: ActionDefinition): ShellCommandAction? {
            if (def.type != ActionType.SHELL_COMMAND) return null
            return ShellCommandAction(
                name = def.name,
                description = def.description,
                commandTemplate = def.commandTemplate,
                includeHeader = def.includeHeader
            )
        }
    }
}

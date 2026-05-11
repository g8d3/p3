package csvui.model

/**
 * A user-defined action that transforms CSV data.
 */
interface DataAction {
    val name: String
    val description: String

    /** Apply this action to the given CSV data with the given selection. */
    fun apply(data: CsvData, selection: Selection): CsvData

    /** Returns true if this action can be applied to the current selection. */
    fun isApplicable(selection: Selection): Boolean
}

/**
 * Serializable data representation of a custom action for persistence.
 */
data class ActionDefinition(
    val id: String = java.util.UUID.randomUUID().toString().take(8),
    val name: String,
    val description: String = "",
    val type: ActionType,
    /** For SHELL_COMMAND: the command template using {cell} placeholder */
    val commandTemplate: String = "",
    /** For REPLACE: find and replace strings */
    val findText: String = "",
    val replaceText: String = "",
    /** For TRANSFORM: inline transformation expression */
    val transformExpression: String = "",
    /** Whether to apply to header */
    val includeHeader: Boolean = false
)

enum class ActionType(val label: String) {
    SHELL_COMMAND("Shell Command"),
    FIND_REPLACE("Find & Replace"),
    TRANSFORM("Transform"),
    TO_UPPER("To Uppercase"),
    TO_LOWER("To Lowercase"),
    TRIM("Trim Whitespace"),
    PREFIX("Add Prefix"),
    SUFFIX("Add Suffix")
}

package csvui

import csvui.actions.*
import csvui.model.*
import kotlin.test.*

class ActionsTest {

    private val sampleData = CsvData(
        headers = listOf("Name", "Value"),
        rows = listOf(
            listOf("Alice", "hello"),
            listOf("Bob", "WORLD"),
            listOf("Charlie", "  spaced  ")
        )
    )

    @Test
    fun `to uppercase action`() {
        val action = BuiltinActions.ToUpperCaseAction
        val selection = Selection.cells(setOf(CellPosition(0, 1), CellPosition(1, 1)))
        val result = action.apply(sampleData, selection)
        assertEquals("HELLO", result.getCell(0, 1))
        assertEquals("WORLD", result.getCell(1, 1))
        assertEquals("  spaced  ", result.getCell(2, 1)) // unchanged
    }

    @Test
    fun `to lowercase action`() {
        val action = BuiltinActions.ToLowerCaseAction
        val selection = Selection.cells(setOf(CellPosition(1, 1)))
        val result = action.apply(sampleData, selection)
        assertEquals("world", result.getCell(1, 1))
    }

    @Test
    fun `trim action`() {
        val action = BuiltinActions.TrimAction
        val selection = Selection.cells(setOf(CellPosition(2, 1)))
        val result = action.apply(sampleData, selection)
        assertEquals("spaced", result.getCell(2, 1))
    }

    @Test
    fun `find and replace action`() {
        val def = ActionDefinition(
            name = "Replace",
            type = ActionType.FIND_REPLACE,
            findText = "hello",
            replaceText = "hi"
        )
        val action = FindReplaceAction(def)
        val selection = Selection.cells(setOf(CellPosition(0, 1)))
        val result = action.apply(sampleData, selection)
        assertEquals("hi", result.getCell(0, 1))
    }

    @Test
    fun `transform reverse`() {
        val def = ActionDefinition(
            name = "Reverse",
            type = ActionType.TRANSFORM,
            transformExpression = "reverse"
        )
        val action = TransformAction(def)
        val selection = Selection.cells(setOf(CellPosition(0, 0)))
        val result = action.apply(sampleData, selection)
        assertEquals("ecilA", result.getCell(0, 0))
    }

    @Test
    fun `transform length`() {
        val def = ActionDefinition(
            name = "Length",
            type = ActionType.TRANSFORM,
            transformExpression = "length"
        )
        val action = TransformAction(def)
        val selection = Selection.cells(setOf(CellPosition(0, 0)))
        val result = action.apply(sampleData, selection)
        assertEquals("5", result.getCell(0, 0))
    }

    @Test
    fun `transform substr`() {
        val def = ActionDefinition(
            name = "Substr",
            type = ActionType.TRANSFORM,
            transformExpression = "substr(1,3)"
        )
        val action = TransformAction(def)
        val selection = Selection.cells(setOf(CellPosition(0, 0)))
        val result = action.apply(sampleData, selection)
        assertEquals("lic", result.getCell(0, 0))
    }

    @Test
    fun `prefix action`() {
        val def = ActionDefinition(
            name = "Prefix",
            type = ActionType.PREFIX,
            findText = "Mr. "
        )
        val action = PrefixAction(def)
        val selection = Selection.cells(setOf(CellPosition(0, 0)))
        val result = action.apply(sampleData, selection)
        assertEquals("Mr. Alice", result.getCell(0, 0))
    }

    @Test
    fun `suffix action`() {
        val def = ActionDefinition(
            name = "Suffix",
            type = ActionType.SUFFIX,
            findText = "!"
        )
        val action = SuffixAction(def)
        val selection = Selection.cells(setOf(CellPosition(0, 0)))
        val result = action.apply(sampleData, selection)
        assertEquals("Alice!", result.getCell(0, 0))
    }

    @Test
    fun `action on rows`() {
        val action = BuiltinActions.ToUpperCaseAction
        val selection = Selection.rows(listOf(0, 2))
        val result = action.apply(sampleData, selection)
        assertEquals("ALICE", result.getCell(0, 0))
        assertEquals("HELLO", result.getCell(0, 1))
        assertEquals("Bob", result.getCell(1, 0)) // row 1 unchanged
        assertEquals("CHARLIE", result.getCell(2, 0))
    }

    @Test
    fun `action on columns`() {
        val action = BuiltinActions.ToUpperCaseAction
        val selection = Selection.columns(listOf(1))
        val result = action.apply(sampleData, selection)
        assertEquals("Alice", result.getCell(0, 0)) // col 0 unchanged
        assertEquals("HELLO", result.getCell(0, 1))
        assertEquals("WORLD", result.getCell(1, 1))
        assertEquals("  SPACED  ", result.getCell(2, 1))
    }

    @Test
    fun `action not applicable on empty selection`() {
        val action = BuiltinActions.ToUpperCaseAction
        assertFalse(action.isApplicable(Selection.empty()))
    }

    @Test
    fun `action applicable on any non-empty selection`() {
        assertTrue(BuiltinActions.ToUpperCaseAction.isApplicable(Selection.rows(listOf(0))))
        assertTrue(BuiltinActions.ToUpperCaseAction.isApplicable(Selection.columns(listOf(0))))
        assertTrue(BuiltinActions.ToUpperCaseAction.isApplicable(
            Selection.cells(setOf(CellPosition(0, 0)))
        ))
    }

    @Test
    fun `create builtin from definition`() {
        val def = ActionDefinition(
            name = "Upper",
            type = ActionType.TO_UPPER
        )
        val action = BuiltinActions.createFromDefinition(def)
        assertNotNull(action)
        assertTrue(action is csvui.actions.BuiltinActions.ToUpperCaseAction)
    }

    @Test
    fun `create transform action from definition`() {
        val def = ActionDefinition(
            name = "Rev",
            type = ActionType.TRANSFORM,
            transformExpression = "reverse"
        )
        val action = BuiltinActions.createFromDefinition(def)
        assertNotNull(action)
    }

    @Test
    fun `apply no selection returns unchanged`() {
        val result = BuiltinActions.ToUpperCaseAction.apply(sampleData, Selection.empty())
        assertEquals(sampleData, result)
    }
}

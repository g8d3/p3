package csvui

import csvui.model.CsvData
import kotlin.test.*

class CsvDataTest {
    private val sampleData = CsvData(
        headers = listOf("Name", "Age"),
        rows = listOf(
            listOf("Alice", "30"),
            listOf("Bob", "25"),
            listOf("Charlie", "35")
        )
    )

    @Test
    fun `cell access`() {
        assertEquals("Alice", sampleData.getCell(0, 0))
        assertEquals("25", sampleData.getCell(1, 1))
        assertEquals("", sampleData.getCell(10, 10))
    }

    @Test
    fun `set cell`() {
        val updated = sampleData.setCell(1, 0, "Robert")
        assertEquals("Robert", updated.getCell(1, 0))
        assertEquals("Bob", sampleData.getCell(1, 0)) // original unchanged
    }

    @Test
    fun `add row`() {
        val updated = sampleData.addRow(listOf("Diana", "28"))
        assertEquals(4, updated.rowCount)
        assertEquals("Diana", updated.getCell(3, 0))
    }

    @Test
    fun `add row with wrong column count pads`() {
        val updated = sampleData.addRow(listOf("Eve")) // only 1 col
        assertEquals("Eve", updated.getCell(3, 0))
        assertEquals("", updated.getCell(3, 1))
    }

    @Test
    fun `add row with too many columns truncates`() {
        val updated = sampleData.addRow(listOf("Frank", "40", "Extra"))
        assertEquals(4, updated.rowCount)
        assertEquals("Frank", updated.getCell(3, 0))
        assertEquals("40", updated.getCell(3, 1))
    }

    @Test
    fun `add column`() {
        val updated = sampleData.addColumn("Score", "0")
        assertEquals(3, updated.columnCount)
        assertEquals("Score", updated.headers[2])
        assertEquals("0", updated.getCell(0, 2))
    }

    @Test
    fun `delete row`() {
        val updated = sampleData.deleteRow(1)
        assertEquals(2, updated.rowCount)
        assertEquals("Alice", updated.getCell(0, 0))
        assertEquals("Charlie", updated.getCell(1, 0))
    }

    @Test
    fun `delete row out of range`() {
        val updated = sampleData.deleteRow(10)
        assertEquals(sampleData, updated)
    }

    @Test
    fun `delete column`() {
        val updated = sampleData.deleteColumn(0)
        assertEquals(1, updated.columnCount)
        assertEquals("Age", updated.headers[0])
        assertEquals("30", updated.getCell(0, 0))
    }

    @Test
    fun `delete column out of range`() {
        val updated = sampleData.deleteColumn(10)
        assertEquals(sampleData, updated)
    }

    @Test
    fun `empty data`() {
        val empty = CsvData()
        assertEquals(0, empty.rowCount)
        assertEquals(0, empty.columnCount)
        assertEquals("", empty.getCell(0, 0))
    }
}

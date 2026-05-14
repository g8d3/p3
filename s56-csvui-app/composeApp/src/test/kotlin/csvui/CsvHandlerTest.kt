package csvui

import csvui.csv.CsvHandler
import kotlin.test.*

class CsvHandlerTest {

    private val csvContent = """
        |Name,Age,City,Score
        |Alice,30,New York,95
        |Bob,25,London,87
        |Charlie,35,Paris,92
    """.trimMargin()

    @Test
    fun parse_CSV_with_headers() {
        val data = CsvHandler.parse(csvContent)
        assertEquals(4, data.columnCount)
        assertEquals(3, data.rowCount)
        assertEquals(listOf("Name", "Age", "City", "Score"), data.headers)
        assertEquals("Alice", data.getCell(0, 0))
        assertEquals("30", data.getCell(0, 1))
        assertEquals("Paris", data.getCell(2, 2))
        assertEquals("92", data.getCell(2, 3))
    }

    @Test
    fun parse_CSV_without_headers() {
        val content = "a,b,c\n1,2,3\n4,5,6"
        val data = CsvHandler.parse(content, hasHeader = false)
        assertEquals(3, data.columnCount)
        assertEquals(3, data.rowCount)
        assertEquals(listOf("Column 1", "Column 2", "Column 3"), data.headers)
    }

    @Test
    fun parse_handles_quoted_fields() {
        val content = "name,description\n" +
                "Alice,\"Engineer, PhD\"\n" +
                "Bob,\"Said \"\"hello\"\"\""
        val data = CsvHandler.parse(content)
        assertEquals("Engineer, PhD", data.getCell(0, 1))
        assertEquals("Said \"hello\"", data.getCell(1, 1))
    }

    @Test
    fun parse_empty_content() {
        val data = CsvHandler.parse("", hasHeader = true)
        assertEquals(0, data.columnCount)
        assertEquals(0, data.rowCount)
    }

    @Test
    fun write_CSV_preserves_data() {
        val data = CsvHandler.parse(csvContent)
        val output = CsvHandler.write(data)
        val parsedBack = CsvHandler.parse(output)
        assertEquals(data.headers, parsedBack.headers)
        assertEquals(data.rows.size, parsedBack.rows.size)
        assertEquals(data.rows[0], parsedBack.rows[0])
    }

    @Test
    fun write_handles_special_characters() {
        val content = "name,note\n" +
                "Alice,\"contains, comma\"\n" +
                "Bob,\"has \"\"quotes\"\" \""
        val data = CsvHandler.parse(content)
        val output = CsvHandler.write(data)
        assertTrue(output.contains("\"contains, comma\""))
        // Parse the output back to verify round-trip correctness
        val reparsed = CsvHandler.parse(output)
        assertEquals(2, reparsed.rowCount)
        assertEquals("contains, comma", reparsed.getCell(0, 1))
        val actual = reparsed.getCell(1, 1)
        assertTrue(actual.contains("quotes") && actual.contains("has"))
    }

    @Test
    fun roundtrip_preserves_row_count() {
        val data = CsvHandler.parse(csvContent)
        val written = CsvHandler.write(data)
        val reparsed = CsvHandler.parse(written)
        assertEquals(data.rowCount, reparsed.rowCount)
        assertEquals(data.columnCount, reparsed.columnCount)
        for (r in 0 until data.rowCount) {
            for (c in 0 until data.columnCount) {
                assertEquals(data.getCell(r, c), reparsed.getCell(r, c))
            }
        }
    }
}

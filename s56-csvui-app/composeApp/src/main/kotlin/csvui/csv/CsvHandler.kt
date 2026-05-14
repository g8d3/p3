package csvui.csv

import csvui.model.CsvData
import java.io.File
import java.io.FileWriter

/**
 * Handles CSV file parsing and writing.
 */
object CsvHandler {

    fun parse(content: String, hasHeader: Boolean = true): CsvData {
        val lines = content.lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() }

        if (lines.isEmpty()) return CsvData()

        val parsedLines = lines.map { parseLine(it) }
        val csvLines = if (hasHeader && parsedLines.isNotEmpty()) {
            parsedLines
        } else if (!hasHeader) {
            parsedLines
        } else {
            parsedLines
        }

        val headers = if (hasHeader) {
            parsedLines.first()
        } else {
            val maxCols = parsedLines.maxOfOrNull { it.size } ?: 0
            (0 until maxCols).map { "Column ${it + 1}" }
        }

        val dataLines = if (hasHeader) parsedLines.drop(1) else parsedLines

        // Ensure all rows have the same number of columns
        val maxCols = maxOf(headers.size, dataLines.maxOfOrNull { it.size } ?: 0)
        val paddedHeaders = if (headers.size < maxCols) {
            headers + (headers.size until maxCols).map { "Column ${it + 1}" }
        } else headers

        val paddedData = dataLines.map { row ->
            if (row.size < maxCols) row + List(maxCols - row.size) { "" }
            else row.take(maxCols)
        }

        return CsvData(paddedHeaders, paddedData)
    }

    fun readFile(file: File): CsvData {
        return parse(file.readText())
    }

    fun write(data: CsvData): String {
        val sb = StringBuilder()
        sb.appendLine(encodeLine(data.headers))
        for (row in data.rows) {
            sb.appendLine(encodeLine(row))
        }
        return sb.toString()
    }

    fun writeToFile(data: CsvData, file: File) {
        FileWriter(file).use { writer ->
            writer.write(encodeLine(data.headers))
            writer.write("\n")
            for (row in data.rows) {
                writer.write(encodeLine(row))
                writer.write("\n")
            }
        }
    }

    /**
     * Parse a single CSV line handling quoted fields.
     */
    private fun parseLine(line: String): List<String> {
        val result = mutableListOf<String>()
        val current = StringBuilder()
        var inQuotes = false
        var i = 0

        while (i < line.length) {
            val c = line[i]
            when {
                c == '"' && !inQuotes -> inQuotes = true
                c == '"' && inQuotes -> {
                    if (i + 1 < line.length && line[i + 1] == '"') {
                        current.append('"')
                        i++ // skip escaped quote
                    } else {
                        inQuotes = false
                    }
                }
                c == ',' && !inQuotes -> {
                    result.add(current.toString().trim())
                    current.clear()
                }
                else -> current.append(c)
            }
            i++
        }
        result.add(current.toString().trim())
        return result
    }

    /**
     * Encode a list of values as a CSV line, quoting when necessary.
     */
    private fun encodeLine(values: List<String>): String {
        return values.joinToString(",") { value ->
            val v = value ?: ""
            if (v.contains(',') || v.contains('"') || v.contains('\n')) {
                "\"${v.replace("\"", "\"\"")}\""
            } else v
        }
    }

    fun hasHeaderLine(content: String): Boolean {
        val lines = content.lines().filter { it.isNotBlank() }
        if (lines.isEmpty()) return true
        val firstLine = parseLine(lines.first())
        // Heuristic: check if first line looks like headers (all non-numeric)
        val secondLine = if (lines.size > 1) parseLine(lines[1]) else emptyList()
        if (secondLine.isEmpty()) return true
        return firstLine.zip(secondLine).any { (header, value) ->
            header.toDoubleOrNull() == null && value.toDoubleOrNull() != null
        } || firstLine.all { it.toDoubleOrNull() == null }
    }
}

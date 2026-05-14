package csvui.android.termux

import android.content.Context
import android.content.Intent
import android.os.Build
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.*

/**
 * Captures crashes and errors, writes them to a log file,
 * and provides a way to share them.
 */
object CrashReporter {

    private const val LOG_FILE = "csv-tabulator-crash.log"
    private const val MAX_LOG_SIZE = 512 * 1024 // 512KB

    private var logFile: File? = null

    fun init(context: Context) {
        logFile = File(context.filesDir, LOG_FILE)

        // Set the default uncaught exception handler
        val existingHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            writeLog("UNCAUGHT EXCEPTION", throwable)
            existingHandler?.uncaughtException(thread, throwable)
        }
    }

    fun logError(tag: String, message: String, throwable: Throwable? = null) {
        val fullMsg = if (throwable != null) {
            "$message\n${stackTraceToString(throwable)}"
        } else {
            message
        }
        writeLog("ERROR [$tag]", fullMsg)
    }

    fun logInfo(tag: String, message: String) {
        writeLog("INFO [$tag]", message)
    }

    /**
     * Creates a share intent with the crash log.
     */
    fun createShareIntent(context: Context): Intent {
        val log = getLog()
        val report = buildString {
            appendLine("=== CSV Tabulator Crash Report ===")
            appendLine("Device: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            appendLine("App Version: 1.0.0")
            appendLine("Time: ${SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())}")
            appendLine()
            appendLine("--- Log ---")
            appendLine(log)
        }

        // Write report to a temp file for sharing
        val reportFile = File(context.cacheDir, "csv-tabulator-report.txt")
        reportFile.writeText(report)

        return Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_STREAM, androidx.core.content.FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                reportFile
            ))
            putExtra(Intent.EXTRA_TEXT, report.take(1000))
            putExtra(Intent.EXTRA_SUBJECT, "CSV Tabulator Crash Report")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }

    /**
     * Creates a share intent with just the text of the log.
     */
    fun createTextShareIntent(context: Context): Intent {
        val log = getLog()
        return Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, buildString {
                appendLine("CSV Tabulator Error Report")
                appendLine("Device: ${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE}")
                appendLine()
                appendLine("--- Log ---")
                appendLine(log)
            })
            putExtra(Intent.EXTRA_SUBJECT, "CSV Tabulator Error Report")
        }
    }

    fun getLog(): String {
        return try {
            logFile?.readText() ?: "No log file"
        } catch (e: Exception) {
            "Error reading log: ${e.message}"
        }
    }

    fun clearLog() {
        logFile?.delete()
    }

    private fun writeLog(tag: String, message: Any) {
        try {
            val file = logFile ?: return
            val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(Date())

            // Rotate log if too large
            if (file.exists() && file.length() > MAX_LOG_SIZE) {
                file.renameTo(File(file.absolutePath + ".old"))
            }

            file.appendText("[$timestamp] $tag: $message\n")
        } catch (_: Exception) {
            // Don't crash in the crash handler
        }
    }

    private fun stackTraceToString(throwable: Throwable): String {
        val sw = StringWriter()
        val pw = PrintWriter(sw)
        throwable.printStackTrace(pw)
        pw.flush()
        return sw.toString()
    }
}

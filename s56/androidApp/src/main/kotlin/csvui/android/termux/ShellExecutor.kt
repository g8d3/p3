package csvui.android.termux

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager

/**
 * Executes shell commands on Android.
 *
 * Strategy:
 * 1. If Termux is installed, use its bash for full Linux command support.
 * 2. Otherwise fall back to Android's /system/bin/sh (limited commands).
 *
 * Termux can be installed from F-Droid: https://f-droid.org/packages/com.termux/
 */
object ShellExecutor {

    private const val TERMUX_PACKAGE = "com.termux"
    private const val TERMUX_BASH = "/data/data/com.termux/files/usr/bin/bash"

    /**
     * Execute a shell command with the given input.
     * Returns (output, exitCode).
     */
    fun execute(context: Context, commandTemplate: String, cellInput: String): ShellResult {
        return try {
            if (isTermuxInstalled(context)) {
                executeTermux(commandTemplate, cellInput)
            } else {
                executeSh(commandTemplate, cellInput)
            }
        } catch (e: Exception) {
            ShellResult("[Error: ${e.message}]", -1)
        }
    }

    fun isTermuxInstalled(context: Context): Boolean {
        return try {
            context.packageManager.getPackageInfo(TERMUX_PACKAGE, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }

    /**
     * Open Termux with a command (user sees Termux UI).
     * For background execution with result, Termux:API app is needed.
     */
    fun openTermuxWithCommand(context: Context, command: String) {
        val intent = Intent("com.termux.RUN_COMMAND").apply {
            putExtra("com.termux.RUN_COMMAND_PATH", TERMUX_BASH)
            putExtra("com.termux.RUN_COMMAND_ARGUMENTS", arrayOf("-c", command))
            putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    }

    /**
     * Safely escapes a string for shell insertion using single-quote wrapping.
     * Prevents ALL shell expansions and preserves special characters.
     */
    private fun escapeShell(s: String): String {
        return "'" + s.replace("'", "'\\''") + "'"
    }

    private fun executeTermux(commandTemplate: String, cellInput: String): ShellResult {
        val escaped = escapeShell(cellInput)
        val command = if (commandTemplate.contains("{cell}")) {
            commandTemplate.replace("{cell}", escaped)
        } else {
            "echo $escaped | $commandTemplate"
        }

        val process = ProcessBuilder(TERMUX_BASH, "-c", command)
            .redirectErrorStream(true)
            .start()
        val output = process.inputStream.bufferedReader().readText().trim()
        val exitCode = process.waitFor()
        return ShellResult(output, exitCode)
    }

    private fun executeSh(commandTemplate: String, cellInput: String): ShellResult {
        val escaped = escapeShell(cellInput)
        val command = if (commandTemplate.contains("{cell}")) {
            commandTemplate.replace("{cell}", escaped)
        } else {
            "echo $escaped | $commandTemplate"
        }

        val process = ProcessBuilder("/system/bin/sh", "-c", command)
            .redirectErrorStream(true)
            .start()
        val output = process.inputStream.bufferedReader().readText().trim()
        val exitCode = process.waitFor()
        return ShellResult(output, exitCode)
    }
}

data class ShellResult(val output: String, val exitCode: Int) {
    val isSuccess: Boolean get() = exitCode == 0
    val formatted: String get() = if (isSuccess) output else "[Exit $exitCode] $output"
}

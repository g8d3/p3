package csvui.android

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import csvui.android.termux.CrashReporter
import csvui.android.ui.MainScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize crash reporter
        CrashReporter.init(this)
        CrashReporter.logInfo("LIFECYCLE", "App started")

        // Capture any crash from the application
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            CrashReporter.logError("UNCAUGHT", "Crash in thread ${thread.name}", throwable)
            // Re-throw to let Android handle it
            android.os.Process.killProcess(android.os.Process.myPid())
            System.exit(1)
        }

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen(
                        context = this@MainActivity,
                        onReportError = { shareErrorLog() }
                    )
                }
            }
        }
    }

    private fun shareErrorLog() {
        val intent = CrashReporter.createTextShareIntent(this)
        startActivity(Intent.createChooser(intent, "Share Error Report"))
    }
}

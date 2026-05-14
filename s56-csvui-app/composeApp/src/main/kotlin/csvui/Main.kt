package csvui

import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import csvui.ui.App

fun main() = application {
    Window(
        onCloseRequest = ::exitApplication,
        title = "CSV Tabulator",
        state = rememberWindowState(width = 1200.dp, height = 800.dp)
    ) {
        App()
    }
}

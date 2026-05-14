package csvui.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogWindow
import androidx.compose.ui.window.rememberDialogState
import java.io.File
import javax.swing.JFileChooser
import javax.swing.filechooser.FileNameExtensionFilter

/**
 * Shows a native file open dialog and returns the selected file, or null.
 */
fun showOpenCsvDialog(): File? {
    val chooser = JFileChooser().apply {
        dialogTitle = "Open CSV File"
        fileFilter = FileNameExtensionFilter("CSV Files (*.csv)", "csv", "tsv", "txt")
        isAcceptAllFileFilterUsed = true
    }
    return if (chooser.showOpenDialog(null) == JFileChooser.APPROVE_OPTION) {
        chooser.selectedFile
    } else null
}

/**
 * Shows a native file save dialog and returns the selected file, or null.
 */
fun showSaveCsvDialog(): File? {
    val chooser = JFileChooser().apply {
        dialogTitle = "Save CSV File"
        fileFilter = FileNameExtensionFilter("CSV Files (*.csv)", "csv")
        isAcceptAllFileFilterUsed = true
    }
    return if (chooser.showSaveDialog(null) == JFileChooser.APPROVE_OPTION) {
        var file = chooser.selectedFile
        if (!file.name.contains(".")) {
            file = File(file.absolutePath + ".csv")
        }
        file
    } else null
}

/**
 * A simple dialog composable for showing messages.
 */
@Composable
fun MessageDialog(
    title: String,
    message: String,
    onDismiss: () -> Unit
) {
    DialogWindow(
        onCloseRequest = onDismiss,
        title = title,
        state = rememberDialogState(width = 400.dp, height = 200.dp)
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = message,
                    style = MaterialTheme.typography.bodyLarge
                )
                Spacer(Modifier.height(16.dp))
                Button(onClick = onDismiss) {
                    Text("OK")
                }
            }
        }
    }
}

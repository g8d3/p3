package csvui.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogWindow
import androidx.compose.ui.window.rememberDialogState
import csvui.model.*

@Composable
fun ActionEditorDialog(
    existingDef: ActionDefinition? = null,
    onSave: (ActionDefinition) -> Unit,
    onDismiss: () -> Unit
) {
    val isEditing = existingDef != null
    var name by remember { mutableStateOf(existingDef?.name ?: "") }
    var description by remember { mutableStateOf(existingDef?.description ?: "") }
    var type by remember { mutableStateOf(existingDef?.type ?: ActionType.SHELL_COMMAND) }
    var commandTemplate by remember { mutableStateOf(existingDef?.commandTemplate ?: "") }
    var findText by remember { mutableStateOf(existingDef?.findText ?: "") }
    var replaceText by remember { mutableStateOf(existingDef?.replaceText ?: "") }
    var transformExpression by remember { mutableStateOf(existingDef?.transformExpression ?: "") }
    var includeHeader by remember { mutableStateOf(existingDef?.includeHeader ?: false) }
    var typeDropdownExpanded by remember { mutableStateOf(false) }

    var nameError by remember { mutableStateOf(false) }

    DialogWindow(
        onCloseRequest = onDismiss,
        title = if (isEditing) "Edit Action" else "Create New Action",
        state = rememberDialogState(width = 500.dp, height = 600.dp)
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            Column(
                modifier = Modifier
                    .padding(24.dp)
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    text = if (isEditing) "Edit Custom Action" else "Create New Custom Action",
                    style = MaterialTheme.typography.headlineSmall,
                    modifier = Modifier.padding(bottom = 16.dp)
                )

                // Name
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it; nameError = false },
                    label = { Text("Action Name") },
                    isError = nameError,
                    supportingText = if (nameError) {{ Text("Name is required") }} else null,
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(Modifier.height(8.dp))

                // Description
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Description (optional)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(Modifier.height(12.dp))

                // Action Type
                Text("Action Type", style = MaterialTheme.typography.labelLarge)
                Spacer(Modifier.height(4.dp))

                Box {
                    OutlinedButton(onClick = { typeDropdownExpanded = true }) {
                        Text(type.label)
                    }
                    DropdownMenu(
                        expanded = typeDropdownExpanded,
                        onDismissRequest = { typeDropdownExpanded = false }
                    ) {
                        ActionType.entries.forEach { actionType ->
                            DropdownMenuItem(
                                text = { Text(actionType.label) },
                                onClick = {
                                    type = actionType
                                    typeDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                Spacer(Modifier.height(16.dp))

                // Type-specific fields
                when (type) {
                    ActionType.SHELL_COMMAND -> {
                        Text(
                            "Use {cell} as placeholder for cell content.",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(
                            value = commandTemplate,
                            onValueChange = { commandTemplate = it },
                            label = { Text("Command Template") },
                            placeholder = { Text("echo {cell} | wc -w") },
                            minLines = 2,
                            maxLines = 4,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Spacer(Modifier.height(4.dp))
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Checkbox(
                                checked = includeHeader,
                                onCheckedChange = { includeHeader = it }
                            )
                            Text("Include header row", fontSize = 12.sp)
                        }
                    }
                    ActionType.FIND_REPLACE -> {
                        OutlinedTextField(
                            value = findText,
                            onValueChange = { findText = it },
                            label = { Text("Find") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Spacer(Modifier.height(8.dp))
                        OutlinedTextField(
                            value = replaceText,
                            onValueChange = { replaceText = it },
                            label = { Text("Replace With") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    ActionType.TRANSFORM -> {
                        Text(
                            "Built-in transform: reverse, length, substr(start,len), " +
                                    "replace(\"old\",\"new\"), repeat(n), padLeft(n,c), padRight(n,c)",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(
                            value = transformExpression,
                            onValueChange = { transformExpression = it },
                            label = { Text("Transform Expression") },
                            placeholder = { Text("reverse") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    ActionType.TO_UPPER -> {
                        Text("Converts selected text to UPPERCASE.", fontSize = 12.sp)
                    }
                    ActionType.TO_LOWER -> {
                        Text("Converts selected text to lowercase.", fontSize = 12.sp)
                    }
                    ActionType.TRIM -> {
                        Text("Trims leading and trailing whitespace.", fontSize = 12.sp)
                    }
                    ActionType.PREFIX -> {
                        OutlinedTextField(
                            value = findText,
                            onValueChange = { findText = it },
                            label = { Text("Prefix Text") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    ActionType.SUFFIX -> {
                        OutlinedTextField(
                            value = findText,
                            onValueChange = { findText = it },
                            label = { Text("Suffix Text") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                Spacer(Modifier.height(24.dp))

                // Action buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("Cancel")
                    }
                    Spacer(Modifier.width(8.dp))
                    Button(
                        onClick = {
                            if (name.isBlank()) {
                                nameError = true
                                return@Button
                            }
                            val newDef = ActionDefinition(
                                id = existingDef?.id ?: java.util.UUID.randomUUID().toString().take(8),
                                name = name.trim(),
                                description = description.trim(),
                                type = type,
                                commandTemplate = commandTemplate.trim(),
                                findText = findText.trim(),
                                replaceText = replaceText.trim(),
                                transformExpression = transformExpression.trim(),
                                includeHeader = includeHeader
                            )
                            onSave(newDef)
                        }
                    ) {
                        Text(if (isEditing) "Save Changes" else "Create Action")
                    }
                }
            }
        }
    }
}

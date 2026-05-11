package csvui.ui

import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import csvui.model.*

@Composable
fun ActionPanel(
    builtinActions: List<DataAction>,
    customActions: List<ActionDefinition>,
    currentSelection: Selection,
    onExecuteBuiltin: (DataAction) -> Unit,
    onExecuteCustom: (ActionDefinition) -> Unit,
    onCreateAction: () -> Unit,
    onEditAction: (ActionDefinition) -> Unit,
    onDeleteAction: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.padding(8.dp)) {
        // Selection info
        Text(
            text = when (currentSelection.type) {
                SelectionType.NONE -> "No selection"
                SelectionType.ROWS -> "${currentSelection.indices.size} row(s) selected"
                SelectionType.COLUMNS -> "${currentSelection.indices.size} column(s) selected"
                SelectionType.CELLS -> "${currentSelection.cellPositions.size} cell(s) selected"
            },
            fontSize = 11.sp,
            color = Color.Gray,
            modifier = Modifier.padding(bottom = 8.dp)
        )

        // Built-in actions section
        Text(
            text = "Built-in Actions",
            fontWeight = FontWeight.Bold,
            fontSize = 12.sp,
            modifier = Modifier.padding(bottom = 4.dp)
        )

        builtinActions.forEach { action ->
            ActionButton(
                name = action.name,
                description = action.description,
                enabled = action.isApplicable(currentSelection),
                onClick = { onExecuteBuiltin(action) }
            )
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        // Custom actions section
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Custom Actions",
                fontWeight = FontWeight.Bold,
                fontSize = 12.sp
            )
            TextButton(
                onClick = onCreateAction,
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp)
            ) {
                Text("+ New", fontSize = 11.sp)
            }
        }

        if (customActions.isEmpty()) {
            Text(
                text = "No custom actions yet.\nCreate one to run shell commands or transformations.",
                fontSize = 11.sp,
                color = Color.Gray,
                modifier = Modifier.padding(top = 8.dp)
            )
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f)
            ) {
                items(customActions, key = { it.id }) { def ->
                    val action = csvui.actions.BuiltinActions.createFromDefinition(def)
                    CustomActionItem(
                        def = def,
                        enabled = action?.isApplicable(currentSelection) ?: false,
                        onExecute = { onExecuteCustom(def) },
                        onEdit = { onEditAction(def) },
                        onDelete = { onDeleteAction(def.id) }
                    )
                }
            }
        }
    }
}

@Composable
private fun ActionButton(
    name: String,
    description: String,
    enabled: Boolean,
    onClick: () -> Unit
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = name,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
            if (description.isNotEmpty()) {
                Text(
                    text = description,
                    fontSize = 10.sp,
                    color = Color.Gray,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

@Composable
private fun CustomActionItem(
    def: ActionDefinition,
    enabled: Boolean,
    onExecute: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (enabled) MaterialTheme.colorScheme.surfaceVariant
            else Color(0xFFF5F5F5)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = def.name,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = def.type.label,
                    fontSize = 10.sp,
                    color = Color.Gray
                )
            }

            IconButton(
                onClick = onExecute,
                enabled = enabled,
                modifier = Modifier.size(28.dp)
            ) {
                Text("▶", fontSize = 12.sp)
            }

            Box {
                IconButton(
                    onClick = { showMenu = true },
                    modifier = Modifier.size(24.dp)
                ) {
                    Text("⋮", fontSize = 14.sp)
                }
                DropdownMenu(
                    expanded = showMenu,
                    onDismissRequest = { showMenu = false }
                ) {
                    DropdownMenuItem(
                        text = { Text("Edit", fontSize = 12.sp) },
                        onClick = { showMenu = false; onEdit() }
                    )
                    DropdownMenuItem(
                        text = { Text("Delete", fontSize = 12.sp, color = Color.Red) },
                        onClick = { showMenu = false; onDelete() }
                    )
                }
            }
        }
    }
}

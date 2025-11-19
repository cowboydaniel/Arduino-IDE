package com.arduino.ide.mobile.snippets

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.icons.Icons
import androidx.compose.material3.icons.filled.Add
import androidx.compose.material3.icons.filled.PlayArrow
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.StateFlow

@Composable
fun SnippetSheet(
    uiState: StateFlow<SnippetViewModel.SnippetUiState>,
    editorValue: StateFlow<TextFieldValue>,
    onQueryChange: (String) -> Unit,
    onCategoryChange: (String?) -> Unit,
    onInsertSnippet: (Snippet) -> Unit,
    onPreviewChange: (Snippet) -> Unit,
    onEditorChange: (TextFieldValue) -> Unit,
    onNextPlaceholder: () -> Unit,
    onAddUserSnippet: (String, String, String) -> Unit
) {
    val state by uiState.collectAsState()
    val editor by editorValue.collectAsState()

    Surface(
        tonalElevation = 4.dp,
        shadowElevation = 8.dp,
        shape = MaterialTheme.shapes.large
    ) {
        Column(
            modifier = Modifier
                .background(MaterialTheme.colorScheme.surface)
                .padding(16.dp)
        ) {
            Text("Snippets", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = state.searchQuery,
                onValueChange = onQueryChange,
                label = { Text("Search or trigger") },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("snippetSearchField")
            )
            Spacer(modifier = Modifier.height(8.dp))
            CategoryRow(
                categories = state.categories,
                selected = state.selectedCategory,
                onCategoryChange = onCategoryChange
            )
            Spacer(modifier = Modifier.height(12.dp))
            state.preview?.let { preview ->
                SnippetPreviewCard(preview)
                Spacer(modifier = Modifier.height(12.dp))
            }

            OutlinedTextField(
                value = editor,
                onValueChange = onEditorChange,
                label = { Text("Editor") },
                textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace),
                colors = TextFieldDefaults.outlinedTextFieldColors(),
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("snippetEditor")
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                AssistChip(
                    onClick = onNextPlaceholder,
                    label = { Text("Next placeholder") },
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null
                        )
                    },
                    modifier = Modifier.testTag("nextPlaceholderButton")
                )
                Text(
                    text = state.activePlaceholderLabel?.let { "Active: $it" } ?: "Cursor",
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.testTag("placeholderIndicator")
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            SnippetActions(onAddUserSnippet = onAddUserSnippet)
            Spacer(modifier = Modifier.height(8.dp))
            LazyColumn(modifier = Modifier.heightIn(max = 360.dp).testTag("snippetList")) {
                items(state.filtered) { snippet ->
                    SnippetCard(
                        snippet = snippet,
                        onClick = {
                            onInsertSnippet(snippet)
                            onPreviewChange(snippet)
                        }
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
private fun CategoryRow(
    categories: List<String>,
    selected: String?,
    onCategoryChange: (String?) -> Unit
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            FilterChip(
                selected = selected == null,
                onClick = { onCategoryChange(null) },
                label = { Text("All") },
                modifier = Modifier.testTag("category_all")
            )
        }
        items(categories) { category ->
            FilterChip(
                selected = selected == category,
                onClick = { onCategoryChange(category) },
                label = { Text(category) },
                modifier = Modifier.testTag("category_${category}")
            )
        }
    }
}

@Composable
private fun SnippetPreviewCard(snippet: Snippet) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(snippet.title, style = MaterialTheme.typography.titleSmall)
            Text(snippet.description, style = MaterialTheme.typography.bodySmall)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = snippetPreview(snippet.joinedBody),
                style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SnippetCard(snippet: Snippet, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.testTag("snippet_${snippet.trigger}")
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(snippet.title, style = MaterialTheme.typography.titleMedium)
                AssistChip(
                    onClick = {},
                    label = { Text(snippet.trigger) },
                    colors = AssistChipDefaults.assistChipColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                )
            }
            Text(snippet.description, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = snippetPreview(snippet.joinedBody),
                style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                maxLines = 4,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun SnippetActions(onAddUserSnippet: (String, String, String) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        TextButton(
            onClick = { onAddUserSnippet("Custom Snippet", "custom", "User") },
            modifier = Modifier.testTag("addUserSnippet")
        ) {
            Icon(Icons.Default.Add, contentDescription = null)
            Spacer(modifier = Modifier.width(4.dp))
            Text("Save as user snippet")
        }
    }
}

private fun snippetPreview(body: String): AnnotatedString {
    val regex = Regex("\\$\\{(\\d+):([^}]*)}|\\$(\\d+)|\\$0")
    return buildAnnotatedString {
        var cursor = 0
        regex.findAll(body).forEach { match ->
            append(body.substring(cursor, match.range.first))
            when {
                match.groupValues[1].isNotEmpty() -> {
                    val text = match.groupValues[2]
                    pushStyle(SpanStyle(color = Color(0xFF00A0E0)))
                    append(text)
                    pop()
                }

                match.groupValues[3].isNotEmpty() -> {
                    pushStyle(SpanStyle(color = Color(0xFF00A0E0)))
                    append("•")
                    pop()
                }

                else -> {
                    pushStyle(SpanStyle(color = Color(0xFFE07A1F)))
                    append("|")
                    pop()
                }
            }
            cursor = match.range.last + 1
        }
        if (cursor < body.length) {
            append(body.substring(cursor))
        }
    }
}

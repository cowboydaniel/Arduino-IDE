package com.arduino.ide.mobile.snippets

import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.TextFieldValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * State holder for snippets, filtering and snippet insertion within the editor.
 */
class SnippetViewModel(private val repository: SnippetRepository) : ViewModel() {

    data class SnippetUiState(
        val searchQuery: String = "",
        val selectedCategory: String? = null,
        val snippets: List<Snippet> = emptyList(),
        val filtered: List<Snippet> = emptyList(),
        val categories: List<String> = emptyList(),
        val preview: Snippet? = null,
        val activePlaceholderLabel: String? = null
    )

    private val _uiState = MutableStateFlow(SnippetUiState())
    val uiState: StateFlow<SnippetUiState> = _uiState.asStateFlow()

    private val _editorValue = MutableStateFlow(TextFieldValue())
    val editorValue: StateFlow<TextFieldValue> = _editorValue.asStateFlow()

    private var lastTabStops: List<TabStop> = emptyList()
    private var tabIndex: Int = 0
    private var finalCursor: Int = 0

    init {
        viewModelScope.launch {
            repository.snippetsFlow().collect { snippets ->
                val categories = snippets.map { it.category }.distinct().sorted()
                _uiState.update {
                    val filtered = repository.searchSnippets(
                        snippets,
                        it.searchQuery,
                        it.selectedCategory
                    )
                    it.copy(
                        snippets = snippets,
                        filtered = filtered,
                        categories = categories,
                        preview = filtered.firstOrNull() ?: snippets.firstOrNull()
                    )
                }
            }
        }
    }

    fun updateSearchQuery(query: String) {
        _uiState.update { current ->
            val filtered = repository.searchSnippets(current.snippets, query, current.selectedCategory)
            current.copy(searchQuery = query, filtered = filtered, preview = filtered.firstOrNull())
        }
    }

    fun filterByCategory(category: String?) {
        _uiState.update { current ->
            val normalized = category?.takeIf { it.isNotBlank() }
            val filtered = repository.searchSnippets(current.snippets, current.searchQuery, normalized)
            current.copy(selectedCategory = normalized, filtered = filtered, preview = filtered.firstOrNull())
        }
    }

    fun setPreview(snippet: Snippet) {
        _uiState.update { it.copy(preview = snippet) }
    }

    fun setEditorValue(value: TextFieldValue) {
        _editorValue.value = value
    }

    fun insertSnippet(snippet: Snippet) {
        val value = _editorValue.value
        val body = snippet.joinedBody
        val expansion = SnippetExpander.expand(body)
        val cursor = value.selection.end

        val newText = StringBuilder(value.text)
            .insert(cursor, expansion.text)
            .toString()

        val shiftedTabStops = expansion.tabStops.map {
            it.copy(start = it.start + cursor, end = it.end + cursor)
        }
        lastTabStops = shiftedTabStops
        tabIndex = 0
        finalCursor = expansion.finalCursorOffset + cursor

        val selection = shiftedTabStops.firstOrNull()?.let { TextRange(it.start, it.end) }
            ?: TextRange(finalCursor)
        _editorValue.value = value.copy(text = newText, selection = selection)
        _uiState.update { state ->
            state.copy(activePlaceholderLabel = shiftedTabStops.firstOrNull()?.placeholder)
        }
    }

    fun moveToNextPlaceholder() {
        if (lastTabStops.isEmpty()) {
            _editorValue.update { current -> current.copy(selection = TextRange(finalCursor)) }
            _uiState.update { it.copy(activePlaceholderLabel = null) }
            return
        }
        tabIndex += 1
        if (tabIndex < lastTabStops.size) {
            val target = lastTabStops[tabIndex]
            _editorValue.update { current -> current.copy(selection = TextRange(target.start, target.end)) }
            _uiState.update { it.copy(activePlaceholderLabel = target.placeholder) }
        } else {
            _editorValue.update { current -> current.copy(selection = TextRange(finalCursor)) }
            _uiState.update { it.copy(activePlaceholderLabel = null) }
        }
    }

    fun addUserSnippetFromEditor(title: String, trigger: String, category: String) {
        val body = _editorValue.value.text.lines().ifEmpty { listOf("// Empty snippet") }
        val snippet = Snippet(
            id = "user-${title.lowercase().replace(' ', '-')}-${trigger}",
            title = title,
            description = "User snippet captured from editor",
            category = category,
            trigger = trigger,
            body = body,
            isUserDefined = true
        )
        viewModelScope.launch { repository.addUserSnippet(snippet) }
    }

    companion object {
        fun factory(repository: SnippetRepository): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    if (modelClass.isAssignableFrom(SnippetViewModel::class.java)) {
                        @Suppress("UNCHECKED_CAST")
                        return SnippetViewModel(repository) as T
                    }
                    throw IllegalArgumentException("Unknown ViewModel class")
                }
            }
    }
}

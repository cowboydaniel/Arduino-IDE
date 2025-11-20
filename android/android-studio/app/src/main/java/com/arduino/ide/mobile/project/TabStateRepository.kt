package com.arduino.ide.mobile.project

import android.content.Context
import androidx.preference.PreferenceManager
import com.arduino.ide.mobile.editor.EditorState

/**
 * Persists the list of open tabs so the editor can restore state between sessions.
 */
class TabStateRepository(context: Context) {
    private val prefs = PreferenceManager.getDefaultSharedPreferences(context)

    fun saveOpenTabs(paths: List<String>) {
        prefs.edit().putString(KEY_OPEN_TABS, paths.joinToString(";"))
            .apply()
    }

    fun loadOpenTabs(): List<String> {
        val raw = prefs.getString(KEY_OPEN_TABS, null) ?: return emptyList()
        return raw.split(';').filter { it.isNotBlank() }
    }

    fun saveEditorState(path: String, state: EditorState) {
        val serializedFolds = state.foldedRegions.joinToString(",") { "${it.first}:${it.last}" }
        val payload = listOf(state.scrollY, state.firstVisibleLine, serializedFolds).joinToString("|")
        prefs.edit().putString(KEY_EDITOR_STATE_PREFIX + path, payload).apply()
    }

    fun loadEditorState(path: String): EditorState? {
        val raw = prefs.getString(KEY_EDITOR_STATE_PREFIX + path, null) ?: return null
        val parts = raw.split('|')
        if (parts.size < 3) return null
        val folds = parts[2]
            .takeIf { it.isNotBlank() }
            ?.split(',')
            ?.mapNotNull {
                val bounds = it.split(':')
                bounds.getOrNull(0)?.toIntOrNull()?.let { start ->
                    bounds.getOrNull(1)?.toIntOrNull()?.let { end -> start..end }
                }
            } ?: emptyList()
        return EditorState(
            scrollY = parts[0].toIntOrNull() ?: 0,
            firstVisibleLine = parts[1].toIntOrNull() ?: 0,
            foldedRegions = folds
        )
    }

    companion object {
        private const val KEY_OPEN_TABS = "project_open_tabs"
        private const val KEY_EDITOR_STATE_PREFIX = "editor_state_"
    }
}

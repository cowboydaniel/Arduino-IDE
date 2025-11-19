package com.arduino.ide.mobile.project

import android.content.Context
import androidx.preference.PreferenceManager

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

    companion object {
        private const val KEY_OPEN_TABS = "project_open_tabs"
    }
}

package com.arduino.ide.mobile.snippets

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

private val Context.snippetDataStore by preferencesDataStore(name = "snippet_store")

class SnippetRepository(
    private val context: Context,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    private val userSnippetsKey = stringPreferencesKey("user_snippets")
    private var bundledCache: List<Snippet>? = null

    fun snippetsFlow(): Flow<List<Snippet>> = combine(
        bundledSnippetsFlow(),
        userSnippetsFlow()
    ) { bundled, user -> bundled + user }

    suspend fun addUserSnippet(snippet: Snippet) {
        withContext(dispatcher) {
            context.snippetDataStore.edit { prefs ->
                val existing = parseUserSnippets(prefs)
                val updated = existing.filterNot { it.id == snippet.id } + snippet.copy(isUserDefined = true)
                prefs[userSnippetsKey] = toJson(updated)
            }
        }
    }

    suspend fun removeUserSnippet(id: String) {
        withContext(dispatcher) {
            context.snippetDataStore.edit { prefs ->
                val existing = parseUserSnippets(prefs)
                val updated = existing.filterNot { it.id == id }
                prefs[userSnippetsKey] = toJson(updated)
            }
        }
    }

    suspend fun bundledSnippets(): List<Snippet> = bundledCache ?: loadBundledSnippets().also {
        bundledCache = it
    }

    private fun bundledSnippetsFlow(): Flow<List<Snippet>> = flow {
        emit(bundledSnippets())
    }

    private fun userSnippetsFlow(): Flow<List<Snippet>> = context.snippetDataStore.data
        .map { prefs -> parseUserSnippets(prefs) }

    private suspend fun loadBundledSnippets(): List<Snippet> = withContext(dispatcher) {
        val assetManager = context.assets
        val directories = assetManager.list("snippets") ?: emptyArray()
        val snippets = mutableListOf<Snippet>()
        directories.forEach { assetFile ->
            val stream = assetManager.open("snippets/$assetFile")
            val content = stream.bufferedReader().use { it.readText() }
            snippets += parseSnippetArray(JSONArray(content), isUserDefined = false)
        }
        snippets
    }

    private fun parseUserSnippets(prefs: Preferences): List<Snippet> {
        val serialized = prefs[userSnippetsKey] ?: return emptyList()
        return try {
            parseSnippetArray(JSONArray(serialized), isUserDefined = true)
        } catch (ex: Exception) {
            emptyList()
        }
    }

    fun searchSnippets(
        snippets: List<Snippet>,
        query: String,
        category: String?
    ): List<Snippet> {
        if (snippets.isEmpty()) return emptyList()
        val normalizedQuery = query.trim().lowercase()
        return snippets.filter { snippet ->
            val matchesQuery = normalizedQuery.isBlank() ||
                snippet.title.lowercase().contains(normalizedQuery) ||
                snippet.description.lowercase().contains(normalizedQuery) ||
                snippet.trigger.lowercase().contains(normalizedQuery)
            val matchesCategory = category.isNullOrBlank() || snippet.category == category
            matchesQuery && matchesCategory
        }.sortedBy { it.title }
    }

    suspend fun categories(): List<String> {
        val bundledCategories = bundledSnippets().map { it.category }
        val userCategories = userSnippetsFlow().first().map { it.category }
        return (bundledCategories + userCategories).distinct().sorted()
    }

    private fun parseSnippetArray(array: JSONArray, isUserDefined: Boolean): List<Snippet> {
        val snippets = mutableListOf<Snippet>()
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            snippets += parseSnippet(obj, isUserDefined)
        }
        return snippets
    }

    private fun parseSnippet(obj: JSONObject, isUserDefined: Boolean): Snippet {
        val bodyArray = obj.optJSONArray("body") ?: JSONArray()
        val body = mutableListOf<String>()
        for (i in 0 until bodyArray.length()) {
            body += bodyArray.getString(i)
        }
        return Snippet(
            id = obj.getString("id"),
            title = obj.getString("title"),
            description = obj.optString("description"),
            category = obj.optString("category", "General"),
            trigger = obj.optString("trigger", obj.getString("id")),
            body = body,
            isUserDefined = isUserDefined
        )
    }

    private fun toJson(snippets: List<Snippet>): String {
        val array = JSONArray()
        snippets.forEach { snippet ->
            array.put(
                JSONObject().apply {
                    put("id", snippet.id)
                    put("title", snippet.title)
                    put("description", snippet.description)
                    put("category", snippet.category)
                    put("trigger", snippet.trigger)
                    put("body", JSONArray(snippet.body))
                }
            )
        }
        return array.toString()
    }
}

package com.arduino.ide.mobile.snippets

/**
 * Simple model representing a reusable snippet definition.
 */
data class Snippet(
    val id: String,
    val title: String,
    val description: String,
    val category: String,
    val trigger: String,
    val body: List<String>,
    val isUserDefined: Boolean = false
) {
    val joinedBody: String
        get() = body.joinToString("\n")
}

/**
 * Represents an expanded snippet with its tab stop navigation metadata.
 */
data class SnippetExpansion(
    val text: String,
    val tabStops: List<TabStop>,
    val finalCursorOffset: Int
)

data class TabStop(
    val index: Int,
    val start: Int,
    val end: Int,
    val placeholder: String
)

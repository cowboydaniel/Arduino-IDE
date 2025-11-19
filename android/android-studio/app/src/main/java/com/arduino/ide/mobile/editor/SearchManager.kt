package com.arduino.ide.mobile.editor

import com.arduino.ide.mobile.project.SketchFile

enum class SearchScope {
    CURRENT_FILE,
    ALL_OPEN_TABS
}

data class SearchResult(
    val file: SketchFile,
    val matches: List<IntRange>
)

class SearchManager {

    fun findMatches(text: String, query: String, regex: Boolean): List<IntRange> {
        if (query.isEmpty()) return emptyList()
        return if (regex) {
            val pattern = query.toRegex(RegexOption.MULTILINE)
            pattern.findAll(text).map { it.range }.toList()
        } else {
            buildList {
                var index = text.indexOf(query)
                while (index >= 0) {
                    add(index until index + query.length)
                    index = text.indexOf(query, startIndex = index + query.length)
                }
            }
        }
    }

    fun replace(
        text: String,
        query: String,
        replacement: String,
        regex: Boolean
    ): Pair<String, Int> {
        if (query.isEmpty()) return text to 0
        return if (regex) {
            val pattern = query.toRegex(RegexOption.MULTILINE)
            val replaced = pattern.replace(text, replacement)
            replaced to pattern.findAll(text).count()
        } else {
            val occurrences = findMatches(text, query, false).size
            text.replace(query, replacement) to occurrences
        }
    }

    fun findAcrossTabs(
        tabs: List<SketchFile>,
        query: String,
        regex: Boolean,
        scope: SearchScope
    ): List<SearchResult> {
        val targets = if (scope == SearchScope.ALL_OPEN_TABS) tabs else tabs.take(1)
        return targets.map { file ->
            val matches = findMatches(file.content, query, regex)
            SearchResult(file, matches)
        }.filter { it.matches.isNotEmpty() }
    }
}

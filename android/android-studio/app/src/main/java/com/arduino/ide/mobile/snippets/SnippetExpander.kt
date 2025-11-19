package com.arduino.ide.mobile.snippets

import java.util.regex.Pattern

/**
 * Utility that expands VS Code style snippet placeholders (e.g. ${1:pin}, $2, $0) and
 * returns the transformed text along with tab stop metadata.
 */
object SnippetExpander {
    private val placeholderRegex = Pattern.compile("\\$\\{(\\d+):([^}]*)}|\\$(\\d+)|\\$0")

    fun expand(body: String): SnippetExpansion {
        val matcher = placeholderRegex.matcher(body)
        val builder = StringBuilder()
        val tabStops = mutableListOf<TabStop>()
        var lastIndex = 0
        var finalCursor = -1

        while (matcher.find()) {
            if (matcher.start() > lastIndex) {
                builder.append(body.substring(lastIndex, matcher.start()))
            }

            val numberedStop = matcher.group(1)
            val placeholderText = matcher.group(2)
            val simpleStop = matcher.group(3)

            when {
                numberedStop != null -> {
                    val start = builder.length
                    val defaultText = placeholderText ?: ""
                    builder.append(defaultText)
                    val end = builder.length
                    tabStops.add(TabStop(numberedStop.toInt(), start, end, defaultText))
                }

                simpleStop != null -> {
                    val start = builder.length
                    val index = simpleStop.toInt()
                    tabStops.add(TabStop(index, start, start, ""))
                }

                else -> {
                    finalCursor = builder.length
                }
            }

            lastIndex = matcher.end()
        }

        if (lastIndex < body.length) {
            builder.append(body.substring(lastIndex))
        }

        val finalText = builder.toString()
        val resolvedFinalCursor = if (finalCursor >= 0) finalCursor else finalText.length

        val sortedStops = tabStops.sortedWith(compareBy<TabStop> { it.index }.thenBy { it.start })
        return SnippetExpansion(finalText, sortedStops, resolvedFinalCursor)
    }
}

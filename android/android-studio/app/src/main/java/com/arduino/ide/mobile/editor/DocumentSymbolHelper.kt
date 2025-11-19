package com.arduino.ide.mobile.editor

/**
 * Simplified representation of clangd's textDocument/documentSymbol response so we
 * can surface the active function in breadcrumbs even without a live language server.
 */
data class DocumentSymbol(
    val name: String,
    val startLine: Int,
    val endLine: Int,
    val kind: String = "function"
)

object DocumentSymbolHelper {

    fun parseFunctions(content: String): List<DocumentSymbol> {
        val regex = """(void|int|float|double|bool|String)\s+(\w+)\s*\(([^)]*)\)\s*\{""".toRegex()
        return regex.findAll(content).map { matchResult ->
            val linesBefore = content.substring(0, matchResult.range.first).lines().size
            DocumentSymbol(
                name = matchResult.groupValues[2],
                startLine = linesBefore,
                endLine = linesBefore + 1
            )
        }.toList()
    }

    fun contextForCursor(content: String, cursorLine: Int): String? {
        return parseFunctions(content)
            .firstOrNull { cursorLine >= it.startLine && cursorLine <= it.endLine + 20 }
            ?.name
    }
}

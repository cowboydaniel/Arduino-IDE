package com.arduino.ide.mobile.lsp

/** UI-friendly data classes that mirror the pieces of LSP we surface in the app. */
data class CompletionItemUiModel(
    val label: String,
    val detail: String?,
    val insertText: String,
    val documentation: String? = null,
    val autoImportText: String? = null
)

data class HoverUiModel(
    val contents: String,
    val range: TextRange? = null
)

data class DiagnosticUiModel(
    val message: String,
    val severity: Severity,
    val range: TextRange,
    val recoveryHint: String? = null
)

data class TextRange(
    val startLine: Int,
    val startCharacter: Int,
    val endLine: Int,
    val endCharacter: Int
)

enum class Severity { ERROR, WARNING, INFORMATION, HINT }

/** Outbound client-to-server LSP calls we care about. */
sealed interface OutboundMessage {
    data class Initialize(val sessionId: String, val rootUri: String) : OutboundMessage
    data class DidOpen(val uri: String, val languageId: String, val text: String) : OutboundMessage
    data class Completion(val uri: String, val line: Int, val character: Int, val requestId: Long) : OutboundMessage
    data class Hover(val uri: String, val line: Int, val character: Int, val requestId: Long) : OutboundMessage
}

/** Inbound server-to-client signals we translate to UI models. */
sealed interface InboundMessage {
    data class Ready(val clangdPath: String) : InboundMessage
    data class CompletionResult(val requestId: Long, val items: List<CompletionItemUiModel>) : InboundMessage
    data class HoverResult(val requestId: Long, val hover: HoverUiModel?) : InboundMessage
    data class PublishDiagnostics(val uri: String, val diagnostics: List<DiagnosticUiModel>) : InboundMessage
}

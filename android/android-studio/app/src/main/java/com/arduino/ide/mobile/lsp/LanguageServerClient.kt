package com.arduino.ide.mobile.lsp

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.filterIsInstance
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.mapNotNull
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.atomic.AtomicLong

/**
 * Thin Kotlin service that owns a clangd session and translates LSP responses into UI models.
 */
class LanguageServerClient(
    private val transport: LanguageServerTransport,
    dispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    private val scope = CoroutineScope(SupervisorJob() + dispatcher)
    private val requestIds = AtomicLong(1L)

    val diagnostics: Flow<DiagnosticUiModel> = transport.incoming
        .filterIsInstance<InboundMessage.PublishDiagnostics>()
        .map { message ->
            // Emit each diagnostic separately so the UI can render streaming feedback.
            message.diagnostics.firstOrNull()
        }
        .mapNotNull { it }

    suspend fun start(sessionId: String, rootUri: String) {
        transport.start()
        transport.send(OutboundMessage.Initialize(sessionId, rootUri))
    }

    suspend fun openDocument(uri: String, languageId: String, contents: String) {
        transport.send(OutboundMessage.DidOpen(uri, languageId, contents))
    }

    suspend fun requestCompletions(
        uri: String,
        line: Int,
        character: Int
    ): List<CompletionItemUiModel> = withContext(scope.coroutineContext) {
        val requestId = requestIds.getAndIncrement()
        transport.send(OutboundMessage.Completion(uri, line, character, requestId))
        transport.incoming
            .filterIsInstance<InboundMessage.CompletionResult>()
            .first { it.requestId == requestId }
            .items
    }

    suspend fun requestHover(
        uri: String,
        line: Int,
        character: Int
    ): HoverUiModel? = withContext(scope.coroutineContext) {
        val requestId = requestIds.getAndIncrement()
        transport.send(OutboundMessage.Hover(uri, line, character, requestId))
        transport.incoming
            .filterIsInstance<InboundMessage.HoverResult>()
            .first { it.requestId == requestId }
            .hover
    }

    fun streamDiagnostics(uri: String, onDiagnostic: (DiagnosticUiModel) -> Unit) {
        scope.launch {
            diagnostics.collect { diagnostic ->
                if (diagnostic != null) {
                    onDiagnostic(diagnostic)
                }
            }
        }
    }

    suspend fun stop() {
        transport.stop()
    }
}

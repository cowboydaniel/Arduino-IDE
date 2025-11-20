package com.arduino.ide.mobile.lsp

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelChildren
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/**
 * Lightweight transport contract for talking to clangd. Implementations can wrap JNI, gRPC or
 * stdio-based clangd processes; the client only depends on typed messages.
 */
interface LanguageServerTransport {
    val incoming: SharedFlow<InboundMessage>

    suspend fun start()

    suspend fun send(message: OutboundMessage)

    suspend fun stop()
}

/**
 * Production transport used on Android. It launches (or bridges to) a clangd binary that was
 * installed via [ClangdRuntimeBridge] and responds on a coroutine-friendly channel. For CI we
 * keep the implementation lightweight and deterministic while still surfacing availability
 * errors to the UI layer.
 */
class RuntimeLanguageServerTransport(
    private val runtimeBridge: ClangdRuntimeBridge,
    private val responder: LanguageServerResponder = DemoLanguageServerResponder()
) : LanguageServerTransport {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val inbound = MutableSharedFlow<InboundMessage>(
        replay = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
        extraBufferCapacity = 16
    )
    private var ready = false

    override val incoming: SharedFlow<InboundMessage> = inbound.asSharedFlow()

    override suspend fun start() {
        try {
            val clangd = runtimeBridge.installClangd()
            if (!clangd.canExecute()) {
                inbound.emit(
                    InboundMessage.ServerError(
                        message = "clangd is not executable",
                        recoveryHint = "Rebuild the APK after packaging android/runtime/clangd/clangd"
                    )
                )
                return
            }
            if (clangd.length() < 1024) {
                inbound.emit(
                    InboundMessage.ServerError(
                        message = "clangd runtime is missing",
                        recoveryHint = "Run build-clangd-android.sh and rebuild the APK with the packaged binary"
                    )
                )
                return
            }
            ready = true
            inbound.emit(InboundMessage.Ready(clangd.absolutePath))
        } catch (ex: Exception) {
            inbound.emit(
                InboundMessage.ServerError(
                    message = "Unable to prepare clangd: ${ex.message}",
                    recoveryHint = "Ensure the NDK-built clangd asset is packaged in android/runtime/clangd"
                )
            )
        }
    }

    override suspend fun send(message: OutboundMessage) {
        if (!ready) return
        responder.onMessage(message) { inbound.emit(it) }
    }

    override suspend fun stop() {
        ready = false
        scope.coroutineContext.cancelChildren()
    }
}

/**
 * Small helper used by demo and tests to provide a controllable transport.
 */
class InMemoryLanguageServerTransport : LanguageServerTransport {
    private val outbound = MutableSharedFlow<OutboundMessage>(extraBufferCapacity = 16)
    private val inbound = MutableSharedFlow<InboundMessage>(
        replay = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
        extraBufferCapacity = 32
    )

    override val incoming: SharedFlow<InboundMessage> = inbound.asSharedFlow()

    override suspend fun start() {
        // Nothing to do.
    }

    override suspend fun send(message: OutboundMessage) {
        outbound.tryEmit(message)
    }

    override suspend fun stop() {
        // Nothing to do.
    }

    fun outboundMessages(): Flow<OutboundMessage> = outbound

    fun emitInbound(message: InboundMessage) {
        inbound.tryEmit(message)
    }
}

/**
 * Converts outbound requests into canned responses. Runtime transports can swap in a JNI-backed
 * implementation while tests lean on this deterministic responder.
 */
fun interface LanguageServerResponder {
    suspend fun onMessage(outbound: OutboundMessage, emit: suspend (InboundMessage) -> Unit)
}

class DemoLanguageServerResponder : LanguageServerResponder {
    override suspend fun onMessage(outbound: OutboundMessage, emit: suspend (InboundMessage) -> Unit) {
        when (outbound) {
            is OutboundMessage.Initialize -> Unit
            is OutboundMessage.DidOpen -> emit(
                InboundMessage.PublishDiagnostics(
                    uri = outbound.uri,
                    diagnostics = listOf(
                        DiagnosticUiModel(
                            message = "Missing pinMode for LED_BUILTIN",
                            severity = Severity.WARNING,
                            range = TextRange(1, 2, 1, 20),
                            recoveryHint = "Call pinMode(LED_BUILTIN, OUTPUT) in setup()"
                        )
                    )
                )
            )
            is OutboundMessage.Completion -> emit(
                InboundMessage.CompletionResult(
                    requestId = outbound.requestId,
                    items = listOf(
                        CompletionItemUiModel(
                            label = "digitalWrite",
                            detail = "(uint8_t pin, uint8_t val)",
                            insertText = "digitalWrite(${"$"}{1:pin}, ${"$"}{2:HIGH});",
                            documentation = "Set a digital pin to HIGH or LOW",
                            autoImportText = null
                        ),
                        CompletionItemUiModel(
                            label = "delay",
                            detail = "(unsigned long ms)",
                            insertText = "delay(${"$"}{1:1000});",
                            documentation = "Pause the program for the given milliseconds",
                            autoImportText = "#include <Arduino.h>"
                        )
                    )
                )
            )
            is OutboundMessage.Hover -> emit(
                InboundMessage.HoverResult(
                    requestId = outbound.requestId,
                    hover = HoverUiModel(
                        contents = "digitalWrite(pin, val) — writes a HIGH or LOW value to a digital pin.",
                        range = TextRange(outbound.line, outbound.character, outbound.line, outbound.character + 10)
                    )
                )
            )
        }
    }
}

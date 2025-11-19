package com.arduino.ide.mobile.lsp

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

/**
 * Demo transport used inside MainActivity to provide live-looking LSP responses without shipping
 * a real clangd binary in CI. It also doubles as a simple integration harness for unit tests.
 */
class DemoLanguageServerTransport : LanguageServerTransport {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val inbound = MutableSharedFlow<InboundMessage>(replay = 1)
    override val incoming: SharedFlow<InboundMessage> = inbound.asSharedFlow()

    override suspend fun start() {
        inbound.emit(InboundMessage.Ready("/data/data/com.arduino.ide.mobile/files/lsp-runtime/clangd"))
    }

    override suspend fun send(message: OutboundMessage) {
        when (message) {
            is OutboundMessage.Initialize -> Unit
            is OutboundMessage.DidOpen -> emitDiagnostics(message)
            is OutboundMessage.Completion -> emitCompletions(message)
            is OutboundMessage.Hover -> emitHover(message)
        }
    }

    override suspend fun stop() {
        // Nothing to tear down for the demo.
    }

    private fun emitDiagnostics(message: OutboundMessage.DidOpen) {
        scope.launch {
            delay(100)
            inbound.emit(
                InboundMessage.PublishDiagnostics(
                    uri = message.uri,
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
        }
    }

    private fun emitCompletions(message: OutboundMessage.Completion) {
        scope.launch {
            delay(50)
            inbound.emit(
                InboundMessage.CompletionResult(
                    requestId = message.requestId,
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
        }
    }

    private fun emitHover(message: OutboundMessage.Hover) {
        scope.launch {
            delay(50)
            inbound.emit(
                InboundMessage.HoverResult(
                    requestId = message.requestId,
                    hover = HoverUiModel(
                        contents = "digitalWrite(pin, val) — writes a HIGH or LOW value to a digital pin.",
                        range = TextRange(message.line, message.character, message.line, message.character + 10)
                    )
                )
            )
        }
    }
}

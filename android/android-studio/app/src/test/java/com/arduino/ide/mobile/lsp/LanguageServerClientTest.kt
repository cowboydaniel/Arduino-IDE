package com.arduino.ide.mobile.lsp

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LanguageServerClientTest {
    private val dispatcher = StandardTestDispatcher()

    @Test
    fun `diagnostics emit recovery hints`() = runTest(dispatcher) {
        val transport = InMemoryLanguageServerTransport()
        val client = LanguageServerClient(transport, dispatcher)
        transport.emitInbound(InboundMessage.Ready("/tmp/clangd"))
        transport.emitInbound(
            InboundMessage.PublishDiagnostics(
                uri = "file:///Blink.ino",
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

        val diagnostic = client.diagnostics.first()
        assertEquals("Missing pinMode for LED_BUILTIN", diagnostic.message)
        assertEquals("Call pinMode(LED_BUILTIN, OUTPUT) in setup()", diagnostic.recoveryHint)
    }

    @Test
    fun `completion requests translate into UI models`() = runTest(dispatcher) {
        val transport = object : LanguageServerTransport {
            val inboundFlow = MutableSharedFlow<InboundMessage>(replay = 1)
            override val incoming = inboundFlow
            override suspend fun start() {}
            override suspend fun stop() {}
            override suspend fun send(message: OutboundMessage) {
                if (message is OutboundMessage.Completion) {
                    inboundFlow.emit(
                        InboundMessage.CompletionResult(
                            requestId = message.requestId,
                            items = listOf(
                                CompletionItemUiModel(
                                    label = "digitalWrite",
                                    detail = "(uint8_t pin, uint8_t val)",
                                    insertText = "digitalWrite(pin, HIGH);",
                                    documentation = "Set a digital pin",
                                    autoImportText = "#include <Arduino.h>"
                                )
                            )
                        )
                    )
                }
            }
        }

        val client = LanguageServerClient(transport, dispatcher)
        transport.emitInbound(InboundMessage.Ready("/tmp/clangd"))
        val completions = client.requestCompletions("file:///Blink.ino", 3, 2)

        assertEquals(1, completions.size)
        assertEquals("digitalWrite", completions.first().label)
        assertEquals("#include <Arduino.h>", completions.first().autoImportText)
    }

    @Test
    fun `status surfaces runtime errors and retries`() = runTest(dispatcher) {
        val transport = object : LanguageServerTransport {
            private val inbound = MutableSharedFlow<InboundMessage>(replay = 1)
            private var startCount = 0
            override val incoming = inbound
            override suspend fun start() {
                startCount++
                if (startCount == 1) {
                    inbound.emit(InboundMessage.ServerError("Missing runtime"))
                } else {
                    inbound.emit(InboundMessage.Ready("/tmp/clangd"))
                }
            }

            override suspend fun send(message: OutboundMessage) {}
            override suspend fun stop() {}
        }

        val client = LanguageServerClient(transport, dispatcher)
        val firstStatus = client.start("session", "root")
        assertEquals(LanguageServerStatus.Error("Missing runtime"), firstStatus)

        val secondStatus = client.start("session", "root")
        assertEquals(LanguageServerStatus.Ready("/tmp/clangd"), secondStatus)
    }
}

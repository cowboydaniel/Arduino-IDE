package com.arduino.ide.mobile.lsp

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/**
 * Demo transport kept solely for integration tests and local demos; production flows always rely
 * on the packaged clangd runtime.
 */
class DemoLanguageServerTransport : LanguageServerTransport {
    private val inbound = MutableSharedFlow<InboundMessage>(replay = 1)
    private val responder = DemoLanguageServerResponder()
    override val incoming: SharedFlow<InboundMessage> = inbound.asSharedFlow()

    override suspend fun start() {
        inbound.emit(InboundMessage.Ready("/data/data/com.arduino.ide.mobile/files/lsp-runtime/clangd"))
    }

    override suspend fun send(message: OutboundMessage) {
        responder.onMessage(message) { inbound.emit(it) }
    }

    override suspend fun stop() {
        // Nothing to tear down for the demo.
    }
}

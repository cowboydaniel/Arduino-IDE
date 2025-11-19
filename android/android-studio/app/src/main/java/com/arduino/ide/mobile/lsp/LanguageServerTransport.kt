package com.arduino.ide.mobile.lsp

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

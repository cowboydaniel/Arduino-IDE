package com.arduino.ide.mobile.lsp

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LanguageServerIntegrationTest {
    private val dispatcher = StandardTestDispatcher()

    @Test
    fun `integration flow returns hover and completions`() = runTest(dispatcher) {
        val transport = DemoLanguageServerTransport()
        val client = LanguageServerClient(transport, dispatcher)

        val status = client.start("session", "file:///workspace")
        assertTrue(status is LanguageServerStatus.Ready)
        client.openDocument("file:///workspace/Blink.ino", "cpp", "void setup(){}")

        val completions = client.requestCompletions("file:///workspace/Blink.ino", 1, 1)
        val hover = client.requestHover("file:///workspace/Blink.ino", 1, 1)
        val diagnostic = client.diagnostics.first()

        assertTrue(completions.isNotEmpty())
        assertTrue(hover?.contents?.contains("digitalWrite") == true)
        assertTrue(diagnostic.recoveryHint?.contains("pinMode") == true)
    }
}

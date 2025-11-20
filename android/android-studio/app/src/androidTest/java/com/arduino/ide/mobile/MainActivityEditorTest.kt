package com.arduino.ide.mobile

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.arduino.ide.mobile.editor.ArduinoLanguageDefinition
import com.arduino.ide.mobile.editor.DocumentSymbolHelper
import com.arduino.ide.mobile.editor.EditorState
import com.arduino.ide.mobile.editor.MinimapView
import com.arduino.ide.mobile.project.TabStateRepository
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MainActivityEditorTest {

    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun arduinoLanguageLoadsHighlightingAssets() {
        val language = ArduinoLanguageDefinition.create(context)
        assertTrue(language.newlineHandlers.isNotEmpty())
        assertTrue(language.symbolPairs != null)
    }

    @Test
    fun minimapTracksViewportChanges() {
        val minimapView = MinimapView(context)
        minimapView.setCode("line1\nline2\nline3\nline4")
        minimapView.updateViewport(1, 2)
        assertEquals(1 to 2, minimapView.viewport())
    }

    @Test
    fun editorStatePersistsThroughRepository() {
        val repository = TabStateRepository(context)
        val state = EditorState(scrollY = 24, firstVisibleLine = 3, foldedRegions = listOf(1..2, 4..5))
        repository.saveEditorState("/tmp/test", state)
        val restored = repository.loadEditorState("/tmp/test")
        assertEquals(state, restored)
    }

    @Test
    fun documentSymbolHelperProvidesFunctionContext() {
        val content = """
            void setup() {
              pinMode(LED_BUILTIN, OUTPUT);
            }

            void loop() {
              digitalWrite(LED_BUILTIN, HIGH);
            }
        """.trimIndent()
        val contextName = DocumentSymbolHelper.contextForCursor(content, 5)
        assertEquals("loop", contextName)
    }
}

package com.arduino.ide.mobile.editor

import com.arduino.ide.mobile.project.SketchFile
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchManagerTest {

    private val manager = SearchManager()

    @Test
    fun `regex find respects escaped characters`() {
        val text = "pinMode(LED_BUILTIN, OUTPUT); // call digitalWrite later"
        val matches = manager.findMatches(text, "digitalWrite\\s*\\(.*\\)", regex = true)
        assertEquals(1, matches.size)
    }

    @Test
    fun `replace across tabs aggregates matches`() {
        val files = listOf(
            SketchFile("a.ino", "/tmp/a.ino", "void loop() { digitalWrite(1, HIGH); }"),
            SketchFile("b.cpp", "/tmp/b.cpp", "int readSensor() { return analogRead(1); }")
        )
        val results = manager.findAcrossTabs(files, "\\d", regex = true, scope = SearchScope.ALL_OPEN_TABS)
        assertEquals(2, results.size)
        val replaced = manager.replace(files.first().content, "HIGH", "LOW", regex = false)
        assertEquals(true, replaced.first.contains("LOW"))
    }

    @Test
    fun `literal search finds overlapping edge cases`() {
        val text = "delay delay delay"
        val matches = manager.findMatches(text, "delay", regex = false)
        assertEquals(3, matches.size)
        assertTrue(matches.all { text.substring(it) == "delay" })
    }
}

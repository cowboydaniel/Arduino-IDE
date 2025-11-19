package com.arduino.ide.mobile.project

/**
 * Represents a single sketch source file that can be opened in the editor.
 */
data class SketchFile(
    val name: String,
    val path: String,
    var content: String
)

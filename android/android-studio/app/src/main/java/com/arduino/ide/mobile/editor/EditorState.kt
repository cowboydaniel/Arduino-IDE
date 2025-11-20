package com.arduino.ide.mobile.editor

data class EditorState(
    val scrollY: Int = 0,
    val firstVisibleLine: Int = 0,
    val foldedRegions: List<IntRange> = emptyList()
)

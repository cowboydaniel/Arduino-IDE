package com.arduino.ide.mobile.editor

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View

class MinimapView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#3A3F4B")
        strokeWidth = 2f
    }
    private val windowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#5FA8FF")
        alpha = 80
    }
    private val foldPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#FFC66D")
        strokeWidth = 3f
    }

    private var lines: List<String> = emptyList()
    private var firstVisibleLine: Int = 0
    private var visibleLineCount: Int = 0
    private var foldedRanges: List<IntRange> = emptyList()

    fun setCode(text: String) {
        lines = text.lines()
        invalidate()
    }

    fun updateViewport(first: Int, count: Int) {
        firstVisibleLine = first
        visibleLineCount = count
        invalidate()
    }

    fun viewport(): Pair<Int, Int> = firstVisibleLine to visibleLineCount

    fun setFoldRegions(regions: List<IntRange>) {
        foldedRanges = regions
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (lines.isEmpty()) return
        val lineHeight = (height.toFloat() / lines.size.coerceAtLeast(1)).coerceAtLeast(2f)
        lines.forEachIndexed { index, line ->
            val y = index * lineHeight + lineHeight / 2
            val normalizedLength = line.length.coerceAtMost(120)
            val lengthRatio = normalizedLength / 120f
            val barWidth = paddingLeft + (width - paddingLeft - paddingRight) * lengthRatio
            canvas.drawLine(0f, y, barWidth, y, linePaint)
        }

        foldedRanges.forEach { range ->
            val top = range.first * lineHeight
            val bottom = (range.last + 1) * lineHeight
            canvas.drawRect(0f, top, width.toFloat(), bottom, foldPaint)
        }

        if (visibleLineCount > 0) {
            val top = firstVisibleLine * lineHeight
            val bottom = (firstVisibleLine + visibleLineCount) * lineHeight
            canvas.drawRect(0f, top, width.toFloat(), bottom, windowPaint)
        }
    }
}

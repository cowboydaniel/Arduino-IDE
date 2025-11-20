package com.arduino.ide.mobile.editor

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.arduino.ide.mobile.databinding.ItemEditorPageBinding
import com.arduino.ide.mobile.project.SketchFile
import com.arduino.ide.mobile.editor.EditorState
import io.github.rosemoe.sora.event.ScrollEvent
import io.github.rosemoe.sora.event.SelectionChangeEvent
import io.github.rosemoe.sora.widget.CodeEditor

class EditorTabAdapter(
    private val inflater: LayoutInflater,
    private val files: MutableList<SketchFile>
) : RecyclerView.Adapter<EditorTabAdapter.EditorViewHolder>() {

    var onCursorChange: ((SketchFile, Int) -> Unit)? = null
    var onStateChange: ((SketchFile, EditorState) -> Unit)? = null
    var loadState: ((SketchFile) -> EditorState?)? = null

    private val language by lazy { ArduinoLanguageDefinition.create(inflater.context) }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): EditorViewHolder {
        val binding = ItemEditorPageBinding.inflate(inflater, parent, false)
        return EditorViewHolder(binding)
    }

    override fun getItemCount(): Int = files.size

    override fun onBindViewHolder(holder: EditorViewHolder, position: Int) {
        holder.bind(files[position])
    }

    fun getFile(position: Int): SketchFile = files[position]

    fun removeAt(position: Int) {
        files.removeAt(position)
        notifyItemRemoved(position)
    }

    fun move(from: Int, to: Int) {
        if (from == to) return
        val file = files.removeAt(from)
        files.add(to, file)
        notifyItemMoved(from, to)
    }

    fun updateFile(updated: SketchFile) {
        val index = files.indexOfFirst { it.path == updated.path }
        if (index >= 0) {
            files[index] = updated
            notifyItemChanged(index)
        }
    }

    fun openFiles(): List<SketchFile> = files.toList()

    inner class EditorViewHolder(
        private val binding: ItemEditorPageBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(file: SketchFile) {
            val foldRegions = computeFoldRegions(file.content)
            binding.minimap.setCode(file.content)
            binding.minimap.setFoldRegions(foldRegions)

            binding.codeEditor.apply {
                setEditorLanguage(language)
                setText(file.content)
                setLineNumberEnabled(true)
                setHighlightCurrentLine(true)
                setBlockLineEnabled(true)
                setPinLineNumber(true)
                setFirstLineNumberAlwaysVisible(true)
                setHighlightCurrentBlock(true)
                setTextSize(16f)

                binding.minimap.updateViewport(firstVisibleLine, visibleLineCount())
                onStateChange?.invoke(
                    file,
                    EditorState(
                        scrollY = scrollY,
                        firstVisibleLine = firstVisibleLine,
                        foldedRegions = foldRegions
                    )
                )

                loadState?.invoke(file)?.let { state ->
                    scrollTo(scrollX, state.scrollY)
                    ensurePositionVisible(state.firstVisibleLine, 0)
                    binding.minimap.updateViewport(state.firstVisibleLine, visibleLineCount())
                }

                subscribeAlways(ScrollEvent::class.java) { event ->
                    val first = firstVisibleLine
                    val count = visibleLineCount()
                    binding.minimap.updateViewport(first, count)
                    onStateChange?.invoke(
                        file,
                        EditorState(
                            scrollY = event.endY,
                            firstVisibleLine = first,
                            foldedRegions = foldRegions
                        )
                    )
                }

                subscribeAlways(SelectionChangeEvent::class.java) { event ->
                    onCursorChange?.invoke(file, event.right.line + 1)
                }
            }
        }

        private fun CodeEditor.visibleLineCount(): Int =
            (lastVisibleLine - firstVisibleLine).coerceAtLeast(0) + 1

        private fun computeFoldRegions(content: String): List<IntRange> {
            val stack = ArrayDeque<Int>()
            val regions = mutableListOf<IntRange>()
            content.lines().forEachIndexed { index, line ->
                val trimmed = line.trim()
                if (trimmed.endsWith("{")) {
                    stack.addLast(index)
                }
                if (trimmed.startsWith("}")) {
                    val start = stack.removeLastOrNull()
                    if (start != null && start < index) {
                        regions.add(start..index)
                    }
                }
            }
            return regions
        }
    }
}

package com.arduino.ide.mobile.editor

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.arduino.ide.mobile.databinding.ItemEditorPageBinding
import com.arduino.ide.mobile.project.SketchFile

class EditorTabAdapter(
    private val inflater: LayoutInflater,
    private val files: MutableList<SketchFile>
) : RecyclerView.Adapter<EditorTabAdapter.EditorViewHolder>() {

    var onCursorChange: ((SketchFile, Int) -> Unit)? = null

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
            val codeLines = file.content.lines()
            val lineNumbers = codeLines.indices.joinToString("\n") { (it + 1).toString().padStart(2, '0') }
            binding.lineNumbers.text = lineNumbers
            binding.codeListing.text = file.content
            binding.codeListing.setOnClickListener {
                val cursorLine = binding.codeListing.layout?.getLineForOffset(0) ?: 0
                onCursorChange?.invoke(file, cursorLine + 1)
            }
        }
    }
}

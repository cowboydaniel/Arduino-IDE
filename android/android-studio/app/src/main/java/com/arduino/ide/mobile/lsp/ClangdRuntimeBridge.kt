package com.arduino.ide.mobile.lsp

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Locates the packaged clangd runtime that is staged under android/runtime and makes it executable
 * for stdio or JNI-based integrations. In a production build the binary is copied into the app's
 * files dir and invoked by {@link ClangdStdioTransport}.
 */
class ClangdRuntimeBridge(private val context: Context) {
    suspend fun installClangd(binaryName: String = "clangd"): File = withContext(Dispatchers.IO) {
        val targetDir = File(context.filesDir, "lsp-runtime").apply { mkdirs() }
        val target = File(targetDir, binaryName)

        // Always replace the on-disk copy to guarantee the packaged asset is used and to avoid
        // silently running with an empty placeholder.
        if (target.exists()) {
            target.delete()
        }

        val packaged = context.assets.list("")?.contains(binaryName) == true
        if (!packaged) {
            throw IllegalStateException("Packaged clangd asset '$binaryName' is missing; run build-clangd-android.sh")
        }

        context.assets.open(binaryName).use { input ->
            target.outputStream().use { output ->
                input.copyTo(output)
            }
        }

        if (!target.setExecutable(true, false)) {
            throw IllegalStateException("Failed to mark clangd executable")
        }

        target
    }
}

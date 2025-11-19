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
        if (!target.exists()) {
            // In a real build we would stream the asset to disk. For now leave a placeholder so
            // callers can reference the path without shipping a real binary in CI.
            target.writeText("placeholder clangd binary; replace during packaging")
            target.setExecutable(true)
        }
        target
    }
}

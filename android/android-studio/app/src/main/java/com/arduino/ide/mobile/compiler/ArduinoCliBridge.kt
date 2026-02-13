package com.arduino.ide.mobile.compiler

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Extracts and manages the arduino-cli ARM64 binary bundled as an APK asset.
 *
 * On first launch the binary is copied from assets into the app's private files directory
 * and marked executable. Subsequent launches reuse the existing copy unless forced to
 * reinstall. The bridge provides methods to run arduino-cli commands and parse their output.
 */
class ArduinoCliBridge(private val context: Context) {

    companion object {
        private const val TAG = "ArduinoCliBridge"
        private const val BINARY_NAME = "arduino-cli"
        private const val RUNTIME_DIR = "arduino-cli-runtime"
        private const val DATA_DIR = "arduino-cli-data"
        private const val SKETCH_DIR = "sketches"
    }

    private val runtimeDir = File(context.filesDir, RUNTIME_DIR).apply { mkdirs() }
    private val dataDir = File(context.filesDir, DATA_DIR).apply { mkdirs() }
    private val sketchDir = File(context.filesDir, SKETCH_DIR).apply { mkdirs() }
    private val binaryFile = File(runtimeDir, BINARY_NAME)

    /**
     * Install the arduino-cli binary from APK assets if not already present.
     * Returns the path to the executable.
     */
    suspend fun install(): File = withContext(Dispatchers.IO) {
        if (binaryFile.exists() && binaryFile.canExecute() && binaryFile.length() > 1024) {
            Log.d(TAG, "arduino-cli already installed at ${binaryFile.absolutePath}")
            return@withContext binaryFile
        }

        Log.d(TAG, "Installing arduino-cli from assets...")

        val hasAsset = context.assets.list("")?.contains(BINARY_NAME) == true
        if (!hasAsset) {
            throw IllegalStateException(
                "arduino-cli asset not found. Run fetch-arduino-cli-android.sh first."
            )
        }

        if (binaryFile.exists()) binaryFile.delete()

        context.assets.open(BINARY_NAME).use { input ->
            binaryFile.outputStream().use { output ->
                input.copyTo(output, bufferSize = 65536)
            }
        }

        if (!binaryFile.setExecutable(true, false)) {
            throw IllegalStateException("Failed to mark arduino-cli executable")
        }

        Log.d(TAG, "arduino-cli installed: ${binaryFile.length()} bytes")
        binaryFile
    }

    /**
     * Check whether the AVR core is installed.
     */
    suspend fun isCoreInstalled(platform: String): Boolean = withContext(Dispatchers.IO) {
        val result = execute("core", "list", "--format", "text")
        result.exitCode == 0 && result.stdout.contains(platform)
    }

    /**
     * Install an Arduino platform core (e.g. "arduino:avr").
     */
    suspend fun installCore(
        platform: String,
        onOutput: (String) -> Unit = {}
    ): CliResult = withContext(Dispatchers.IO) {
        onOutput("Installing platform $platform...")
        val result = execute("core", "install", platform)
        if (result.exitCode == 0) {
            onOutput("Platform $platform installed successfully")
        } else {
            onOutput("Failed to install $platform: ${result.stderr}")
        }
        result
    }

    /**
     * Compile a sketch and return the path to the output directory containing the .hex file.
     *
     * @param sketchPath path to the .ino sketch file
     * @param fqbn fully qualified board name (e.g. "arduino:avr:uno")
     * @param onOutput callback for real-time build output lines
     * @return CliResult with output directory in stdout on success
     */
    suspend fun compile(
        sketchPath: String,
        fqbn: String,
        onOutput: (String) -> Unit = {}
    ): CliResult = withContext(Dispatchers.IO) {
        val sketchFile = File(sketchPath)
        val outputDir = File(context.cacheDir, "build-${System.currentTimeMillis()}")
        outputDir.mkdirs()

        // arduino-cli expects sketches in a directory matching the sketch name
        val sketchDir = prepareSketchDir(sketchFile)

        onOutput("Compiling ${sketchFile.name} for $fqbn...")

        val result = execute(
            "compile",
            "--fqbn", fqbn,
            "--output-dir", outputDir.absolutePath,
            "--verbose",
            sketchDir.absolutePath
        )

        // Stream output lines
        result.stdout.lines().filter { it.isNotBlank() }.forEach { onOutput(it) }
        if (result.exitCode != 0) {
            result.stderr.lines().filter { it.isNotBlank() }.forEach { onOutput(it) }
        }

        // Return with outputDir path embedded in a success result
        if (result.exitCode == 0) {
            CliResult(0, outputDir.absolutePath, result.stderr)
        } else {
            result
        }
    }

    /**
     * List connected boards.
     */
    suspend fun boardList(): CliResult = withContext(Dispatchers.IO) {
        execute("board", "list", "--format", "json")
    }

    /**
     * Get the list of installed platforms/cores.
     */
    suspend fun coreList(): CliResult = withContext(Dispatchers.IO) {
        execute("core", "list", "--format", "json")
    }

    /**
     * Prepare a sketch directory structure that arduino-cli expects.
     * The sketch must be in a directory with the same name as the .ino file.
     */
    private fun prepareSketchDir(sketchFile: File): File {
        val name = sketchFile.nameWithoutExtension
        val dir = File(sketchDir, name)
        dir.mkdirs()

        val target = File(dir, sketchFile.name)
        if (sketchFile.absolutePath != target.absolutePath) {
            sketchFile.copyTo(target, overwrite = true)
        }
        return dir
    }

    /**
     * Execute an arduino-cli command and capture output.
     */
    private fun execute(vararg args: String): CliResult {
        if (!binaryFile.exists() || !binaryFile.canExecute()) {
            return CliResult(-1, "", "arduino-cli binary not installed")
        }

        val cmd = mutableListOf(binaryFile.absolutePath).apply {
            addAll(args)
            // Point data directory to our private storage
            add("--config-file")
            add(File(dataDir, "arduino-cli.yaml").absolutePath)
        }

        Log.d(TAG, "Executing: ${cmd.joinToString(" ")}")

        return try {
            val env = mapOf(
                "HOME" to context.filesDir.absolutePath,
                "ARDUINO_DATA_DIR" to dataDir.absolutePath,
                "ARDUINO_DOWNLOADS_DIR" to File(dataDir, "staging").absolutePath,
                "ARDUINO_SKETCHBOOK_DIR" to sketchDir.absolutePath
            )

            val process = ProcessBuilder(cmd)
                .directory(runtimeDir)
                .redirectErrorStream(false)
                .also { pb ->
                    pb.environment().putAll(env)
                }
                .start()

            val stdout = process.inputStream.bufferedReader().readText()
            val stderr = process.errorStream.bufferedReader().readText()
            val exitCode = process.waitFor()

            Log.d(TAG, "Exit code: $exitCode")
            if (stderr.isNotBlank()) Log.w(TAG, "stderr: $stderr")

            CliResult(exitCode, stdout, stderr)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to execute arduino-cli: ${e.message}", e)
            CliResult(-1, "", e.message ?: "Unknown execution error")
        }
    }

    /**
     * Create the arduino-cli config file if it doesn't exist.
     */
    suspend fun ensureConfig() = withContext(Dispatchers.IO) {
        val configFile = File(dataDir, "arduino-cli.yaml")
        if (!configFile.exists()) {
            configFile.writeText("""
                board_manager:
                  additional_urls: []
                daemon:
                  port: "50051"
                directories:
                  data: ${dataDir.absolutePath}
                  downloads: ${File(dataDir, "staging").absolutePath}
                  user: ${sketchDir.absolutePath}
                logging:
                  level: info
                  format: text
            """.trimIndent())
            Log.d(TAG, "Created arduino-cli config at ${configFile.absolutePath}")
        }
    }

    /**
     * Find the .hex file in the build output directory for a given FQBN.
     */
    fun findHexFile(outputDir: String, sketchName: String): File? {
        val dir = File(outputDir)
        if (!dir.exists()) return null

        // arduino-cli names the hex file: <sketchname>.ino.hex (AVR)
        // or <sketchname>.ino.bin (ARM/ESP)
        return dir.listFiles()?.firstOrNull { file ->
            file.name.endsWith(".hex") || file.name.endsWith(".ino.hex")
        }
    }

    /**
     * Find the .bin file in the build output directory (for ESP32/ARM boards).
     */
    fun findBinFile(outputDir: String, sketchName: String): File? {
        val dir = File(outputDir)
        if (!dir.exists()) return null

        return dir.listFiles()?.firstOrNull { file ->
            file.name.endsWith(".bin") || file.name.endsWith(".ino.bin")
        }
    }
}

/**
 * Result of an arduino-cli command execution.
 */
data class CliResult(
    val exitCode: Int,
    val stdout: String,
    val stderr: String
) {
    val isSuccess: Boolean get() = exitCode == 0
}

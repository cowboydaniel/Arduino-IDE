package com.arduino.ide.mobile.compiler

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext

/**
 * Service for compiling and uploading Arduino sketches.
 *
 * Currently provides a scaffold implementation with simulated operations.
 * Future versions will integrate with arduino-cli for actual compilation
 * and USB OTG for uploads.
 */
class ArduinoBuildService(private val context: Context) {

    private val _buildState = MutableStateFlow<BuildState>(BuildState.Idle)
    val buildState: StateFlow<BuildState> = _buildState.asStateFlow()

    private val _buildOutput = MutableStateFlow<List<BuildMessage>>(emptyList())
    val buildOutput: StateFlow<List<BuildMessage>> = _buildOutput.asStateFlow()

    /**
     * Verify (compile) the sketch without uploading.
     */
    suspend fun verify(sketchPath: String, board: BoardConfig): BuildResult = withContext(Dispatchers.IO) {
        _buildState.value = BuildState.Compiling
        _buildOutput.value = emptyList()

        appendOutput(BuildMessage.Info("Compiling sketch: $sketchPath"))
        appendOutput(BuildMessage.Info("Board: ${board.fqbn}"))

        // Simulate compilation steps
        delay(500)
        appendOutput(BuildMessage.Info("Detecting libraries..."))
        delay(300)
        appendOutput(BuildMessage.Info("Compiling core..."))
        delay(400)
        appendOutput(BuildMessage.Info("Compiling sketch..."))
        delay(300)
        appendOutput(BuildMessage.Info("Linking..."))
        delay(200)

        // Check for basic syntax errors in the sketch
        val syntaxErrors = performBasicSyntaxCheck(sketchPath)
        if (syntaxErrors.isNotEmpty()) {
            syntaxErrors.forEach { error ->
                appendOutput(BuildMessage.Error(error))
            }
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = syntaxErrors,
                message = "Compilation failed with ${syntaxErrors.size} error(s)"
            )
        }

        appendOutput(BuildMessage.Success("Compilation complete"))
        appendOutput(BuildMessage.Info("Sketch uses 2048 bytes (6%) of program storage space."))
        appendOutput(BuildMessage.Info("Global variables use 184 bytes (8%) of dynamic memory."))

        _buildState.value = BuildState.Idle
        BuildResult.Success(
            binarySize = 2048,
            memoryUsage = 184,
            message = "Compilation successful"
        )
    }

    /**
     * Compile and upload the sketch to the connected board.
     */
    suspend fun upload(sketchPath: String, board: BoardConfig, port: String): BuildResult = withContext(Dispatchers.IO) {
        // First verify the sketch
        val verifyResult = verify(sketchPath, board)
        if (verifyResult is BuildResult.Failure) {
            return@withContext verifyResult
        }

        _buildState.value = BuildState.Uploading
        appendOutput(BuildMessage.Info("Uploading to ${board.name} on $port..."))

        // Check if port is available
        if (!isPortAvailable(port)) {
            val error = "Port $port not available. Please check USB connection."
            appendOutput(BuildMessage.Error(error))
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = listOf(error),
                message = "Upload failed: port not available"
            )
        }

        // Simulate upload progress
        for (progress in listOf(10, 25, 50, 75, 90, 100)) {
            delay(200)
            appendOutput(BuildMessage.Progress("Uploading... $progress%", progress))
        }

        appendOutput(BuildMessage.Success("Upload complete"))
        _buildState.value = BuildState.Idle

        BuildResult.Success(
            binarySize = 2048,
            memoryUsage = 184,
            message = "Upload successful"
        )
    }

    /**
     * Get list of available serial ports.
     */
    suspend fun getAvailablePorts(): List<SerialPort> = withContext(Dispatchers.IO) {
        // TODO: Implement USB device enumeration
        // For now, return a demo port
        listOf(
            SerialPort(
                path = "/dev/ttyUSB0",
                displayName = "USB Serial Device",
                vendorId = 0x2341,
                productId = 0x0043
            )
        )
    }

    /**
     * Get list of installed boards.
     */
    suspend fun getInstalledBoards(): List<BoardConfig> = withContext(Dispatchers.IO) {
        // TODO: Integrate with arduino-cli board list
        listOf(
            BoardConfig(
                fqbn = "arduino:avr:nano",
                name = "Arduino Nano",
                platform = "arduino:avr"
            ),
            BoardConfig(
                fqbn = "arduino:avr:uno",
                name = "Arduino Uno",
                platform = "arduino:avr"
            ),
            BoardConfig(
                fqbn = "esp32:esp32:esp32",
                name = "ESP32 Dev Module",
                platform = "esp32:esp32"
            )
        )
    }

    private fun appendOutput(message: BuildMessage) {
        _buildOutput.value = _buildOutput.value + message
    }

    private fun performBasicSyntaxCheck(sketchPath: String): List<String> {
        // TODO: Implement actual syntax checking via arduino-cli
        // For now, return empty list (no errors)
        return emptyList()
    }

    private fun isPortAvailable(port: String): Boolean {
        // TODO: Implement actual port check via USB manager
        // For now, simulate that port is available
        return true
    }
}

/**
 * Build state for UI updates.
 */
sealed class BuildState {
    object Idle : BuildState()
    object Compiling : BuildState()
    object Uploading : BuildState()
    object Failed : BuildState()
}

/**
 * Result of a build operation.
 */
sealed class BuildResult {
    data class Success(
        val binarySize: Int,
        val memoryUsage: Int,
        val message: String
    ) : BuildResult()

    data class Failure(
        val errors: List<String>,
        val message: String
    ) : BuildResult()
}

/**
 * Build output message for the console.
 */
sealed class BuildMessage {
    abstract val text: String

    data class Info(override val text: String) : BuildMessage()
    data class Warning(override val text: String) : BuildMessage()
    data class Error(override val text: String) : BuildMessage()
    data class Success(override val text: String) : BuildMessage()
    data class Progress(override val text: String, val percent: Int) : BuildMessage()
}

/**
 * Board configuration.
 */
data class BoardConfig(
    val fqbn: String,
    val name: String,
    val platform: String
)

/**
 * Serial port information.
 */
data class SerialPort(
    val path: String,
    val displayName: String,
    val vendorId: Int,
    val productId: Int
)

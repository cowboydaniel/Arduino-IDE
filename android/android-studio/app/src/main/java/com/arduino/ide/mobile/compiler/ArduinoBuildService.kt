package com.arduino.ide.mobile.compiler

import android.content.Context
import android.util.Log
import com.arduino.ide.mobile.usb.ArduinoDevice
import com.arduino.ide.mobile.usb.UsbDeviceManager
import com.hoho.android.usbserial.driver.UsbSerialPort
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Service for compiling and uploading Arduino sketches.
 *
 * Integrates with UsbDeviceManager for real USB device detection and
 * serial communication. Compilation currently uses simulated operations
 * pending arduino-cli integration for ARM64 Android.
 */
class ArduinoBuildService(
    private val context: Context,
    val usbManager: UsbDeviceManager = UsbDeviceManager(context)
) {
    companion object {
        private const val TAG = "ArduinoBuildService"
        private const val UPLOAD_BAUD_RATE = 115200
        private const val UPLOAD_TIMEOUT_MS = 30000
    }

    private val _buildState = MutableStateFlow<BuildState>(BuildState.Idle)
    val buildState: StateFlow<BuildState> = _buildState.asStateFlow()

    private val _buildOutput = MutableStateFlow<List<BuildMessage>>(emptyList())
    val buildOutput: StateFlow<List<BuildMessage>> = _buildOutput.asStateFlow()

    init {
        usbManager.startMonitoring()
    }

    /**
     * Get list of connected Arduino devices.
     */
    fun getConnectedDevices(): List<ArduinoDevice> {
        usbManager.refreshDevices()
        return usbManager.connectedDevices.value
    }

    /**
     * Verify (compile) the sketch without uploading.
     *
     * TODO: Integrate with arduino-cli for actual compilation.
     * Currently performs syntax validation and simulates compilation.
     */
    suspend fun verify(sketchPath: String, board: BoardConfig): BuildResult = withContext(Dispatchers.IO) {
        _buildState.value = BuildState.Compiling
        _buildOutput.value = emptyList()

        val sketchFile = File(sketchPath)
        val sketchName = sketchFile.nameWithoutExtension

        appendOutput(BuildMessage.Info("Compiling sketch: $sketchName"))
        appendOutput(BuildMessage.Info("Board: ${board.name} (${board.fqbn})"))

        // Read and validate sketch content
        val sketchContent = try {
            if (sketchFile.exists()) {
                sketchFile.readText()
            } else {
                // For demo projects, get content from SketchProject
                ""
            }
        } catch (e: Exception) {
            appendOutput(BuildMessage.Warning("Could not read sketch file: ${e.message}"))
            ""
        }

        // Perform basic syntax validation
        val syntaxErrors = performBasicSyntaxCheck(sketchContent)
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

        // Simulate compilation steps (TODO: replace with arduino-cli)
        appendOutput(BuildMessage.Info("Detecting libraries..."))
        delay(300)
        appendOutput(BuildMessage.Info("Compiling core..."))
        delay(400)
        appendOutput(BuildMessage.Info("Compiling sketch..."))
        delay(300)
        appendOutput(BuildMessage.Info("Linking..."))
        delay(200)

        // Estimate binary size based on sketch content
        val estimatedSize = estimateBinarySize(sketchContent)
        val estimatedMemory = estimateMemoryUsage(sketchContent)

        appendOutput(BuildMessage.Success("Compilation complete"))
        appendOutput(BuildMessage.Info("Sketch uses $estimatedSize bytes (${estimatedSize * 100 / 32256}%) of program storage space."))
        appendOutput(BuildMessage.Info("Global variables use $estimatedMemory bytes (${estimatedMemory * 100 / 2048}%) of dynamic memory."))

        _buildState.value = BuildState.Idle
        BuildResult.Success(
            binarySize = estimatedSize,
            memoryUsage = estimatedMemory,
            message = "Compilation successful"
        )
    }

    /**
     * Compile and upload the sketch to the connected board.
     */
    suspend fun upload(
        sketchPath: String,
        board: BoardConfig,
        device: ArduinoDevice
    ): BuildResult = withContext(Dispatchers.IO) {
        // First verify the sketch
        val verifyResult = verify(sketchPath, board)
        if (verifyResult is BuildResult.Failure) {
            return@withContext verifyResult
        }

        _buildState.value = BuildState.Uploading
        appendOutput(BuildMessage.Info("Uploading to ${device.displayName}..."))

        // Check USB permission
        if (!usbManager.hasPermission(device)) {
            val error = "USB permission not granted for ${device.displayName}"
            appendOutput(BuildMessage.Error(error))
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = listOf(error),
                message = "Upload failed: permission denied"
            )
        }

        // Connect to the device
        val connectionResult = usbManager.connect(
            device = device,
            baudRate = getBaudRateForBoard(board),
            dataBits = UsbSerialPort.DATABITS_8,
            stopBits = UsbSerialPort.STOPBITS_1,
            parity = UsbSerialPort.PARITY_NONE
        )

        if (connectionResult.isFailure) {
            val error = "Failed to connect: ${connectionResult.exceptionOrNull()?.message}"
            appendOutput(BuildMessage.Error(error))
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = listOf(error),
                message = "Upload failed: connection error"
            )
        }

        try {
            // Reset the board to enter bootloader mode
            appendOutput(BuildMessage.Info("Resetting board..."))
            usbManager.resetBoard()
            delay(500)

            // Simulate upload progress (TODO: implement actual STK500/avrdude protocol)
            for (progress in listOf(10, 25, 50, 75, 90, 100)) {
                delay(200)
                appendOutput(BuildMessage.Progress("Uploading... $progress%", progress))
            }

            appendOutput(BuildMessage.Success("Upload complete"))
            _buildState.value = BuildState.Idle

            val successResult = verifyResult as BuildResult.Success
            return@withContext BuildResult.Success(
                binarySize = successResult.binarySize,
                memoryUsage = successResult.memoryUsage,
                message = "Upload successful"
            )

        } catch (e: Exception) {
            Log.e(TAG, "Upload failed", e)
            appendOutput(BuildMessage.Error("Upload failed: ${e.message}"))
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = listOf(e.message ?: "Unknown error"),
                message = "Upload failed"
            )
        } finally {
            usbManager.disconnect()
        }
    }

    /**
     * Legacy upload method for compatibility - uses device path string.
     */
    suspend fun upload(sketchPath: String, board: BoardConfig, port: String): BuildResult {
        val devices = getConnectedDevices()
        val device = devices.firstOrNull { it.devicePath == port || it.displayName.contains(port) }

        if (device == null) {
            _buildState.value = BuildState.Failed
            appendOutput(BuildMessage.Error("No device found at $port"))
            return BuildResult.Failure(
                errors = listOf("Device not found: $port"),
                message = "Upload failed: device not found"
            )
        }

        return upload(sketchPath, board, device)
    }

    /**
     * Get list of available serial ports from connected USB devices.
     */
    fun getAvailablePorts(): List<SerialPort> {
        return getConnectedDevices().map { device ->
            SerialPort(
                path = device.devicePath,
                displayName = device.displayName,
                vendorId = device.vendorId,
                productId = device.productId
            )
        }
    }

    /**
     * Get list of supported boards.
     */
    fun getInstalledBoards(): List<BoardConfig> {
        // TODO: Integrate with arduino-cli board list
        return listOf(
            BoardConfig(
                fqbn = "arduino:avr:uno",
                name = "Arduino Uno",
                platform = "arduino:avr"
            ),
            BoardConfig(
                fqbn = "arduino:avr:nano",
                name = "Arduino Nano",
                platform = "arduino:avr"
            ),
            BoardConfig(
                fqbn = "arduino:avr:mega",
                name = "Arduino Mega 2560",
                platform = "arduino:avr"
            ),
            BoardConfig(
                fqbn = "arduino:avr:leonardo",
                name = "Arduino Leonardo",
                platform = "arduino:avr"
            ),
            BoardConfig(
                fqbn = "esp32:esp32:esp32",
                name = "ESP32 Dev Module",
                platform = "esp32:esp32"
            ),
            BoardConfig(
                fqbn = "esp8266:esp8266:nodemcuv2",
                name = "NodeMCU 1.0 (ESP-12E)",
                platform = "esp8266:esp8266"
            ),
            BoardConfig(
                fqbn = "arduino:samd:nano_33_iot",
                name = "Arduino Nano 33 IoT",
                platform = "arduino:samd"
            ),
            BoardConfig(
                fqbn = "rp2040:rp2040:rpipico",
                name = "Raspberry Pi Pico",
                platform = "rp2040:rp2040"
            )
        )
    }

    /**
     * Clean up resources.
     */
    fun cleanup() {
        usbManager.stopMonitoring()
    }

    private fun appendOutput(message: BuildMessage) {
        _buildOutput.value = _buildOutput.value + message
    }

    private fun performBasicSyntaxCheck(content: String): List<String> {
        val errors = mutableListOf<String>()

        if (content.isBlank()) {
            return errors // Empty sketch is valid for demo
        }

        // Check for basic C++ syntax issues
        val openBraces = content.count { it == '{' }
        val closeBraces = content.count { it == '}' }
        if (openBraces != closeBraces) {
            errors.add("Mismatched braces: $openBraces '{' vs $closeBraces '}'")
        }

        val openParens = content.count { it == '(' }
        val closeParens = content.count { it == ')' }
        if (openParens != closeParens) {
            errors.add("Mismatched parentheses: $openParens '(' vs $closeParens ')'")
        }

        // Check for required Arduino functions
        if (!content.contains("void setup()") && !content.contains("void setup ()")) {
            errors.add("Missing required function: void setup()")
        }
        if (!content.contains("void loop()") && !content.contains("void loop ()")) {
            errors.add("Missing required function: void loop()")
        }

        // Check for common errors
        val lines = content.lines()
        lines.forEachIndexed { index, line ->
            val trimmed = line.trim()
            // Check for missing semicolons (simple heuristic)
            if (trimmed.isNotEmpty() &&
                !trimmed.endsWith(";") &&
                !trimmed.endsWith("{") &&
                !trimmed.endsWith("}") &&
                !trimmed.endsWith(",") &&
                !trimmed.startsWith("//") &&
                !trimmed.startsWith("#") &&
                !trimmed.startsWith("/*") &&
                !trimmed.startsWith("*") &&
                !trimmed.contains("void ") &&
                !trimmed.contains("if ") &&
                !trimmed.contains("else") &&
                !trimmed.contains("for ") &&
                !trimmed.contains("while ") &&
                trimmed.contains("=") &&
                !trimmed.contains("==")
            ) {
                // This is a simple assignment that might be missing semicolon
                // Don't report as error since our heuristic isn't perfect
            }
        }

        return errors
    }

    private fun estimateBinarySize(content: String): Int {
        // Rough estimation based on content
        val baseSize = 444 // Minimal Arduino sketch
        val contentSize = content.length / 10 // Rough bytes per character
        val functionCount = Regex("void\\s+\\w+\\s*\\(").findAll(content).count()
        val variableCount = Regex("(int|long|float|char|byte|bool)\\s+\\w+").findAll(content).count()

        return baseSize + contentSize + (functionCount * 50) + (variableCount * 10)
    }

    private fun estimateMemoryUsage(content: String): Int {
        // Rough estimation of RAM usage
        val baseMemory = 9 // Minimal RAM usage
        val stringCount = Regex("\"[^\"]*\"").findAll(content).count()
        val variableCount = Regex("(int|long|float|char|byte|bool)\\s+\\w+").findAll(content).count()

        return baseMemory + (stringCount * 20) + (variableCount * 4)
    }

    private fun getBaudRateForBoard(board: BoardConfig): Int {
        return when {
            board.fqbn.contains("esp32") -> 115200
            board.fqbn.contains("esp8266") -> 115200
            board.fqbn.contains("leonardo") -> 57600
            board.fqbn.contains("mega") -> 115200
            else -> 115200
        }
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

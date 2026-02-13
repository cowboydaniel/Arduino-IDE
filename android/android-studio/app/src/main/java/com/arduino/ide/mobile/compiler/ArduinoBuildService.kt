package com.arduino.ide.mobile.compiler

import android.content.Context
import android.util.Log
import com.arduino.ide.mobile.usb.ArduinoDevice
import com.arduino.ide.mobile.usb.UsbDeviceManager
import com.hoho.android.usbserial.driver.UsbSerialPort
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Service for compiling and uploading Arduino sketches.
 *
 * Uses the real arduino-cli ARM64 binary for compilation (avr-gcc, linker, etc.)
 * and an STK500v1 protocol implementation for uploading firmware to AVR-based
 * boards (Uno, Nano, Mega) over USB serial via [UsbDeviceManager].
 */
class ArduinoBuildService(
    private val context: Context,
    val usbManager: UsbDeviceManager = UsbDeviceManager(context)
) {
    companion object {
        private const val TAG = "ArduinoBuildService"
    }

    private val cliBridge = ArduinoCliBridge(context)

    private val _buildState = MutableStateFlow<BuildState>(BuildState.Idle)
    val buildState: StateFlow<BuildState> = _buildState.asStateFlow()

    private val _buildOutput = MutableStateFlow<List<BuildMessage>>(emptyList())
    val buildOutput: StateFlow<List<BuildMessage>> = _buildOutput.asStateFlow()

    private var _cliReady = false

    init {
        usbManager.startMonitoring()
    }

    /**
     * Initialize the build toolchain: extract arduino-cli, create config, install AVR core.
     * Should be called once during app startup.
     */
    suspend fun initialize(onStatus: (String) -> Unit = {}) = withContext(Dispatchers.IO) {
        try {
            onStatus("Installing arduino-cli runtime...")
            cliBridge.install()

            onStatus("Configuring arduino-cli...")
            cliBridge.ensureConfig()

            // Check if AVR core is installed, install if not
            if (!cliBridge.isCoreInstalled("arduino:avr")) {
                onStatus("Installing Arduino AVR core (first run, may take a minute)...")
                val result = cliBridge.installCore("arduino:avr") { msg ->
                    onStatus(msg)
                }
                if (!result.isSuccess) {
                    Log.w(TAG, "AVR core install failed: ${result.stderr}")
                    onStatus("Warning: AVR core install failed. Compilation may not work until connected to internet.")
                }
            }

            _cliReady = true
            onStatus("Build toolchain ready")
            Log.d(TAG, "ArduinoBuildService initialized")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize build service: ${e.message}", e)
            onStatus("Build toolchain setup failed: ${e.message}")
        }
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
     * Uses arduino-cli for real compilation with avr-gcc.
     */
    suspend fun verify(sketchPath: String, board: BoardConfig): BuildResult = withContext(Dispatchers.IO) {
        _buildState.value = BuildState.Compiling
        _buildOutput.value = emptyList()

        val sketchFile = File(sketchPath)
        val sketchName = sketchFile.nameWithoutExtension

        appendOutput(BuildMessage.Info("Compiling sketch: $sketchName"))
        appendOutput(BuildMessage.Info("Board: ${board.name} (${board.fqbn})"))

        if (!_cliReady) {
            appendOutput(BuildMessage.Warning("Build toolchain not initialized, attempting setup..."))
            initialize { msg -> appendOutput(BuildMessage.Info(msg)) }
        }

        // Ensure the platform core is installed
        val platformId = board.platform
        if (!cliBridge.isCoreInstalled(platformId)) {
            appendOutput(BuildMessage.Info("Installing platform $platformId..."))
            val installResult = cliBridge.installCore(platformId) { msg ->
                appendOutput(BuildMessage.Info(msg))
            }
            if (!installResult.isSuccess) {
                val error = "Failed to install platform $platformId: ${installResult.stderr}"
                appendOutput(BuildMessage.Error(error))
                _buildState.value = BuildState.Failed
                return@withContext BuildResult.Failure(
                    errors = listOf(error),
                    message = "Platform installation failed"
                )
            }
        }

        // Run real compilation via arduino-cli
        val compileResult = cliBridge.compile(sketchPath, board.fqbn) { line ->
            // Parse arduino-cli output and emit appropriate message types
            when {
                line.contains("error:", ignoreCase = true) ||
                line.contains("Error", ignoreCase = true) ->
                    appendOutput(BuildMessage.Error(line))
                line.contains("warning:", ignoreCase = true) ->
                    appendOutput(BuildMessage.Warning(line))
                else ->
                    appendOutput(BuildMessage.Info(line))
            }
        }

        if (!compileResult.isSuccess) {
            val errors = compileResult.stderr.lines().filter {
                it.contains("error:", ignoreCase = true)
            }.ifEmpty {
                listOf(compileResult.stderr.ifBlank { "Compilation failed" })
            }

            errors.forEach { appendOutput(BuildMessage.Error(it)) }
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = errors,
                message = "Compilation failed with ${errors.size} error(s)"
            )
        }

        // Parse binary size from arduino-cli output
        val outputDir = compileResult.stdout.trim()
        val hexFile = cliBridge.findHexFile(outputDir, sketchName)
        val binarySize = hexFile?.length()?.toInt() ?: 0

        // Try to extract actual sizes from arduino-cli verbose output
        val sizeInfo = extractSizeInfo(compileResult.stderr + compileResult.stdout)

        appendOutput(BuildMessage.Success("Compilation complete"))
        appendOutput(BuildMessage.Info(
            "Sketch uses ${sizeInfo.programSize} bytes (${sizeInfo.programPercent}%) of program storage space. " +
            "Maximum is ${sizeInfo.programMax} bytes."
        ))
        appendOutput(BuildMessage.Info(
            "Global variables use ${sizeInfo.dataSize} bytes (${sizeInfo.dataPercent}%) of dynamic memory, " +
            "leaving ${sizeInfo.dataMax - sizeInfo.dataSize} bytes for local variables. " +
            "Maximum is ${sizeInfo.dataMax} bytes."
        ))

        _buildState.value = BuildState.Idle
        BuildResult.Success(
            binarySize = sizeInfo.programSize,
            memoryUsage = sizeInfo.dataSize,
            message = "Compilation successful",
            outputDir = outputDir
        )
    }

    /**
     * Compile and upload the sketch to the connected board.
     * Uses arduino-cli for compilation and STK500v1 protocol for upload.
     */
    suspend fun upload(
        sketchPath: String,
        board: BoardConfig,
        device: ArduinoDevice
    ): BuildResult = withContext(Dispatchers.IO) {
        // First verify (compile) the sketch
        val verifyResult = verify(sketchPath, board)
        if (verifyResult is BuildResult.Failure) {
            return@withContext verifyResult
        }

        _buildState.value = BuildState.Uploading
        appendOutput(BuildMessage.Info("Uploading to ${device.displayName}..."))

        val successResult = verifyResult as BuildResult.Success
        val outputDir = successResult.outputDir
            ?: run {
                val error = "No build output directory"
                appendOutput(BuildMessage.Error(error))
                _buildState.value = BuildState.Failed
                return@withContext BuildResult.Failure(
                    errors = listOf(error),
                    message = "Upload failed: no compiled firmware"
                )
            }

        // Find the .hex file from compilation output
        val sketchName = File(sketchPath).nameWithoutExtension
        val hexFile = cliBridge.findHexFile(outputDir, sketchName)
        if (hexFile == null || !hexFile.exists()) {
            val error = "Compiled .hex file not found in $outputDir"
            appendOutput(BuildMessage.Error(error))
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = listOf(error),
                message = "Upload failed: firmware file missing"
            )
        }

        appendOutput(BuildMessage.Info("Firmware: ${hexFile.name} (${hexFile.length()} bytes)"))

        // Parse the Intel HEX file
        val hexData = try {
            IntelHexParser.parse(hexFile)
        } catch (e: HexParseException) {
            val error = "Failed to parse hex file: ${e.message}"
            appendOutput(BuildMessage.Error(error))
            _buildState.value = BuildState.Failed
            return@withContext BuildResult.Failure(
                errors = listOf(error),
                message = "Upload failed: bad firmware file"
            )
        }

        appendOutput(BuildMessage.Info("Flash data: ${hexData.size} bytes starting at 0x${hexData.startAddress.toString(16)}"))

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

        // Connect to the device at the board's upload baud rate
        val baudRate = getBaudRateForBoard(board)
        val connectionResult = usbManager.connect(
            device = device,
            baudRate = baudRate,
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
            // Use the STK500v1 programmer for AVR boards
            val programmer = Stk500v1Programmer(usbManager) { message, percent ->
                appendOutput(BuildMessage.Progress(message, percent))
            }

            val uploadSuccess = programmer.program(hexData)

            if (uploadSuccess) {
                appendOutput(BuildMessage.Success("Upload complete"))
                _buildState.value = BuildState.Idle
                return@withContext BuildResult.Success(
                    binarySize = successResult.binarySize,
                    memoryUsage = successResult.memoryUsage,
                    message = "Upload successful",
                    outputDir = outputDir
                )
            } else {
                val error = "STK500v1 programming failed"
                appendOutput(BuildMessage.Error(error))
                _buildState.value = BuildState.Failed
                return@withContext BuildResult.Failure(
                    errors = listOf(error),
                    message = "Upload failed"
                )
            }

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
    fun getInstalledBoards(): List<BoardConfig> = getBuiltinBoards()

    /**
     * Clean up resources.
     */
    fun cleanup() {
        usbManager.stopMonitoring()
    }

    private fun appendOutput(message: BuildMessage) {
        _buildOutput.value = _buildOutput.value + message
    }

    /**
     * Extract program/data size info from arduino-cli output.
     * arduino-cli prints lines like:
     *   Sketch uses 924 bytes (2%) of program storage space. Maximum is 32256 bytes.
     *   Global variables use 9 bytes (0%) of dynamic memory...
     */
    private fun extractSizeInfo(output: String): SizeInfo {
        val programRegex = Regex("""Sketch uses (\d+) bytes \((\d+)%\).*Maximum is (\d+)""")
        val dataRegex = Regex("""Global variables use (\d+) bytes \((\d+)%\).*Maximum is (\d+)""")

        val programMatch = programRegex.find(output)
        val dataMatch = dataRegex.find(output)

        return SizeInfo(
            programSize = programMatch?.groupValues?.get(1)?.toIntOrNull() ?: 0,
            programPercent = programMatch?.groupValues?.get(2)?.toIntOrNull() ?: 0,
            programMax = programMatch?.groupValues?.get(3)?.toIntOrNull() ?: 32256,
            dataSize = dataMatch?.groupValues?.get(1)?.toIntOrNull() ?: 0,
            dataPercent = dataMatch?.groupValues?.get(2)?.toIntOrNull() ?: 0,
            dataMax = dataMatch?.groupValues?.get(3)?.toIntOrNull() ?: 2048
        )
    }

    private fun getBaudRateForBoard(board: BoardConfig): Int {
        return when {
            board.fqbn.contains("leonardo") -> 57600
            board.fqbn.contains("esp32") -> 115200
            board.fqbn.contains("esp8266") -> 115200
            board.fqbn.contains("mega") -> 115200
            else -> 115200
        }
    }

    private fun getBuiltinBoards(): List<BoardConfig> = listOf(
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
            fqbn = "arduino:avr:nano:cpu=atmega328old",
            name = "Arduino Nano (Old Bootloader)",
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

private data class SizeInfo(
    val programSize: Int,
    val programPercent: Int,
    val programMax: Int,
    val dataSize: Int,
    val dataPercent: Int,
    val dataMax: Int
)

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
        val message: String,
        val outputDir: String? = null
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

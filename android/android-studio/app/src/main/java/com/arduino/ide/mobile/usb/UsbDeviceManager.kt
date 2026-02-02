package com.arduino.ide.mobile.usb

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Build
import android.util.Log
import com.hoho.android.usbserial.driver.UsbSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort
import com.hoho.android.usbserial.driver.UsbSerialProber
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.callbackFlow

/**
 * Manages USB device detection and communication for Arduino boards.
 *
 * Supports common USB-to-serial chips:
 * - FTDI FT232, FT2232
 * - Silicon Labs CP210x
 * - Prolific PL2303
 * - CH340/CH341
 * - CDC ACM (Arduino native USB)
 */
class UsbDeviceManager(private val context: Context) {

    companion object {
        private const val TAG = "UsbDeviceManager"
        private const val ACTION_USB_PERMISSION = "com.arduino.ide.mobile.USB_PERMISSION"

        // Known Arduino board identifiers
        private val ARDUINO_VENDORS = mapOf(
            0x2341 to "Arduino SA",
            0x2A03 to "Arduino SRL",
            0x1B4F to "SparkFun",
            0x239A to "Adafruit",
            0x0403 to "FTDI",
            0x10C4 to "Silicon Labs",
            0x067B to "Prolific",
            0x1A86 to "CH340/CH341",
            0x303A to "Espressif",
            0x0483 to "STMicroelectronics",
            0x03EB to "Microchip/Atmel",
            0x16C0 to "Teensy",
            0x2886 to "Seeed Studio",
            0x2E8A to "Raspberry Pi"
        )
    }

    private val usbManager: UsbManager = context.getSystemService(Context.USB_SERVICE) as UsbManager

    private val _connectedDevices = MutableStateFlow<List<ArduinoDevice>>(emptyList())
    val connectedDevices: StateFlow<List<ArduinoDevice>> = _connectedDevices.asStateFlow()

    private val _connectionState = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private var currentConnection: SerialConnection? = null
    private var permissionReceiver: BroadcastReceiver? = null

    /**
     * Start monitoring for USB device connections.
     */
    fun startMonitoring() {
        refreshDevices()
        registerUsbReceiver()
    }

    /**
     * Stop monitoring and clean up resources.
     */
    fun stopMonitoring() {
        unregisterUsbReceiver()
        disconnect()
    }

    /**
     * Refresh the list of connected USB devices.
     */
    fun refreshDevices() {
        val drivers = UsbSerialProber.getDefaultProber().findAllDrivers(usbManager)
        val devices = drivers.map { driver ->
            val device = driver.device
            val vendorName = ARDUINO_VENDORS[device.vendorId] ?: "Unknown"
            ArduinoDevice(
                usbDevice = device,
                driver = driver,
                vendorId = device.vendorId,
                productId = device.productId,
                vendorName = vendorName,
                productName = device.productName ?: "USB Serial Device",
                serialNumber = device.serialNumber,
                portCount = driver.ports.size
            )
        }
        _connectedDevices.value = devices
        Log.d(TAG, "Found ${devices.size} USB serial devices")
    }

    /**
     * Request permission to access a USB device.
     */
    fun requestPermission(device: ArduinoDevice, onResult: (Boolean) -> Unit) {
        if (usbManager.hasPermission(device.usbDevice)) {
            onResult(true)
            return
        }

        val permissionIntent = PendingIntent.getBroadcast(
            context,
            0,
            Intent(ACTION_USB_PERMISSION),
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                PendingIntent.FLAG_MUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
        )

        val receiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context?, intent: Intent?) {
                if (intent?.action == ACTION_USB_PERMISSION) {
                    val granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)
                    context.unregisterReceiver(this)
                    onResult(granted)
                }
            }
        }

        val filter = IntentFilter(ACTION_USB_PERMISSION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            context.registerReceiver(receiver, filter)
        }

        usbManager.requestPermission(device.usbDevice, permissionIntent)
    }

    /**
     * Check if we have permission to access a device.
     */
    fun hasPermission(device: ArduinoDevice): Boolean {
        return usbManager.hasPermission(device.usbDevice)
    }

    /**
     * Connect to a device and open a serial port.
     */
    fun connect(
        device: ArduinoDevice,
        baudRate: Int = 115200,
        dataBits: Int = UsbSerialPort.DATABITS_8,
        stopBits: Int = UsbSerialPort.STOPBITS_1,
        parity: Int = UsbSerialPort.PARITY_NONE
    ): Result<SerialConnection> {
        if (!hasPermission(device)) {
            return Result.failure(SecurityException("USB permission not granted"))
        }

        try {
            val connection = usbManager.openDevice(device.usbDevice)
                ?: return Result.failure(Exception("Failed to open USB device"))

            val port = device.driver.ports.firstOrNull()
                ?: return Result.failure(Exception("No serial ports available"))

            port.open(connection)
            port.setParameters(baudRate, dataBits, stopBits, parity)
            port.dtr = true  // Data Terminal Ready
            port.rts = true  // Request To Send

            val serialConnection = SerialConnection(
                device = device,
                port = port,
                usbConnection = connection,
                baudRate = baudRate
            )

            currentConnection = serialConnection
            _connectionState.value = ConnectionState.Connected(device)

            Log.d(TAG, "Connected to ${device.productName} at $baudRate baud")
            return Result.success(serialConnection)

        } catch (e: Exception) {
            Log.e(TAG, "Failed to connect: ${e.message}", e)
            _connectionState.value = ConnectionState.Error(e.message ?: "Unknown error")
            return Result.failure(e)
        }
    }

    /**
     * Disconnect from the current device.
     */
    fun disconnect() {
        currentConnection?.let { conn ->
            try {
                conn.port.close()
                conn.usbConnection.close()
            } catch (e: Exception) {
                Log.e(TAG, "Error closing connection: ${e.message}", e)
            }
        }
        currentConnection = null
        _connectionState.value = ConnectionState.Disconnected
    }

    /**
     * Write data to the connected device.
     */
    fun write(data: ByteArray): Result<Int> {
        val conn = currentConnection
            ?: return Result.failure(Exception("Not connected"))

        return try {
            val written = conn.port.write(data, 1000)
            Result.success(written)
        } catch (e: Exception) {
            Log.e(TAG, "Write error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Read data from the connected device.
     */
    fun read(buffer: ByteArray, timeout: Int = 1000): Result<Int> {
        val conn = currentConnection
            ?: return Result.failure(Exception("Not connected"))

        return try {
            val read = conn.port.read(buffer, timeout)
            Result.success(read)
        } catch (e: Exception) {
            Log.e(TAG, "Read error: ${e.message}", e)
            Result.failure(e)
        }
    }

    /**
     * Flow of incoming serial data.
     */
    fun dataFlow(): Flow<ByteArray> = callbackFlow {
        val buffer = ByteArray(4096)

        while (currentConnection != null) {
            val result = read(buffer, 100)
            result.onSuccess { bytesRead ->
                if (bytesRead > 0) {
                    trySend(buffer.copyOf(bytesRead))
                }
            }
        }

        awaitClose { }
    }

    /**
     * Trigger a board reset using DTR toggle (for upload).
     */
    fun resetBoard() {
        currentConnection?.port?.let { port ->
            try {
                port.dtr = false
                Thread.sleep(50)
                port.dtr = true
                Thread.sleep(50)
                Log.d(TAG, "Board reset triggered via DTR toggle")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to reset board: ${e.message}", e)
            }
        }
    }

    private fun registerUsbReceiver() {
        if (permissionReceiver != null) return

        permissionReceiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context?, intent: Intent?) {
                when (intent?.action) {
                    UsbManager.ACTION_USB_DEVICE_ATTACHED -> {
                        Log.d(TAG, "USB device attached")
                        refreshDevices()
                    }
                    UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                        Log.d(TAG, "USB device detached")
                        val device = intent.getParcelableExtra<UsbDevice>(UsbManager.EXTRA_DEVICE)
                        if (currentConnection?.device?.usbDevice == device) {
                            disconnect()
                        }
                        refreshDevices()
                    }
                }
            }
        }

        val filter = IntentFilter().apply {
            addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED)
            addAction(UsbManager.ACTION_USB_DEVICE_DETACHED)
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(permissionReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            context.registerReceiver(permissionReceiver, filter)
        }
    }

    private fun unregisterUsbReceiver() {
        permissionReceiver?.let {
            try {
                context.unregisterReceiver(it)
            } catch (e: Exception) {
                Log.e(TAG, "Error unregistering receiver: ${e.message}")
            }
        }
        permissionReceiver = null
    }
}

/**
 * Represents an Arduino-compatible device connected via USB.
 */
data class ArduinoDevice(
    val usbDevice: UsbDevice,
    val driver: UsbSerialDriver,
    val vendorId: Int,
    val productId: Int,
    val vendorName: String,
    val productName: String,
    val serialNumber: String?,
    val portCount: Int
) {
    val displayName: String
        get() = "$vendorName $productName"

    val devicePath: String
        get() = "/dev/bus/usb/${usbDevice.deviceId}"
}

/**
 * Active serial connection to a device.
 */
data class SerialConnection(
    val device: ArduinoDevice,
    val port: UsbSerialPort,
    val usbConnection: android.hardware.usb.UsbDeviceConnection,
    val baudRate: Int
)

/**
 * Connection state for UI updates.
 */
sealed class ConnectionState {
    object Disconnected : ConnectionState()
    data class Connected(val device: ArduinoDevice) : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}

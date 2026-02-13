package com.arduino.ide.mobile.compiler

import android.util.Log
import com.arduino.ide.mobile.usb.UsbDeviceManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

/**
 * Implements the STK500v1 protocol used by the Optiboot bootloader on Arduino Uno,
 * Nano, and other ATmega328P-based boards. Communicates over USB serial via
 * [UsbDeviceManager].
 *
 * Protocol reference: AVR061 - STK500 Communication Protocol (Atmel/Microchip)
 *
 * Flow:
 *   1. Reset board via DTR toggle → bootloader starts
 *   2. Sync with bootloader (STK_GET_SYNC)
 *   3. Enter programming mode (STK_ENTER_PROGMODE)
 *   4. Program flash page by page (STK_LOAD_ADDRESS + STK_PROG_PAGE)
 *   5. Verify by reading back (STK_READ_PAGE)
 *   6. Leave programming mode (STK_LEAVE_PROGMODE)
 */
class Stk500v1Programmer(
    private val usbManager: UsbDeviceManager,
    private val onProgress: (String, Int) -> Unit = { _, _ -> }
) {
    companion object {
        private const val TAG = "Stk500v1"

        // STK500v1 protocol constants
        const val STK_OK: Byte = 0x10
        const val STK_FAILED: Byte = 0x11
        const val STK_UNKNOWN: Byte = 0x12
        const val STK_INSYNC: Byte = 0x14
        const val STK_NOSYNC: Byte = 0x15
        const val CRC_EOP: Byte = 0x20 // 'space'

        const val STK_GET_SYNC: Byte = 0x30
        const val STK_GET_PARAMETER: Byte = 0x41
        const val STK_SET_DEVICE: Byte = 0x42
        const val STK_SET_DEVICE_EXT: Byte = 0x45
        const val STK_ENTER_PROGMODE: Byte = 0x50
        const val STK_LEAVE_PROGMODE: Byte = 0x51
        const val STK_LOAD_ADDRESS: Byte = 0x55
        const val STK_UNIVERSAL: Byte = 0x56
        const val STK_PROG_PAGE: Byte = 0x64
        const val STK_READ_PAGE: Byte = 0x74
        const val STK_READ_SIGN: Byte = 0x75

        // Optiboot page size for ATmega328P
        const val PAGE_SIZE = 128

        // Timeouts
        const val SYNC_TIMEOUT_MS = 500
        const val RESPONSE_TIMEOUT_MS = 1000
        const val SYNC_RETRIES = 10
    }

    /**
     * Program the device with data from a parsed Intel HEX file.
     *
     * @param hexData parsed binary data to flash
     * @return true if programming completed successfully
     */
    suspend fun program(hexData: HexData): Boolean = withContext(Dispatchers.IO) {
        Log.d(TAG, "Starting STK500v1 upload: ${hexData.size} bytes")
        onProgress("Resetting board...", 0)

        // Step 1: Reset the board to enter bootloader
        usbManager.resetBoard()
        delay(250) // Wait for bootloader to initialize

        // Drain any stale data
        drainInput()

        // Step 2: Synchronize with bootloader
        onProgress("Syncing with bootloader...", 2)
        if (!sync()) {
            Log.e(TAG, "Failed to sync with bootloader")
            onProgress("Failed to sync with bootloader", 0)
            return@withContext false
        }
        Log.d(TAG, "Bootloader sync OK")

        // Step 3: Enter programming mode
        onProgress("Entering programming mode...", 5)
        if (!enterProgramMode()) {
            Log.e(TAG, "Failed to enter programming mode")
            onProgress("Failed to enter programming mode", 0)
            return@withContext false
        }
        Log.d(TAG, "Programming mode entered")

        // Step 4: Program flash page by page
        val data = hexData.data
        val totalPages = (data.size + PAGE_SIZE - 1) / PAGE_SIZE

        for (pageIndex in 0 until totalPages) {
            val offset = pageIndex * PAGE_SIZE
            val length = minOf(PAGE_SIZE, data.size - offset)
            val pageData = data.copyOfRange(offset, offset + length)
            val wordAddress = (hexData.startAddress + offset) / 2 // STK500 uses word addresses

            // Load address (word address, little-endian)
            if (!loadAddress(wordAddress)) {
                Log.e(TAG, "Failed to load address 0x${wordAddress.toString(16)}")
                onProgress("Address load failed at page $pageIndex", 0)
                return@withContext false
            }

            // Program the page
            if (!programPage(pageData)) {
                Log.e(TAG, "Failed to program page $pageIndex")
                onProgress("Programming failed at page $pageIndex", 0)
                return@withContext false
            }

            val percent = 5 + ((pageIndex + 1) * 85 / totalPages)
            onProgress("Programming... ${pageIndex + 1}/$totalPages pages", percent)
        }

        Log.d(TAG, "All $totalPages pages programmed")

        // Step 5: Verify (read back and compare)
        onProgress("Verifying...", 92)
        val verified = verifyFlash(hexData)
        if (!verified) {
            Log.e(TAG, "Verification failed")
            onProgress("Verification failed", 0)
            return@withContext false
        }

        // Step 6: Leave programming mode
        onProgress("Leaving programming mode...", 98)
        leaveProgramMode()

        onProgress("Upload complete", 100)
        Log.d(TAG, "Upload successful: ${hexData.size} bytes written")
        true
    }

    /**
     * Attempt to synchronize with the bootloader.
     */
    private fun sync(): Boolean {
        for (attempt in 1..SYNC_RETRIES) {
            Log.d(TAG, "Sync attempt $attempt/$SYNC_RETRIES")

            // Send sync command
            sendCommand(byteArrayOf(STK_GET_SYNC, CRC_EOP))

            // Wait for response
            val response = readResponse(2, SYNC_TIMEOUT_MS)
            if (response != null && response.size >= 2 &&
                response[0] == STK_INSYNC && response[1] == STK_OK
            ) {
                return true
            }

            // Drain and retry
            drainInput()
            Thread.sleep(50)
        }
        return false
    }

    /**
     * Enter programming mode.
     */
    private fun enterProgramMode(): Boolean {
        sendCommand(byteArrayOf(STK_ENTER_PROGMODE, CRC_EOP))
        return expectInsyncOk()
    }

    /**
     * Leave programming mode.
     */
    private fun leaveProgramMode(): Boolean {
        sendCommand(byteArrayOf(STK_LEAVE_PROGMODE, CRC_EOP))
        return expectInsyncOk()
    }

    /**
     * Load word address for the next read/write operation.
     */
    private fun loadAddress(wordAddress: Int): Boolean {
        val addrLow = (wordAddress and 0xFF).toByte()
        val addrHigh = ((wordAddress shr 8) and 0xFF).toByte()
        sendCommand(byteArrayOf(STK_LOAD_ADDRESS, addrLow, addrHigh, CRC_EOP))
        return expectInsyncOk()
    }

    /**
     * Program a page of flash memory.
     */
    private fun programPage(data: ByteArray): Boolean {
        val lengthHigh = ((data.size shr 8) and 0xFF).toByte()
        val lengthLow = (data.size and 0xFF).toByte()

        val cmd = ByteArray(4 + data.size + 1)
        cmd[0] = STK_PROG_PAGE
        cmd[1] = lengthHigh
        cmd[2] = lengthLow
        cmd[3] = 'F'.code.toByte() // 'F' for flash memory

        data.copyInto(cmd, 4)
        cmd[cmd.size - 1] = CRC_EOP

        sendCommand(cmd)
        return expectInsyncOk(timeout = 2000)
    }

    /**
     * Read a page of flash memory for verification.
     */
    private fun readPage(size: Int): ByteArray? {
        val lengthHigh = ((size shr 8) and 0xFF).toByte()
        val lengthLow = (size and 0xFF).toByte()

        sendCommand(byteArrayOf(
            STK_READ_PAGE,
            lengthHigh,
            lengthLow,
            'F'.code.toByte(), // 'F' for flash
            CRC_EOP
        ))

        // Expect: STK_INSYNC + <size bytes of data> + STK_OK
        val response = readResponse(size + 2, RESPONSE_TIMEOUT_MS * 2)
        if (response == null || response.size < size + 2) return null
        if (response[0] != STK_INSYNC || response[response.size - 1] != STK_OK) return null

        return response.copyOfRange(1, 1 + size)
    }

    /**
     * Verify programmed flash by reading it back and comparing.
     */
    private fun verifyFlash(hexData: HexData): Boolean {
        val data = hexData.data
        val totalPages = (data.size + PAGE_SIZE - 1) / PAGE_SIZE

        for (pageIndex in 0 until totalPages) {
            val offset = pageIndex * PAGE_SIZE
            val length = minOf(PAGE_SIZE, data.size - offset)
            val wordAddress = (hexData.startAddress + offset) / 2

            if (!loadAddress(wordAddress)) return false

            val readBack = readPage(length) ?: return false

            // Compare
            for (i in 0 until length) {
                if (readBack[i] != data[offset + i]) {
                    Log.e(TAG, "Verify mismatch at offset ${offset + i}: " +
                            "expected 0x${(data[offset + i].toInt() and 0xFF).toString(16)}, " +
                            "got 0x${(readBack[i].toInt() and 0xFF).toString(16)}")
                    return false
                }
            }
        }
        return true
    }

    /**
     * Send raw bytes to the device.
     */
    private fun sendCommand(data: ByteArray) {
        usbManager.write(data)
    }

    /**
     * Read an expected number of bytes from the device with timeout.
     */
    private fun readResponse(expectedBytes: Int, timeout: Int = RESPONSE_TIMEOUT_MS): ByteArray? {
        val buffer = ByteArray(expectedBytes + 16) // Extra space for safety
        val result = ByteArray(expectedBytes)
        var totalRead = 0
        val deadline = System.currentTimeMillis() + timeout

        while (totalRead < expectedBytes && System.currentTimeMillis() < deadline) {
            val remaining = (deadline - System.currentTimeMillis()).toInt()
            if (remaining <= 0) break

            val readResult = usbManager.read(buffer, minOf(remaining, 100))
            readResult.onSuccess { bytesRead ->
                if (bytesRead > 0) {
                    val toCopy = minOf(bytesRead, expectedBytes - totalRead)
                    buffer.copyInto(result, totalRead, 0, toCopy)
                    totalRead += toCopy
                }
            }
            readResult.onFailure {
                break
            }
        }

        return if (totalRead >= expectedBytes) result else {
            Log.w(TAG, "Read timeout: expected $expectedBytes bytes, got $totalRead")
            if (totalRead > 0) result.copyOf(totalRead) else null
        }
    }

    /**
     * Expect the standard INSYNC + OK response.
     */
    private fun expectInsyncOk(timeout: Int = RESPONSE_TIMEOUT_MS): Boolean {
        val response = readResponse(2, timeout) ?: return false
        return response.size >= 2 && response[0] == STK_INSYNC && response[1] == STK_OK
    }

    /**
     * Drain any pending input data.
     */
    private fun drainInput() {
        val buffer = ByteArray(512)
        var drained = 0
        repeat(10) {
            val result = usbManager.read(buffer, 50)
            result.onSuccess { bytesRead ->
                drained += bytesRead
            }
        }
        if (drained > 0) {
            Log.d(TAG, "Drained $drained bytes of stale input")
        }
    }
}

package com.arduino.ide.mobile.compiler

import java.io.File

/**
 * Parses Intel HEX format files (.hex) produced by avr-gcc/arduino-cli into raw
 * binary data suitable for flashing via STK500 or other bootloader protocols.
 *
 * Intel HEX record format:
 *   :LLAAAATT[DD...]CC
 *   LL   = byte count
 *   AAAA = 16-bit address
 *   TT   = record type (00=data, 01=EOF, 02=ext segment, 04=ext linear)
 *   DD   = data bytes
 *   CC   = two's complement checksum
 */
object IntelHexParser {

    /**
     * Parse a .hex file into a contiguous byte array ready for programming.
     *
     * @param hexFile the Intel HEX file to parse
     * @return HexData containing the binary data and metadata
     * @throws HexParseException on malformed input
     */
    fun parse(hexFile: File): HexData {
        return parse(hexFile.readLines())
    }

    /**
     * Parse Intel HEX lines into binary data.
     */
    fun parse(lines: List<String>): HexData {
        val segments = mutableListOf<DataSegment>()
        var extendedAddress = 0
        var minAddress = Int.MAX_VALUE
        var maxAddress = 0

        for ((lineNum, rawLine) in lines.withIndex()) {
            val line = rawLine.trim()
            if (line.isEmpty()) continue
            if (!line.startsWith(':')) {
                throw HexParseException("Line ${lineNum + 1}: missing start code ':'")
            }

            val hex = line.substring(1)
            if (hex.length < 10) {
                throw HexParseException("Line ${lineNum + 1}: record too short")
            }

            val bytes = hexStringToBytes(hex)
            val byteCount = bytes[0].toInt() and 0xFF
            val address = ((bytes[1].toInt() and 0xFF) shl 8) or (bytes[2].toInt() and 0xFF)
            val recordType = bytes[3].toInt() and 0xFF

            // Verify checksum
            val checksum = bytes.map { it.toInt() and 0xFF }.sum() and 0xFF
            if (checksum != 0) {
                throw HexParseException("Line ${lineNum + 1}: checksum error")
            }

            // Verify byte count matches data length
            if (bytes.size != byteCount + 5) {
                throw HexParseException("Line ${lineNum + 1}: byte count mismatch")
            }

            when (recordType) {
                0x00 -> {
                    // Data record
                    val data = bytes.sliceArray(4 until 4 + byteCount)
                    val fullAddress = extendedAddress + address
                    segments.add(DataSegment(fullAddress, data))

                    if (fullAddress < minAddress) minAddress = fullAddress
                    val end = fullAddress + byteCount
                    if (end > maxAddress) maxAddress = end
                }
                0x01 -> {
                    // End of File
                    break
                }
                0x02 -> {
                    // Extended Segment Address
                    extendedAddress = (((bytes[4].toInt() and 0xFF) shl 8) or
                            (bytes[5].toInt() and 0xFF)) shl 4
                }
                0x04 -> {
                    // Extended Linear Address
                    extendedAddress = (((bytes[4].toInt() and 0xFF) shl 8) or
                            (bytes[5].toInt() and 0xFF)) shl 16
                }
                0x03, 0x05 -> {
                    // Start Segment/Linear Address - ignore
                }
                else -> {
                    throw HexParseException("Line ${lineNum + 1}: unknown record type 0x${recordType.toString(16)}")
                }
            }
        }

        if (segments.isEmpty()) {
            throw HexParseException("No data records found")
        }

        // Merge segments into a contiguous byte array
        if (minAddress == Int.MAX_VALUE) minAddress = 0
        val totalSize = maxAddress - minAddress
        val data = ByteArray(totalSize) { 0xFF.toByte() } // Fill with 0xFF (erased flash)

        for (segment in segments) {
            val offset = segment.address - minAddress
            segment.data.copyInto(data, offset)
        }

        return HexData(
            data = data,
            startAddress = minAddress,
            size = totalSize
        )
    }

    private fun hexStringToBytes(hex: String): ByteArray {
        val len = hex.length / 2
        val bytes = ByteArray(len)
        for (i in 0 until len) {
            bytes[i] = hex.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
        return bytes
    }

    private data class DataSegment(val address: Int, val data: ByteArray)
}

/**
 * Parsed Intel HEX file data.
 */
data class HexData(
    val data: ByteArray,
    val startAddress: Int,
    val size: Int
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is HexData) return false
        return data.contentEquals(other.data) && startAddress == other.startAddress && size == other.size
    }

    override fun hashCode(): Int {
        var result = data.contentHashCode()
        result = 31 * result + startAddress
        result = 31 * result + size
        return result
    }
}

class HexParseException(message: String) : Exception(message)

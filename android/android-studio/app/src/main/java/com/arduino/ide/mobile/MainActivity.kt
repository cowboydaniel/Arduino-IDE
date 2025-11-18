package com.arduino.ide.mobile

import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.arduino.ide.mobile.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { view, windowInsets ->
            val insets = windowInsets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(insets.left, insets.top, insets.right, insets.bottom)
            WindowInsetsCompat.CONSUMED
        }

        binding.boardChip.text = getString(R.string.board_label)
        binding.portChip.text = getString(R.string.port_label)
        binding.statusChip.text = getString(R.string.status_label)
        binding.statusText.text = getString(R.string.status_connected)

        val codeLines = (1..11).joinToString("\n") { it.toString().padStart(2, '0') }
        val codeListing = """
            // Blink an LED on pin 13
            void setup() {
              pinMode(LED_BUILTIN, OUTPUT);
            }

            void loop() {
              digitalWrite(LED_BUILTIN, HIGH);
              delay(1000);
              digitalWrite(LED_BUILTIN, LOW);
              delay(1000);
            }
        """.trimIndent()

        binding.lineNumbers.text = codeLines
        binding.codeListing.text = codeListing

        binding.serialMonitorLog.text = """
            [12:00:01] Opening serial monitor...
            [12:00:02] Syncing board configuration
            [12:00:03] Upload complete
            [12:00:05] Hello, world!
        """.trimIndent()
    }
}

package com.arduino.ide.mobile

import android.os.Bundle
import android.text.Spannable
import android.text.SpannableStringBuilder
import android.text.style.ForegroundColorSpan
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.content.ContextCompat
import androidx.compose.material3.MaterialTheme
import com.arduino.ide.mobile.databinding.ActivityMainBinding
import com.arduino.ide.mobile.snippets.SnippetRepository
import com.arduino.ide.mobile.snippets.SnippetSheet
import com.arduino.ide.mobile.snippets.SnippetViewModel
import com.google.android.material.bottomsheet.BottomSheetBehavior
import java.util.regex.Pattern

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val snippetRepository by lazy { SnippetRepository(this) }
    private val snippetViewModel: SnippetViewModel by viewModels {
        SnippetViewModel.factory(snippetRepository)
    }

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
        binding.codeListing.text = applySyntaxHighlighting(codeListing)

        binding.serialMonitorLog.text = """
            [12:00:01] Opening serial monitor...
            [12:00:02] Syncing board configuration
            [12:00:03] Upload complete
            [12:00:05] Hello, world!
        """.trimIndent()

        configureSnippetPanel()
    }

    private fun applySyntaxHighlighting(code: String): SpannableStringBuilder {
        val builder = SpannableStringBuilder(code)

        val keywordColor = ContextCompat.getColor(this, R.color.arduino_code_keyword)
        val functionColor = ContextCompat.getColor(this, R.color.arduino_code_function)
        val constantColor = ContextCompat.getColor(this, R.color.arduino_code_constant)
        val commentColor = ContextCompat.getColor(this, R.color.arduino_code_comment)

        highlightPattern(builder, code, "\\b(void|int|float|double|bool|return)\\b", keywordColor)
        highlightPattern(builder, code, "\\b(pinMode|digitalWrite|delay)\\b", functionColor)
        highlightPattern(builder, code, "\\b(LED_BUILTIN|OUTPUT|HIGH|LOW)\\b", constantColor)
        highlightPattern(builder, code, "//.*$", commentColor, Pattern.MULTILINE)

        return builder
    }

    private fun highlightPattern(
        builder: SpannableStringBuilder,
        source: String,
        pattern: String,
        color: Int,
        flags: Int = 0
    ) {
        val regex = Pattern.compile(pattern, flags)
        val matcher = regex.matcher(source)
        while (matcher.find()) {
            builder.setSpan(
                ForegroundColorSpan(color),
                matcher.start(),
                matcher.end(),
                Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
            )
        }
    }

    private fun configureSnippetPanel() {
        val sheetBehavior = BottomSheetBehavior.from(binding.snippetBottomSheet)
        val peekHeightPx = (260 * resources.displayMetrics.density).toInt()
        sheetBehavior.peekHeight = peekHeightPx
        sheetBehavior.state = BottomSheetBehavior.STATE_COLLAPSED

        binding.snippetComposeView.setContent {
            MaterialTheme {
                SnippetSheet(
                    uiState = snippetViewModel.uiState,
                    editorValue = snippetViewModel.editorValue,
                    onQueryChange = snippetViewModel::updateSearchQuery,
                    onCategoryChange = snippetViewModel::filterByCategory,
                    onInsertSnippet = snippetViewModel::insertSnippet,
                    onPreviewChange = snippetViewModel::setPreview,
                    onEditorChange = snippetViewModel::setEditorValue,
                    onNextPlaceholder = snippetViewModel::moveToNextPlaceholder,
                    onAddUserSnippet = snippetViewModel::addUserSnippetFromEditor
                )
            }
        }
    }
}

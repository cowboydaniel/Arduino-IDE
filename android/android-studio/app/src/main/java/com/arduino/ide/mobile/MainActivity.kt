package com.arduino.ide.mobile

import android.os.Bundle
import android.widget.ArrayAdapter
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.material3.MaterialTheme
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.arduino.ide.mobile.databinding.ActivityMainBinding
import com.arduino.ide.mobile.snippets.SnippetRepository
import com.arduino.ide.mobile.snippets.SnippetSheet
import com.arduino.ide.mobile.snippets.SnippetViewModel
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.arduino.ide.mobile.databinding.ViewEditorTabBinding
import com.arduino.ide.mobile.editor.DocumentSymbolHelper
import com.arduino.ide.mobile.editor.EditorTabAdapter
import com.arduino.ide.mobile.editor.SearchManager
import com.arduino.ide.mobile.editor.SearchScope
import com.arduino.ide.mobile.project.SketchFile
import com.arduino.ide.mobile.project.SketchProject
import com.arduino.ide.mobile.project.TabStateRepository
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.tabs.TabLayoutMediator
import com.arduino.ide.mobile.lsp.DemoLanguageServerTransport
import com.arduino.ide.mobile.lsp.LanguageServerClient
import kotlinx.coroutines.launch
import java.util.regex.Pattern

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val snippetRepository by lazy { SnippetRepository(this) }
    private val snippetViewModel: SnippetViewModel by viewModels {
        SnippetViewModel.factory(snippetRepository)
    }
    private lateinit var tabMediator: TabLayoutMediator
    private lateinit var adapter: EditorTabAdapter
    private lateinit var project: SketchProject
    private lateinit var tabStateRepository: TabStateRepository

    private val searchManager = SearchManager()
    private val docs = mapOf(
        "digitalWrite" to "Sets the voltage of a digital pin to HIGH or LOW.",
        "pinMode" to "Configures the specified pin to behave either as an input or an output.",
        "delay" to "Pauses the program for the amount of time (in milliseconds)."
    )

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

        tabStateRepository = TabStateRepository(this)
        project = SketchProject.demoProject(this)
        binding.codePath.text = project.basePath.absolutePath
        val codeListing = project.files.firstOrNull()?.content.orEmpty()

        setupTabs(project)
        setupSearchControls()
        val languageServerClient = LanguageServerClient(DemoLanguageServerTransport())
        lifecycleScope.launch {
            languageServerClient.start(sessionId = "demo-session", rootUri = "file:///blink")
            languageServerClient.openDocument("file:///blink/Blink.ino", "cpp", codeListing)

            val completions = languageServerClient.requestCompletions(
                uri = "file:///blink/Blink.ino",
                line = 5,
                character = 6
            )
            binding.completionList.text = completions.joinToString("\n") { item ->
                buildString {
                    append(item.label)
                    item.detail?.let { append(" — ").append(it) }
                    item.autoImportText?.let { append(" (auto-import: ").append(it).append(")") }
                }
            }

            val hover = languageServerClient.requestHover(
                uri = "file:///blink/Blink.ino",
                line = 5,
                character = 6
            )
            binding.hoverText.text = hover?.contents ?: getString(R.string.status_connected)
        }

        lifecycleScope.launch {
            languageServerClient.diagnostics.collect { diagnostic ->
                binding.diagnosticMessage.text = diagnostic.message
                val hint = diagnostic.recoveryHint
                binding.diagnosticHint.text = hint ?: getString(R.string.status_connected)
            }
        }

        binding.serialMonitorLog.text = """
            [12:00:01] Opening serial monitor...
            [12:00:02] Syncing board configuration
            [12:00:03] Upload complete
            [12:00:05] Hello, world!
        """.trimIndent()

        configureSnippetPanel()
    }

    private fun setupTabs(project: SketchProject) {
        val restored = project.resolveTabOrder(tabStateRepository.loadOpenTabs())
        adapter = EditorTabAdapter(layoutInflater, restored.toMutableList())
        adapter.onCursorChange = { file, line ->
            updateBreadcrumb(file, line)
            maybeShowHelp(file, line)
        }
        binding.editorPager.adapter = adapter

        tabMediator = TabLayoutMediator(binding.tabRow, binding.editorPager) { tab, position ->
            tab.customView = createTabView(position)
        }
        tabMediator.attach()

        binding.moveTabLeft.setOnClickListener { moveTab(-1) }
        binding.moveTabRight.setOnClickListener { moveTab(1) }

        binding.editorPager.registerOnPageChangeCallback(object : androidx.viewpager2.widget.ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                val file = adapter.getFile(position)
                updateBreadcrumb(file, 1)
            }
        })

        if (restored.isNotEmpty()) {
            updateBreadcrumb(restored.first(), 1)
        }
    }

    private fun createTabView(position: Int) = ViewEditorTabBinding.inflate(layoutInflater).apply {
        val file = adapter.getFile(position)
        tabTitle.text = file.name
        tabClose.setOnClickListener {
            closeTab(position)
        }
        tabTitle.setTextColor(ContextCompat.getColor(root.context, R.color.arduino_on_primary))
    }.root

    private fun recreateMediator() {
        tabMediator.detach()
        tabMediator = TabLayoutMediator(binding.tabRow, binding.editorPager) { tab, position ->
            tab.customView = createTabView(position)
        }
        tabMediator.attach()
    }

    private fun closeTab(position: Int) {
        if (adapter.itemCount <= 1) return
        adapter.removeAt(position)
        binding.editorPager.adapter = adapter
        recreateMediator()
        binding.editorPager.currentItem = position.coerceAtMost(adapter.itemCount - 1)
    }

    private fun moveTab(offset: Int) {
        val current = binding.editorPager.currentItem
        val target = (current + offset).coerceIn(0, adapter.itemCount - 1)
        adapter.move(current, target)
        recreateMediator()
        binding.editorPager.currentItem = target
    }

    private fun setupSearchControls() {
        val scopeAdapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            listOf(getString(R.string.scope_current_file), getString(R.string.scope_all_tabs))
        )
        binding.searchScope.adapter = scopeAdapter

        binding.findNext.setOnClickListener { performFind() }
        binding.replace.setOnClickListener { performReplace(single = true) }
        binding.replaceAll.setOnClickListener { performReplace(single = false) }
    }

    private fun performFind() {
        val query = binding.findQuery.text?.toString().orEmpty()
        val regex = binding.regexToggle.isChecked
        val scope = if (binding.searchScope.selectedItemPosition == 0) SearchScope.CURRENT_FILE else SearchScope.ALL_OPEN_TABS
        val targets = if (scope == SearchScope.CURRENT_FILE) {
            listOf(adapter.getFile(binding.editorPager.currentItem))
        } else {
            adapter.openFiles()
        }
        val results = searchManager.findAcrossTabs(targets, query, regex, scope)
        if (results.isEmpty()) {
            Snackbar.make(binding.root, R.string.no_match_found, Snackbar.LENGTH_SHORT).show()
            return
        }

        val first = results.first()
        val message = getString(R.string.search_result_message, first.matches.size, first.file.name)
        Snackbar.make(binding.root, message, Snackbar.LENGTH_SHORT).show()
        val lineNumber = first.file.content.substring(0, first.matches.first().first).lines().size
        updateBreadcrumb(first.file, lineNumber)
        maybeShowHelp(first.file, lineNumber)
    }

    private fun performReplace(single: Boolean) {
        val query = binding.findQuery.text?.toString().orEmpty()
        val replacement = binding.replaceQuery.text?.toString().orEmpty()
        val regex = binding.regexToggle.isChecked
        val currentFile = adapter.getFile(binding.editorPager.currentItem)
        lifecycleScope.launch {
            val (updatedText, count) = if (single && !regex) {
                val range = searchManager.findMatches(currentFile.content, query, false).firstOrNull()
                if (range != null) {
                    val newText = currentFile.content.replaceRange(range, replacement)
                    newText to 1
                } else {
                    currentFile.content to 0
                }
            } else {
                searchManager.replace(currentFile.content, query, replacement, regex)
            }

            currentFile.content = updatedText
            adapter.updateFile(currentFile)
            val message = getString(R.string.search_replaced_message, count, currentFile.name)
            Snackbar.make(binding.root, message, Snackbar.LENGTH_SHORT).show()
        }
    }

    private fun updateBreadcrumb(file: SketchFile, line: Int) {
        val function = DocumentSymbolHelper.contextForCursor(file.content, line)
        val breadcrumb = buildString {
            append(project.basePath.absolutePath)
            append(" > ")
            append(file.name)
            if (!function.isNullOrBlank()) {
                append(" > ")
                append(function)
            }
        }
        binding.breadcrumbs.text = breadcrumb
    }

    private fun maybeShowHelp(file: SketchFile, line: Int) {
        val function = DocumentSymbolHelper.contextForCursor(file.content, line)
        val symbol = docs.keys.firstOrNull { file.content.contains(it) && function?.contains(it) == true }
        val description = symbol?.let { docs[it] }
        if (description != null) {
            MaterialAlertDialogBuilder(this)
                .setTitle(getString(R.string.help_dialog_title))
                .setMessage(description)
                .setPositiveButton(android.R.string.ok, null)
                .show()
        }
    }

    override fun onPause() {
        super.onPause()
        tabStateRepository.saveOpenTabs(adapter.openFiles().map { it.path })
    }

    private fun configureSnippetPanel() {
        val sheetBehavior = BottomSheetBehavior.from(binding.snippetBottomSheet)
        sheetBehavior.peekHeight = resources.getDimensionPixelSize(R.dimen.snippet_peek_height)
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

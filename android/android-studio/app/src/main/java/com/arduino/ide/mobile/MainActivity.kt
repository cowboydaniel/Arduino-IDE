package com.arduino.ide.mobile

import android.content.Intent
import android.hardware.usb.UsbManager
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.PopupMenu
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.material3.MaterialTheme
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.arduino.ide.mobile.compiler.ArduinoBuildService
import com.arduino.ide.mobile.compiler.BoardConfig
import com.arduino.ide.mobile.compiler.BuildMessage
import com.arduino.ide.mobile.compiler.BuildResult
import com.arduino.ide.mobile.compiler.BuildState
import com.arduino.ide.mobile.databinding.ActivityMainBinding
import com.arduino.ide.mobile.usb.ArduinoDevice
import com.arduino.ide.mobile.usb.ConnectionState
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
import com.arduino.ide.mobile.lsp.ClangdRuntimeBridge
import com.arduino.ide.mobile.lsp.LanguageServerClient
import com.arduino.ide.mobile.lsp.LanguageServerStatus
import com.arduino.ide.mobile.lsp.RuntimeLanguageServerTransport
import kotlinx.coroutines.Job
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
    private lateinit var languageServerClient: LanguageServerClient
    private lateinit var activeFileUri: String
    private var statusJob: Job? = null
    private var diagnosticJob: Job? = null
    private var buildJob: Job? = null
    private lateinit var buildService: ArduinoBuildService
    private var currentBoard = BoardConfig(
        fqbn = "arduino:avr:uno",
        name = "Arduino Uno",
        platform = "arduino:avr"
    )
    private var selectedDevice: ArduinoDevice? = null
    private var currentLine = 1
    private var currentCol = 1

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

        tabStateRepository = TabStateRepository(this)
        project = SketchProject.demoProject(this)
        val activeFile = project.files.firstOrNull()
        activeFileUri = activeFile?.path?.let { java.io.File(it).toURI().toString() }
            ?: "file://${project.basePath.absolutePath}/Sketch.ino"
        val codeListing = activeFile?.content.orEmpty()

        // Setup title bar
        updateTitleBar()

        // Setup menu bar
        setupMenuBar()

        // Setup toolbar (board selector)
        setupBoardSelector()

        // Setup sidebar
        setupSidebar()

        // Setup tabs and editor
        setupTabs(project)

        // Setup search controls (hidden by default)
        setupSearchControls()

        // Setup status bar
        updateStatusBar()

        // Language server
        languageServerClient = LanguageServerClient(
            RuntimeLanguageServerTransport(ClangdRuntimeBridge(this))
        )
        lifecycleScope.launch {
            attachLanguageServer(activeFile, codeListing)
        }

        // Output panel
        binding.outputLog.text = getString(R.string.build_ready_message)

        // Build service
        buildService = ArduinoBuildService(this)
        lifecycleScope.launch {
            buildService.initialize { status ->
                runOnUiThread { binding.outputLog.text = status }
            }
        }
        setupBuildButtons()
        observeBuildState()
        observeUsbDevices()

        // Snippet panel (hidden by default)
        configureSnippetPanel()

        // Handle USB device if app was launched by USB attachment
        handleUsbIntent(intent)
    }

    // ── Title bar ──────────────────────────────────────────────

    private fun updateTitleBar() {
        val sketchName = project.files.firstOrNull()?.name?.removeSuffix(".ino") ?: "Untitled"
        binding.titleText.text = getString(R.string.title_format, sketchName, getString(R.string.app_version))
    }

    // ── Menu bar ───────────────────────────────────────────────

    private fun setupMenuBar() {
        binding.menuFile.setOnClickListener { showFileMenu(it) }
        binding.menuEdit.setOnClickListener { showEditMenu(it) }
        binding.menuSketch.setOnClickListener { showSketchMenu(it) }
        binding.menuTools.setOnClickListener { showToolsMenu(it) }
        binding.menuHelp.setOnClickListener {
            Snackbar.make(binding.root, "Help menu", Snackbar.LENGTH_SHORT).show()
        }
    }

    private fun showFileMenu(anchor: View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(getString(R.string.menu_new_sketch))
        popup.menu.add(getString(R.string.menu_open))
        popup.menu.add(getString(R.string.menu_save))
        popup.menu.add(getString(R.string.menu_save_as))
        popup.menu.add(getString(R.string.menu_preferences))
        popup.show()
    }

    private fun showEditMenu(anchor: View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(getString(R.string.menu_undo))
        popup.menu.add(getString(R.string.menu_redo))
        popup.menu.add(getString(R.string.menu_cut))
        popup.menu.add(getString(R.string.menu_copy))
        popup.menu.add(getString(R.string.menu_paste))
        popup.menu.add(getString(R.string.menu_select_all))
        popup.menu.add(getString(R.string.menu_find)).setOnMenuItemClickListener {
            toggleFindReplace()
            true
        }
        popup.show()
    }

    private fun showSketchMenu(anchor: View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(getString(R.string.action_verify)).setOnMenuItemClickListener {
            performVerify()
            true
        }
        popup.menu.add(getString(R.string.action_upload)).setOnMenuItemClickListener {
            performUpload()
            true
        }
        popup.show()
    }

    private fun showToolsMenu(anchor: View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(getString(R.string.action_serial_monitor))
        popup.menu.add(getString(R.string.action_serial_plotter))
        popup.menu.add(getString(R.string.menu_board_manager)).setOnMenuItemClickListener {
            showBoardSelectionDialog()
            true
        }
        popup.menu.add(getString(R.string.menu_library_manager))
        popup.show()
    }

    // ── Sidebar ────────────────────────────────────────────────

    private fun setupSidebar() {
        binding.sidebarSketchbook.setOnClickListener {
            Snackbar.make(binding.root, R.string.sidebar_sketchbook, Snackbar.LENGTH_SHORT).show()
        }
        binding.sidebarBoards.setOnClickListener {
            showBoardSelectionDialog()
        }
        binding.sidebarLibraries.setOnClickListener {
            Snackbar.make(binding.root, R.string.sidebar_library_manager, Snackbar.LENGTH_SHORT).show()
        }
        binding.sidebarDebug.setOnClickListener {
            Snackbar.make(binding.root, R.string.sidebar_debug, Snackbar.LENGTH_SHORT).show()
        }
        binding.sidebarSearch.setOnClickListener {
            toggleFindReplace()
        }
    }

    private fun toggleFindReplace() {
        val panel = binding.findReplacePanel
        panel.visibility = if (panel.visibility == View.VISIBLE) View.GONE else View.VISIBLE
    }

    // ── Board Selector (Toolbar) ───────────────────────────────

    private fun setupBoardSelector() {
        binding.boardName.text = currentBoard.name
        binding.boardSelector.setOnClickListener {
            showBoardSelectionDialog()
        }
    }

    // ── Status Bar ─────────────────────────────────────────────

    private fun updateStatusBar() {
        binding.statusLineCol.text = getString(R.string.status_line_col, currentLine, currentCol)
        val portName = selectedDevice?.productName ?: getString(R.string.status_no_board)
        binding.statusBoardInfo.text = getString(R.string.status_board_info, currentBoard.name, portName)
    }

    private fun updateCursorPosition(line: Int, col: Int) {
        currentLine = line
        currentCol = col
        binding.statusLineCol.text = getString(R.string.status_line_col, line, col)
    }

    // ── Build / Upload ─────────────────────────────────────────

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleUsbIntent(intent)
    }

    private fun handleUsbIntent(intent: Intent) {
        if (intent.action == UsbManager.ACTION_USB_DEVICE_ATTACHED) {
            buildService.usbManager.refreshDevices()
            Snackbar.make(binding.root, R.string.usb_device_attached, Snackbar.LENGTH_SHORT).show()
        }
    }

    private fun showBoardSelectionDialog() {
        val boards = buildService.getInstalledBoards()
        val boardNames = boards.map { it.name }.toTypedArray()
        val currentIndex = boards.indexOfFirst { it.fqbn == currentBoard.fqbn }.coerceAtLeast(0)

        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.select_board_title)
            .setSingleChoiceItems(boardNames, currentIndex) { dialog, which ->
                currentBoard = boards[which]
                binding.boardName.text = currentBoard.name
                updateStatusBar()
                dialog.dismiss()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun showPortSelectionDialog() {
        val devices = buildService.getConnectedDevices()

        if (devices.isEmpty()) {
            MaterialAlertDialogBuilder(this)
                .setTitle(R.string.select_port_title)
                .setMessage(R.string.no_devices_connected)
                .setPositiveButton(android.R.string.ok, null)
                .show()
            return
        }

        val deviceNames = devices.map { it.displayName }.toTypedArray()
        val currentIndex = devices.indexOfFirst { it == selectedDevice }.coerceAtLeast(0)

        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.select_port_title)
            .setSingleChoiceItems(deviceNames, currentIndex) { dialog, which ->
                val device = devices[which]
                if (!buildService.usbManager.hasPermission(device)) {
                    buildService.usbManager.requestPermission(device) { granted ->
                        if (granted) {
                            selectDevice(device)
                        } else {
                            Snackbar.make(binding.root, R.string.usb_permission_denied, Snackbar.LENGTH_LONG).show()
                        }
                    }
                } else {
                    selectDevice(device)
                }
                dialog.dismiss()
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun selectDevice(device: ArduinoDevice) {
        selectedDevice = device
        updateStatusBar()
    }

    private fun observeUsbDevices() {
        lifecycleScope.launch {
            buildService.usbManager.connectedDevices.collect { devices ->
                updateDeviceStatus(devices)
            }
        }

        lifecycleScope.launch {
            buildService.usbManager.connectionState.collect { state ->
                when (state) {
                    is ConnectionState.Connected -> {
                        binding.statusIndicator.setBackgroundResource(R.drawable.status_indicator_connected)
                        updateStatusBar()
                    }
                    is ConnectionState.Disconnected -> {
                        binding.statusIndicator.setBackgroundResource(R.drawable.status_indicator)
                        updateStatusBar()
                    }
                    is ConnectionState.Error -> {
                        binding.statusIndicator.setBackgroundResource(R.drawable.status_indicator_error)
                        updateStatusBar()
                    }
                }
            }
        }
    }

    private fun updateDeviceStatus(devices: List<ArduinoDevice>) {
        when {
            devices.isEmpty() -> {
                selectedDevice = null
                updateStatusBar()
            }
            selectedDevice == null && devices.isNotEmpty() -> {
                val firstDevice = devices.first()
                if (buildService.usbManager.hasPermission(firstDevice)) {
                    selectDevice(firstDevice)
                }
            }
            selectedDevice != null && !devices.contains(selectedDevice) -> {
                selectedDevice = null
                updateStatusBar()
                Snackbar.make(binding.root, R.string.device_disconnected_message, Snackbar.LENGTH_SHORT).show()
            }
        }
    }

    private fun setupBuildButtons() {
        binding.uploadButton.setOnClickListener { performUpload() }
        binding.verifyButton.setOnClickListener { performVerify() }
        binding.serialMonitorButton.setOnClickListener {
            Snackbar.make(binding.root, R.string.action_serial_monitor, Snackbar.LENGTH_SHORT).show()
        }
        binding.serialPlotterButton.setOnClickListener {
            Snackbar.make(binding.root, R.string.action_serial_plotter, Snackbar.LENGTH_SHORT).show()
        }
        binding.moreOptionsButton.setOnClickListener {
            showPortSelectionDialog()
        }
    }

    private fun performVerify() {
        if (buildJob?.isActive == true) {
            Snackbar.make(binding.root, R.string.build_already_running, Snackbar.LENGTH_SHORT).show()
            return
        }

        val currentFile = adapter.getFile(binding.editorPager.currentItem)
        buildJob = lifecycleScope.launch {
            binding.verifyButton.isEnabled = false
            binding.uploadButton.isEnabled = false

            val result = buildService.verify(currentFile.path, currentBoard)
            when (result) {
                is BuildResult.Success -> {
                    Snackbar.make(binding.root, result.message, Snackbar.LENGTH_SHORT).show()
                }
                is BuildResult.Failure -> {
                    Snackbar.make(binding.root, result.message, Snackbar.LENGTH_LONG).show()
                }
            }

            binding.verifyButton.isEnabled = true
            binding.uploadButton.isEnabled = true
        }
    }

    private fun performUpload() {
        if (buildJob?.isActive == true) {
            Snackbar.make(binding.root, R.string.build_already_running, Snackbar.LENGTH_SHORT).show()
            return
        }

        val device = selectedDevice
        if (device == null) {
            Snackbar.make(binding.root, R.string.no_device_selected_for_upload, Snackbar.LENGTH_LONG).show()
            return
        }

        if (!buildService.usbManager.hasPermission(device)) {
            buildService.usbManager.requestPermission(device) { granted ->
                if (granted) {
                    doUpload(device)
                } else {
                    Snackbar.make(binding.root, R.string.usb_permission_denied, Snackbar.LENGTH_LONG).show()
                }
            }
            return
        }

        doUpload(device)
    }

    private fun doUpload(device: ArduinoDevice) {
        val currentFile = adapter.getFile(binding.editorPager.currentItem)
        buildJob = lifecycleScope.launch {
            binding.verifyButton.isEnabled = false
            binding.uploadButton.isEnabled = false

            val result = buildService.upload(currentFile.path, currentBoard, device)
            when (result) {
                is BuildResult.Success -> {
                    Snackbar.make(binding.root, result.message, Snackbar.LENGTH_SHORT).show()
                }
                is BuildResult.Failure -> {
                    Snackbar.make(binding.root, result.message, Snackbar.LENGTH_LONG).show()
                }
            }

            binding.verifyButton.isEnabled = true
            binding.uploadButton.isEnabled = true
        }
    }

    private fun observeBuildState() {
        lifecycleScope.launch {
            buildService.buildState.collect { state ->
                when (state) {
                    BuildState.Idle -> { /* Status bar handles idle state */ }
                    BuildState.Compiling -> {
                        binding.outputLog.append("\n${getString(R.string.status_compiling)}")
                    }
                    BuildState.Uploading -> {
                        binding.outputLog.append("\n${getString(R.string.status_uploading)}")
                    }
                    BuildState.Failed -> {
                        binding.outputLog.append("\n${getString(R.string.status_failed)}")
                    }
                }
            }
        }

        lifecycleScope.launch {
            buildService.buildOutput.collect { messages ->
                val logText = messages.joinToString("\n") { msg ->
                    val timestamp = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                        .format(java.util.Date())
                    when (msg) {
                        is BuildMessage.Info -> "[$timestamp] ${msg.text}"
                        is BuildMessage.Warning -> "[$timestamp] WARNING: ${msg.text}"
                        is BuildMessage.Error -> "[$timestamp] ERROR: ${msg.text}"
                        is BuildMessage.Success -> "[$timestamp] ${msg.text}"
                        is BuildMessage.Progress -> "[$timestamp] ${msg.text}"
                    }
                }
                if (logText.isNotEmpty()) {
                    binding.outputLog.text = logText
                }
            }
        }
    }

    // ── Tabs & Editor ──────────────────────────────────────────

    private fun setupTabs(project: SketchProject) {
        val restored = project.resolveTabOrder(tabStateRepository.loadOpenTabs())
        adapter = EditorTabAdapter(layoutInflater, restored.toMutableList())
        adapter.onCursorChange = { file, line ->
            updateCursorPosition(line, 1)
            maybeShowHelp(file, line)
        }
        adapter.loadState = { file -> tabStateRepository.loadEditorState(file.path) }
        adapter.onStateChange = { file, state -> tabStateRepository.saveEditorState(file.path, state) }
        binding.editorPager.adapter = adapter

        tabMediator = TabLayoutMediator(binding.tabRow, binding.editorPager) { tab, position ->
            tab.customView = createTabView(position)
        }
        tabMediator.attach()

        binding.editorPager.registerOnPageChangeCallback(object : androidx.viewpager2.widget.ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                val file = adapter.getFile(position)
                updateCursorPosition(1, 1)
                updateTitleBar()
            }
        })
    }

    private fun createTabView(position: Int) = ViewEditorTabBinding.inflate(layoutInflater).apply {
        val file = adapter.getFile(position)
        tabTitle.text = file.name
        tabClose.setOnClickListener {
            closeTab(position)
        }
        tabTitle.setTextColor(ContextCompat.getColor(root.context, R.color.arduino_text_tab_active))
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

    // ── Search ─────────────────────────────────────────────────

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

    // ── Language Server ────────────────────────────────────────

    private suspend fun attachLanguageServer(activeFile: SketchFile?, codeListing: String) {
        if (activeFile == null) return
        observeStatus(languageServerClient)
        val status = languageServerClient.start(sessionId = "mobile-session", rootUri = project.basePath.toURI().toString())
        if (status is LanguageServerStatus.Error) {
            showLspError(status)
            return
        }
        languageServerClient.openDocument(activeFileUri, "cpp", codeListing)
        observeDiagnostics(languageServerClient)
    }

    private fun observeStatus(client: LanguageServerClient) {
        statusJob?.cancel()
        statusJob = lifecycleScope.launch {
            client.status.collect { status ->
                when (status) {
                    is LanguageServerStatus.Ready -> {
                        updateStatusBar()
                    }
                    is LanguageServerStatus.Error -> {
                        Snackbar.make(binding.root, status.message, Snackbar.LENGTH_LONG).show()
                    }
                    LanguageServerStatus.Idle -> { /* no-op */ }
                }
            }
        }
    }

    private fun observeDiagnostics(client: LanguageServerClient) {
        diagnosticJob?.cancel()
        diagnosticJob = lifecycleScope.launch {
            client.diagnostics.collect { diagnostic ->
                // Show diagnostics in the output panel
                binding.outputLog.append("\n${diagnostic.message}")
            }
        }
    }

    private fun showLspError(status: LanguageServerStatus.Error) {
        val message = status.recoveryHint ?: getString(R.string.status_connected)
        Snackbar.make(binding.root, message, Snackbar.LENGTH_LONG).show()
    }

    private fun maybeShowHelp(file: SketchFile, line: Int) {
        val function = DocumentSymbolHelper.contextForCursor(file.content, line)
        val lineText = file.content.lines().getOrNull(line - 1)
        val character = lineText?.indexOfFirst { !it.isWhitespace() }?.coerceAtLeast(0) ?: 0
        lifecycleScope.launch {
            val hover = if (::languageServerClient.isInitialized) {
                languageServerClient.requestHover(activeFileUri, line, character)
            } else null
            if (hover != null) {
                MaterialAlertDialogBuilder(this@MainActivity)
                    .setTitle(getString(R.string.help_dialog_title))
                    .setMessage(hover.contents)
                    .setPositiveButton(android.R.string.ok, null)
                    .show()
            } else {
                val symbol = docs.keys.firstOrNull { file.content.contains(it) && function?.contains(it) == true }
                val description = symbol?.let { docs[it] }
                if (description != null) {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle(getString(R.string.help_dialog_title))
                        .setMessage(description)
                        .setPositiveButton(android.R.string.ok, null)
                        .show()
                }
            }
        }
    }

    // ── Lifecycle ──────────────────────────────────────────────

    override fun onPause() {
        super.onPause()
        tabStateRepository.saveOpenTabs(adapter.openFiles().map { it.path })
    }

    override fun onDestroy() {
        super.onDestroy()
        buildService.cleanup()
    }

    // ── Snippet Panel ──────────────────────────────────────────

    private fun configureSnippetPanel() {
        val sheetBehavior = BottomSheetBehavior.from(binding.snippetBottomSheet)
        sheetBehavior.peekHeight = 0
        sheetBehavior.state = BottomSheetBehavior.STATE_HIDDEN

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

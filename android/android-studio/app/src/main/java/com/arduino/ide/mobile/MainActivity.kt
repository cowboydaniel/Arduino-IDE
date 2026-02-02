package com.arduino.ide.mobile

import android.content.Intent
import android.hardware.usb.UsbManager
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
        val activeFile = project.files.firstOrNull()
        activeFileUri = activeFile?.path?.let { java.io.File(it).toURI().toString() }
            ?: "file://${project.basePath.absolutePath}/Sketch.ino"
        val codeListing = activeFile?.content.orEmpty()

        setupTabs(project)
        setupSearchControls()
        languageServerClient = LanguageServerClient(
            RuntimeLanguageServerTransport(ClangdRuntimeBridge(this))
        )
        lifecycleScope.launch {
            attachLanguageServer(activeFile, codeListing)
        }

        binding.serialMonitorLog.text = getString(R.string.build_ready_message)

        buildService = ArduinoBuildService(this)
        setupBuildButtons()
        setupBoardAndPortSelection()
        observeBuildState()
        observeUsbDevices()

        configureSnippetPanel()

        // Handle USB device if app was launched by USB attachment
        handleUsbIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { handleUsbIntent(it) }
    }

    private fun handleUsbIntent(intent: Intent) {
        if (intent.action == UsbManager.ACTION_USB_DEVICE_ATTACHED) {
            // Refresh device list when a USB device is attached
            buildService.usbManager.refreshDevices()
            Snackbar.make(binding.root, R.string.usb_device_attached, Snackbar.LENGTH_SHORT).show()
        }
    }

    private fun setupBoardAndPortSelection() {
        // Board selection chip
        binding.boardChip.text = currentBoard.name
        binding.boardChip.setOnClickListener {
            showBoardSelectionDialog()
        }

        // Port selection chip - shows connected devices
        binding.portChip.setOnClickListener {
            showPortSelectionDialog()
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
                binding.boardChip.text = currentBoard.name
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

                // Request permission if needed
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
        binding.portChip.text = device.productName
        binding.statusText.text = getString(R.string.device_selected, device.displayName)
    }

    private fun observeUsbDevices() {
        // Observe connected devices
        lifecycleScope.launch {
            buildService.usbManager.connectedDevices.collect { devices ->
                updatePortChip(devices)
            }
        }

        // Observe connection state
        lifecycleScope.launch {
            buildService.usbManager.connectionState.collect { state ->
                when (state) {
                    is ConnectionState.Connected -> {
                        binding.statusIndicator.setBackgroundResource(R.drawable.status_indicator_connected)
                        binding.statusText.text = getString(R.string.connected_to_device, state.device.displayName)
                    }
                    is ConnectionState.Disconnected -> {
                        binding.statusIndicator.setBackgroundResource(R.drawable.status_indicator)
                        if (selectedDevice == null) {
                            binding.statusText.text = getString(R.string.no_device_selected)
                        }
                    }
                    is ConnectionState.Error -> {
                        binding.statusIndicator.setBackgroundResource(R.drawable.status_indicator_error)
                        binding.statusText.text = state.message
                    }
                }
            }
        }
    }

    private fun updatePortChip(devices: List<ArduinoDevice>) {
        when {
            devices.isEmpty() -> {
                binding.portChip.text = getString(R.string.no_device)
                selectedDevice = null
            }
            selectedDevice == null && devices.isNotEmpty() -> {
                // Auto-select first device
                val firstDevice = devices.first()
                if (buildService.usbManager.hasPermission(firstDevice)) {
                    selectDevice(firstDevice)
                } else {
                    binding.portChip.text = getString(R.string.tap_to_connect)
                }
            }
            selectedDevice != null && !devices.contains(selectedDevice) -> {
                // Selected device was disconnected
                binding.portChip.text = getString(R.string.device_disconnected)
                selectedDevice = null
                Snackbar.make(binding.root, R.string.device_disconnected_message, Snackbar.LENGTH_SHORT).show()
            }
        }
    }

    private fun setupBuildButtons() {
        binding.uploadButton.setOnClickListener {
            performUpload()
        }
        binding.verifyButton.setOnClickListener {
            performVerify()
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

        // Request permission if needed
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
                    BuildState.Idle -> {
                        binding.statusChip.text = getString(R.string.status_label)
                    }
                    BuildState.Compiling -> {
                        binding.statusChip.text = getString(R.string.status_compiling)
                    }
                    BuildState.Uploading -> {
                        binding.statusChip.text = getString(R.string.status_uploading)
                    }
                    BuildState.Failed -> {
                        binding.statusChip.text = getString(R.string.status_failed)
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
                    binding.serialMonitorLog.text = logText
                }
            }
        }
    }

    private fun setupTabs(project: SketchProject) {
        val restored = project.resolveTabOrder(tabStateRepository.loadOpenTabs())
        adapter = EditorTabAdapter(layoutInflater, restored.toMutableList())
        adapter.onCursorChange = { file, line ->
            updateBreadcrumb(file, line)
            maybeShowHelp(file, line)
        }
        adapter.loadState = { file -> tabStateRepository.loadEditorState(file.path) }
        adapter.onStateChange = { file, state -> tabStateRepository.saveEditorState(file.path, state) }
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
        refreshEditorInsights(activeFile)
    }

    private fun observeStatus(client: LanguageServerClient) {
        statusJob?.cancel()
        statusJob = lifecycleScope.launch {
            client.status.collect { status ->
                when (status) {
                    is LanguageServerStatus.Ready -> {
                        binding.statusText.text = getString(R.string.status_connected)
                        binding.statusChip.text = getString(R.string.status_label)
                    }
                    is LanguageServerStatus.Error -> {
                        binding.statusText.text = status.message
                        binding.diagnosticHint.text = status.recoveryHint ?: getString(R.string.status_label)
                        Snackbar.make(binding.root, status.message, Snackbar.LENGTH_LONG).show()
                    }
                    LanguageServerStatus.Idle -> {
                        binding.statusText.text = getString(R.string.status_label)
                    }
                }
            }
        }
    }

    private fun observeDiagnostics(client: LanguageServerClient) {
        diagnosticJob?.cancel()
        diagnosticJob = lifecycleScope.launch {
            client.diagnostics.collect { diagnostic ->
                binding.diagnosticMessage.text = diagnostic.message
                val hint = diagnostic.recoveryHint
                binding.diagnosticHint.text = hint ?: getString(R.string.status_connected)
            }
        }
    }

    private fun showLspError(status: LanguageServerStatus.Error) {
        val message = status.recoveryHint ?: getString(R.string.status_connected)
        Snackbar.make(binding.root, message, Snackbar.LENGTH_LONG).show()
        binding.hoverText.text = getString(R.string.status_label)
    }

    private suspend fun refreshEditorInsights(activeFile: SketchFile) {
        val line = activeFile.content.lines().size.coerceAtLeast(1)
        val character = activeFile.content.lines().lastOrNull()?.length?.coerceAtLeast(0) ?: 0
        val completions = languageServerClient.requestCompletions(
            uri = activeFileUri,
            line = line,
            character = character
        )
        binding.completionList.text = completions.joinToString("\n") { item ->
            buildString {
                append(item.label)
                item.detail?.let { append(" — ").append(it) }
                item.autoImportText?.let { append(" (auto-import: ").append(it).append(")") }
            }
        }

        val hover = languageServerClient.requestHover(
            uri = activeFileUri,
            line = line,
            character = character
        )
        binding.hoverText.text = hover?.contents ?: getString(R.string.status_connected)
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

    override fun onPause() {
        super.onPause()
        tabStateRepository.saveOpenTabs(adapter.openFiles().map { it.path })
    }

    override fun onDestroy() {
        super.onDestroy()
        buildService.cleanup()
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

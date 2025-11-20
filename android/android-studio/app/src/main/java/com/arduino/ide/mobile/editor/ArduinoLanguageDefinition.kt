package com.arduino.ide.mobile.editor

import android.content.Context
import android.os.Bundle
import io.github.rosemoe.sora.lang.Language
import io.github.rosemoe.sora.lang.analysis.AnalyzeManager
import io.github.rosemoe.sora.lang.completion.CompletionPublisher
import io.github.rosemoe.sora.lang.format.Formatter
import io.github.rosemoe.sora.lang.smartEnter.NewlineHandleResult
import io.github.rosemoe.sora.lang.smartEnter.NewlineHandler
import io.github.rosemoe.sora.lang.styling.Styles
import io.github.rosemoe.sora.langs.textmate.TextMateLanguage
import io.github.rosemoe.sora.langs.textmate.registry.FileProviderRegistry
import io.github.rosemoe.sora.langs.textmate.registry.GrammarRegistry
import io.github.rosemoe.sora.langs.textmate.registry.ThemeRegistry
import io.github.rosemoe.sora.langs.textmate.registry.model.DefaultGrammarDefinition
import io.github.rosemoe.sora.langs.textmate.registry.model.ThemeModel
import io.github.rosemoe.sora.langs.textmate.registry.provider.AssetsFileResolver
import io.github.rosemoe.sora.text.CharPosition
import io.github.rosemoe.sora.text.Content
import io.github.rosemoe.sora.text.ContentReference
import io.github.rosemoe.sora.widget.SymbolPairMatch
import org.eclipse.tm4e.core.registry.IGrammarSource
import org.eclipse.tm4e.core.registry.IThemeSource
import java.nio.charset.StandardCharsets

object ArduinoLanguageDefinition {

    private const val GRAMMAR_PATH = "textmate/arduino.tmLanguage.json"
    private const val LANGUAGE_CONFIGURATION_PATH = "textmate/arduino-language-configuration.json"
    private const val THEME_PATH = "textmate/arduino.theme.json"
    private const val SCOPE_NAME = "source.arduino"

    fun create(context: Context): Language {
        val assets = context.assets
        val fileResolver = AssetsFileResolver(assets)
        FileProviderRegistry.getInstance().addFileProvider(fileResolver)

        val grammarSource = IGrammarSource.fromInputStream(
            assets.open(GRAMMAR_PATH),
            GRAMMAR_PATH,
            StandardCharsets.UTF_8
        )
        val definition = DefaultGrammarDefinition.withLanguageConfiguration(
            grammarSource,
            LANGUAGE_CONFIGURATION_PATH,
            SCOPE_NAME,
            "Arduino"
        )

        val grammarRegistry = GrammarRegistry.getInstance()
        grammarRegistry.loadGrammars(listOf(definition))

        val themeModel = ThemeModel(
            IThemeSource.fromInputStream(
                assets.open(THEME_PATH),
                THEME_PATH,
                StandardCharsets.UTF_8
            ),
            "Arduino Dark"
        ).apply { isDark = true }

        val themeRegistry = ThemeRegistry.getInstance()
        themeRegistry.loadTheme(themeModel, true)
        themeRegistry.setTheme(themeModel.name)

        val textMateLanguage = TextMateLanguage.create(
            definition,
            grammarRegistry,
            themeRegistry,
            true
        )

        return ArduinoLanguage(textMateLanguage)
    }

    private class ArduinoLanguage(
        private val delegate: TextMateLanguage
    ) : Language {
        override fun getAnalyzeManager(): AnalyzeManager = delegate.analyzeManager

        override fun getInterruptionLevel(): Int = delegate.interruptionLevel

        override fun requireAutoComplete(
            content: ContentReference,
            position: CharPosition,
            publisher: CompletionPublisher,
            extra: Bundle
        ) {
            delegate.requireAutoComplete(content, position, publisher, extra)
        }

        override fun getIndentAdvance(
            content: ContentReference,
            line: Int,
            column: Int
        ): Int {
            val base = delegate.getIndentAdvance(content, line, column)
            if (line <= 0) return base
            val previousLine = content.getLine(line - 1).trim()
            val opensArduinoBlock = previousLine.contains("setup(") || previousLine.contains("loop(")
            val opensControlBlock = previousLine.endsWith("{")
            val closesBlock = previousLine.startsWith("}")
            return when {
                opensArduinoBlock || opensControlBlock -> base + delegate.tabSize
                closesBlock -> (base - delegate.tabSize).coerceAtLeast(0)
                else -> base
            }
        }

        override fun useTab(): Boolean = delegate.useTab()

        override fun getFormatter(): Formatter = delegate.formatter

        override fun getSymbolPairs(): SymbolPairMatch = delegate.symbolPairs

        override fun getNewlineHandlers(): Array<NewlineHandler> =
            arrayOf(ArduinoNewlineHandler(delegate))

        override fun destroy() {
            delegate.destroy()
        }
    }

    private class ArduinoNewlineHandler(
        private val delegate: TextMateLanguage
    ) : NewlineHandler {
        override fun matchesRequirement(
            content: Content,
            cursor: CharPosition,
            styles: Styles?
        ): Boolean = true

        override fun handleNewline(
            content: Content,
            cursor: CharPosition,
            styles: Styles?,
            tabLength: Int
        ): NewlineHandleResult {
            val delegateResult = delegate.newlineHandler.handleNewline(content, cursor, styles, tabLength)
            val currentLine = content.getLine(cursor.line).trimEnd()
            val prefersExtraIndent = currentLine.endsWith("{") || currentLine.contains("setup(") || currentLine.contains("loop(")
            val additionalIndent = if (prefersExtraIndent) " ".repeat(tabLength) else ""
            return NewlineHandleResult("\n" + delegateResult.text + additionalIndent, delegateResult.shiftLeft)
        }
    }
}

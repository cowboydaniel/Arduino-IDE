package com.arduino.ide.mobile.snippets

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.arduino.ide.mobile.MainActivity
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SnippetSheetTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun searchFiltersSnippetsAndShowsCategories() {
        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onNodeWithTag("snippetList").fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithTag("category_Serial").performClick()
        composeRule.onNodeWithTag("snippet_serial-print").assertIsDisplayed()

        composeRule.onNodeWithTag("snippetSearchField").performTextInput("analog")
        composeRule.onNodeWithTag("snippet_analog-read").assertIsDisplayed()
    }

    @Test
    fun placeholderNavigationAdvancesThroughTabStops() {
        composeRule.waitUntil(timeoutMillis = 5_000) {
            composeRule.onNodeWithTag("snippet_digital-write").fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithTag("snippet_digital-write").performClick()
        composeRule.onNodeWithTag("placeholderIndicator").assertTextContains("pin")

        composeRule.onNodeWithTag("nextPlaceholderButton").performClick()
        composeRule.onNodeWithTag("placeholderIndicator").assertTextContains("state")

        composeRule.onNodeWithTag("nextPlaceholderButton").performClick()
        composeRule.onNodeWithTag("placeholderIndicator").assertTextContains("Cursor")
    }
}

# File Workflow Manual Tests

These manual test cases verify the basic file lifecycle for the editor, including the
unsaved-changes prompt and the file dialogs used for opening and saving sketches.

## Prerequisites
- Start the Arduino IDE Modern application.
- Ensure you can access a directory with at least one `.ino` file for testing.

## Test Cases

### 1. Prompt on Unsaved Changes
1. Choose **File → New** to create a new sketch tab.
2. Type any text to ensure the document is dirty.
3. Close the tab via the close button or **File → Close Tab** (if available).
4. **Expected:** A dialog appears warning about unsaved changes with **Save**, **Discard**, and **Cancel** options.
5. Select **Cancel** and verify the tab remains open.
6. Repeat steps 1–4 and select **Discard**. The tab should close without saving.

### 2. Save Workflow
1. Create a new sketch or use the tab from the previous test.
2. Choose **File → Save** (or press `Ctrl+S`).
3. **Expected:** A **Save Sketch As** dialog appears when the sketch has never been saved.
4. Select a destination and confirm the save.
5. **Expected:**
   - The tab title loses the asterisk.
   - The status bar briefly shows “Saved <filename>”.
   - No dirty prompt appears if you immediately close the tab.

### 3. Save As Workflow
1. With a saved sketch open, choose **File → Save As…**.
2. Pick a new filename and confirm.
3. **Expected:**
   - A new file is written to disk with the chosen name.
   - The tab title reflects the new filename without an asterisk.
   - Closing the tab does not prompt for unsaved changes.

### 4. Open Workflow
1. Choose **File → Open…**.
2. Select an existing sketch file (e.g., `Blink.ino`).
3. **Expected:**
   - The file opens in a new tab displaying its contents.
   - The tab title matches the opened filename and has no asterisk.
   - The status bar briefly reports “Opened <filename>”.
4. Re-open the same file from **File → Open…**.
5. **Expected:** The IDE switches to the existing tab instead of opening a duplicate.

### 5. Recent Files Persistence
1. Complete the open and save workflows for at least two different files.
2. Close and restart the application.
3. **Expected:** The recently used files appear in the persisted settings (visible via developer tools or logs if a UI list is not yet exposed).

Document any deviations from the expected outcomes.

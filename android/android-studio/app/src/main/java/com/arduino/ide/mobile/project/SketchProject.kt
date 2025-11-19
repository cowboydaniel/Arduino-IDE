package com.arduino.ide.mobile.project

import android.content.Context
import java.io.File

/**
 * Lightweight project model that knows how to discover sketch files and keep
 * track of the currently opened tabs.
 */
class SketchProject(
    val name: String,
    val basePath: File,
    val files: List<SketchFile>
) {

    fun resolveTabOrder(preferredPaths: List<String>): List<SketchFile> {
        if (preferredPaths.isEmpty()) return files
        val pathLookup = files.associateBy { it.path }
        val restored = preferredPaths.mapNotNull { pathLookup[it] }
        val missing = files.filterNot { preferredPaths.contains(it.path) }
        return restored + missing
    }

    companion object {
        /**
        * Loads all .ino and .cpp files found under the provided directory. The loader
        * tolerates missing directories by returning an empty project to keep previews alive.
        */
        fun loadFromDirectory(context: Context, basePath: File, name: String = basePath.name): SketchProject {
            if (!basePath.exists()) {
                return SketchProject(name, basePath, emptyList())
            }

            val discovered = basePath
                .walkTopDown()
                .filter { it.isFile && (it.extension.equals("ino", true) || it.extension.equals("cpp", true)) }
                .map { file ->
                    val content = runCatching { file.readText() }.getOrDefault("")
                    SketchFile(
                        name = file.name,
                        path = file.absolutePath,
                        content = content
                    )
                }
                .toList()

            return SketchProject(name, basePath, discovered)
        }

        fun demoProject(context: Context): SketchProject {
            val demoRoot = File(context.cacheDir, "demo-sketch")
            if (!demoRoot.exists()) {
                demoRoot.mkdirs()
            }

            val files = listOf(
                "Blink.ino" to """
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
                """.trimIndent(),
                "Utilities.cpp" to """
                    #include <Arduino.h>

                    int readSensor(int pin) {
                      return analogRead(pin);
                    }
                """.trimIndent(),
                "Diagnostics.cpp" to """
                    #include <Arduino.h>

                    void logStatus(const char* label) {
                      Serial.println(label);
                    }
                """.trimIndent()
            )

            val sketchFiles = files.map { (name, body) ->
                val file = File(demoRoot, name)
                file.writeText(body)
                SketchFile(name = name, path = file.absolutePath, content = body)
            }

            return SketchProject("Blink", demoRoot, sketchFiles)
        }
    }
}

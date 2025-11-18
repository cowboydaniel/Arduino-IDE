[app]
title = Arduino IDE Modern - Android
package.name = arduinoidemodern
package.domain = org.arduino.ide
source.dir = .
source.include_exts = py,kv,json,ini
version = 0.1.0
requirements = python3, PySide6
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 24
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,REQUEST_INSTALL_PACKAGES

[buildozer]
log_level = 2
warn_on_root = 0

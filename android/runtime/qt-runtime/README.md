# Bundled Qt runtime

This folder is populated with the Qt for Android runtime expected by
`org.qtproject.qt.android.bindings.QtActivity`. The binaries are organized by
ABI (for example `arm64-v8a` and `armeabi-v7a`) so Gradle can pick them up as
both assets and native libraries during the sync step.

The placeholder `.so` files mirror the names produced by Qt's Android
deployment tooling. Replace them with the official Qt for Android runtime
artifacts for your targeted Qt release when producing a build destined for end
users.

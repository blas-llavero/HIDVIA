# Android APK distribution

**No APK is supplied in this repository snapshot.** A compiled APK cannot be generated without an Android SDK/build environment.

After running `gradle assembleDebug` in the `android` directory, the expected installable file is:

`android/app/build/outputs/apk/debug/app-debug.apk`

The included GitHub Actions workflow builds the APK and attaches it as an artifact called `HIDVIA-demo-debug-apk`.

Only share the APK as a non-clinical research demo after trademark checks, security review and device testing.

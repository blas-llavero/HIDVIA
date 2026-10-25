# HIDVIA — HS monitoring and research AI

**HIDVIA** is a research prototype created by **Team 4 of the Healthtech Challenge 2030 at UPC (Gabriel R., Evelyn M., Fairuz, Mané and Blas L)** in collaboration with **Almirall, UPC and Xartec Salut**. Learn more at [blasllavero.com](https://blasllavero.com).

It combines an Android patient companion, a clinician web portal, diary entries and photographs, appointment/test notifications, exploratory flare modelling, optional personal calibration and a provisional RNA sensor integration. The software is open-source under the MIT licence (original code only), and charitable uses and modifications are welcome.

**Research and fictional data only.** Do not use for treatment decisions, store real patient records, or expose this prototype as a clinical service. No AI model has been externally validated using the supplied challenge files. Real RNA sensor interoperability is conditional on manufacturer hardware specifications.

## Android APK — expected installation location

After the full Android source is committed and built: `android/app/build/outputs/apk/debug/app-debug.apk`. An APK is **not yet built or hosted here**. Use Android Studio or the Android GitHub Actions workflow after uploading the full project source. Copy `app-debug.apk` to an Android phone, open it in Files, allow temporary installation from that source, then launch **HIDVIA (Demo)**. No calibration is required.

## Optional calibration

Open **Settings → Optional calibration**, set usual pain, swelling and fatigue, and save the personal reference. Without calibration the app starts using a transparent, *non-validated* illustrative signal. Calibrating does not establish medical accuracy.

## Web deployment

`render.yaml` is the planned **research demonstration only** Render Blueprint. The repository must first contain the complete `server/` and `web/` application directories. Then authorize a Render account to access the repo and create a Blueprint deployment. The two demo pages will be `/patient` and `/clinician`. Source publication alone does not provide a live URL.

## RNA sensor, via Android or clinician computer

The full research prototype implements `hidvia-rna-v1` JSON import on both interfaces, plus conditional BLE GATT and desktop Web Serial connectors. A manufacturer-specific driver requires actual service UUIDs and measurement protocol. Assay outputs are not used as validated predictors. See the complete source package's `docs/RNA_SENSOR.md`.

## Almirall validation and licensing

The earlier project attachments (challenge DOCX, public archives, HS datasets) are **not available in this GitHub repository**. Keep these files private until rights and consent have been verified. A dataset audit and training/evaluation scripts are provided in the separate complete source package; prospective prediction needs patient-linked dates and clinically adjudicated future flare outcomes. Cross-sectional RNA/image samples alone cannot establish 7-day forecast accuracy.

## Upload the complete source

This GitHub repository was initially empty. A complete updated source archive is provided to the project team through the project conversation. To replace this starter documentation with the whole runnable application:

```bash
git clone https://github.com/blas-llavero/HIDVIA.git
cd HIDVIA
# Extract the HIDVIA source ZIP here so that server/, web/, android/, ml/, docs/ and render.yaml are at repository root
git add .
git commit -m "Add HIDVIA research prototype: Android, clinician web, RNA and ML audit"
git push origin main
```

Never commit identifiable patients, restricted Almirall datasets, passwords or build secrets. The README in the complete source package has full install, usage, APK build, sensor and validation instructions.

## Build from source (Android) — after source upload

Open `android/` as an Android Studio project (JDK 17 and Android SDK). Run Gradle `assembleDebug`, or use **Actions → Build HIDVIA Android demo APK** and download `HIDVIA-demo-debug-apk`. The current repository starter alone is not enough to build the application.

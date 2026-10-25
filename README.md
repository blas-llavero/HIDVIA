# HIDVIA — HS Care Companion

**HIDVIA** is a six-letter **provisional** project name for an open-source research prototype intended to connect people living with hidradenitis suppurativa (HS) with clinicians. It comprises an Android patient application and a web-based clinician dashboard. Patients can record daily symptoms, attach emerging-flare images, optionally share available phone sensor snapshots, view visit and test updates, and follow changes over time. Clinicians can review fictional demonstration histories, receive signal alerts, create appointment notifications, publish test-result updates, and record visit notes. The software includes an exploratory seven-day flare-onset ML pipeline, but **does not come with a clinically trained or validated prediction model**; without one, a transparent illustrative symptom indicator works immediately and does not require calibration.

**Project attribution:** The program was conceived and developed by **Team 4 of the Healthtech Challenge 2030 at UPC (Gabriel R., Evelyn M., Fairuz, Mané, and Blas L)**, in collaboration with **Almirall, UPC, and Xartec Salut**. For further information visit **[blasllavero.com](https://blasllavero.com)**. The software is **open-source under the MIT License** (subject to contributors' rights/authorization) and may be modified and used by anyone, including for charitable and non-profit purposes. This grant applies to original code; no rights to third-party clinical datasets, partner trademarks, or external services are implied.

## Almirall 2026 challenge — six-month IHS4 regression

The uploaded challenge files define **a different target from the app's seven-day flare demonstration**: the underlying mean IHS4 between January 1 and June 30, 2026. The `ml/hs_rwe_pipeline.py` pipeline reads the actual challenge CSVs (not committed to GitHub), trains a tabular LightGBM model and cross-fitted image/RNA residual adjustments, produces four complete Team 4 submission files, and performs an **internal** patient-disjoint validation only.

**Measured internal holdout MAE: 1.457 on 4,200 training patients** (Hurley baseline 2.582; last recorded IHS4 2.693). Image augmentation gives little benefit on the small validation subset; RNA+image has exploratory additional signal, with no unbiased test confirmation. The test_1 and test_2 labels are private, therefore their MAE remains unknown. The optional super-responder probability is omitted because actual counterfactual treatment response labels are not supplied. Source archives are labelled INTERNAL USE and are deliberately excluded from public GitHub.

See [`ml/HS_RWE_README.md`](ml/HS_RWE_README.md) for commands, [`ml/hs_rwe_pipeline.py`](ml/hs_rwe_pipeline.py) for the full implementation and the generated `VALIDATION_REPORT.md` inside the **private results ZIP**. The six-month competition model is not a smartphone flare prediction or a validated clinical score.

## Android APK — installation location

**Expected APK location after building:** `android/app/build/outputs/apk/debug/app-debug.apk`

**Continuous-integration download:** In GitHub, open **Actions → Build HIDVIA Android demo APK → latest successful run → Artifacts → HIDVIA-demo-debug-apk**. Extract `app-debug.apk` from the downloaded artifact.

**Current deliverable:** Android source and a build workflow are provided, **but no compiled APK is included**. The supplied environment did not have an Android SDK and could not download it. Do not assume an APK exists until you build or download the workflow artifact. A signed release APK is **not** provided.

> **Important:** Research/hackathon demonstrator only. **DO NOT use with real patient records or for clinical decisions.** The illustrative score is not a probability, medical diagnosis, or validated prediction. A trained research model is not a cleared medical device. Seek professional medical help based on symptoms and usual care instructions, regardless of this app's output.

## Install an APK on an Android phone

1. Build the debug APK in Android Studio or download the APK artifact from the included GitHub Actions workflow (details at the end of this README).
2. Transfer `app-debug.apk` to the phone (USB, a file transfer app, or a secure internal test distribution service).
3. On the phone, open **Files → Downloads** (or the transfer destination) and tap `app-debug.apk`.
4. If Android asks, allow **Install unknown apps** *temporarily for that file-management app*, confirm the installation, and turn the allowance off afterwards. Do not distribute test APKs as clinical software.
5. Launch **HIDVIA (Demo)**. Android **8.0 (API 26) or newer** is supported by the project configuration. Use **Home**, **Daily check-in**, **Timeline**, and **Settings**. The first launch opens the offline patient interface, even without any clinic server.
6. Grant Android notification or optional activity/heart-rate sensor permissions only if you want those demo features. Devices lacking a given sensor still work normally. Photos can be selected from the image picker; supported camera apps can be offered by the native picker.

### Run and use the Android application

- **Offline, no calibration:** Launch the APK; select **Daily check-in**; enter fictional symptom scores (pain, itching, swelling/tenderness, fatigue and stress from 0–10), hours slept, anatomical area, optional drainage, and early warning notes; tap **Save check-in**. The default demo symptom indicator is immediately available without calibration. **Offline records are stored unencrypted in the app's WebView local storage; never enter real patient data.** Photos selected in offline mode are only previewed, not persisted as images.
- **Online clinician demo:** Start the clinic server following the next section. Open **Settings → Clinic connection** on the phone. Enter the test server origin, e.g. `http://10.0.2.2:8765` on the Android emulator, or the private LAN address `http://192.168.1.20:8765` on a physical test phone. Tap **Save server address**. The native shell will open `/patient` from that test server. Sign in using the patient demo account, then submit fictional records; symptom alerts will appear in the clinician dashboard. An online image is uploaded only when the patient submits the form.
- **Appointment/test updates:** While connected, a clinician can publish a demo appointment or result. The patient sees it on the next refresh (automatically while the app is open, approximately every 30 seconds, or on reload). Android local notification display is attempted if runtime permission was granted. **This is polling while the app is open, not Firebase Cloud Messaging / guaranteed background push.**
- **Wearables:** A compatible Fitbit Charge 6 or Garmin watch may relay allowed *phone* app notifications depending on pairing and companion-app settings. **No direct Fitbit/Garmin integration or guaranteed watch delivery is implemented.** Optional API integration is a future milestone.
- **Bottom navigation:** Android `WindowInsets` are applied for status/navigation bars, including Android 15 edge-to-edge behaviour; the web interface also reserves safe-area space for the bottom tab bar. Test on both gesture navigation and three-button navigation before release.

### Perform optional calibration inside HIDVIA

Calibration is **never required**. To choose a personal reference:

1. Open **HIDVIA → Settings → Optional calibration**.
2. Prefer a day when symptoms are stable, without an emerging flare. Adjust the three 0–10 sliders for **typical pain**, **typical swelling**, and **typical fatigue**.
3. Tap **Save personal reference**. The badge changes from *Default mode — no calibration needed* to *Personal reference enabled*.
4. Continue daily check-ins normally. The offline/default illustrative score can take differences from that reference into account. If connected, the baseline is saved to the demonstration clinic server for that patient.
5. You can re-enter typical values and save again to update the reference. No calibration accuracy or clinical gain has been established; a trained model may use its own explicit feature definition rather than these reference values.

## Run the demonstration without an APK

Requires **Python 3.10 or newer**, with no third-party packages for the server or the web application.

```bash
cd hidvia
python3 server/app.py
```

Open:

- **Patient web app:** http://127.0.0.1:8765/patient
- **Clinician platform:** http://127.0.0.1:8765/clinician
- **Health endpoint:** http://127.0.0.1:8765/api/health

**Fictional demo accounts:**

| Role | Username | Password |
|---|---|---|
| Patient | `patient@hidvia.test` | `demo-pass-123` |
| Clinician | `clinician@hidvia.test` | `demo-pass-123` |

These credentials are deliberately public demonstration credentials. Optionally set `HIDVIA_DEMO_PASSWORD` before creating a fresh demonstration database to use a different password. The server auto-generates **fictional** records, a fictional appointment, and a fictional visit note. The database is written to `demo_data/hidvia.sqlite3` on first run and is excluded from version control. For a fresh demo, stop the server and delete that file (deletes all demo records).

For a physical Android test phone on the same trusted Wi-Fi network:

```bash
# For fictional data on a closed local network ONLY; never expose to the internet.
HIDVIA_HOST=0.0.0.0 HIDVIA_PORT=8765 python3 server/app.py
```

Find the development computer's private LAN IPv4 address, use the address from the phone's **Settings → Clinic connection**, and allow port 8765 through the test computer's local firewall if needed. Plain HTTP and demonstration credentials are **unsafe for real health data**. For production, move to an audited HTTPS backend with an appropriate identity system.

## Features and what is genuinely implemented

| Feature | State | Remarks |
|---|---|---|
| Android native WebView project | Source implemented; APK not compiled here | Offline-first UI, photo chooser, native notifications, device signal bridge |
| Clinician portal | Working local demo | Patient records, illustrative alerts, acknowledgment, visits, appointments, results |
| HS daily diary | Working | Pain, itching, swelling, fatigue, stress, sleep, drainage, location text, notes |
| Symptom photo capture/upload | Working in online demo, subject to device picker | Up to 4 MB JPEG/PNG/WebP; authenticated viewing in clinician portal |
| Patient–clinician data transfer | Working in local demo | HTTP REST + SQLite and bearer-token demo authentication |
| Patient notifications | In-app polling; Android local display attempted | **No background FCM delivery** |
| Optional calibration | Working | User-entered pain/swelling/fatigue reference; not needed by default |
| Device sensors | On demand | Accelerometer, gyroscope, light, barometric pressure, proximity; step count and heart rate only where hardware and permissions permit. No data is collected remotely unless a patient opts in during a check-in. |
| Predictive AI | Training + optional inference implemented | Requires suitable de-identified HS longitudinal data and explicit model configuration. No clinical validation. |
| Fitbit/Garmin sensor ingest | Not implemented | OAuth, device integration or Health Connect work required |
| High-assurance clinic security / GDPR readiness | Not implemented | **Do not process real patient information** |
| Multilingual UI | 10 core translation dictionaries | All 83 common keys translated; dynamic medical notes remain in their entered language. Translation review required. |

## Languages

English (`en`), Catalan (`ca`), Spanish (`es`), French (`fr`), German (`de`), Italian (`it`), Portuguese (`pt`), Arabic (`ar`, right-to-left), Simplified Chinese (`zh`), and Hindi (`hi`). Change language from **Settings → Language** in the patient app, or from the top-right selector in the clinician portal. English is the fallback for future new terms. Clinician-authored notes are not machine-translated.

## Flare-onset modelling

Default scoring is a **non-validated symptom composite**, deliberately shown as an *illustrative signal*. The score uses symptom magnitudes, relative changes over recent check-ins, sleep, and optional personal reference measurements. Do **not** interpret `65/100` as a 65% probability or as a medical emergency threshold. The example clinician alert uses a demonstration threshold and must not be used for triage.

With explicit `HIDVIA_MODEL_PATH` configuration, the backend can use a trained seven-day exploratory logistic-regression model instead of the illustrative composite. See **[ML pipeline documentation](ml/README.md)** for the de-identified CSV schema, outcome-label construction, patient-grouped train/test evaluation, and training command. The original challenge datasets were not part of this generated code package; we therefore do not claim model accuracy or ship fabricated model weights.

## Data protection and clinical regulatory notes

- **Never use real PHI/health data in this prototype.** Passwords are public, there is no TLS on the local demo, no comprehensive role assignments, no clinical audit trail, no data-at-rest encryption, no robust consent/withdrawal flow, and no medical incident process.
- To deploy a medical prediction product in the EU, obtain a documented regulatory assessment for software under **EU MDR / MDCG 2019-11**, assess applicable EU AI Act requirements, conduct a GDPR data protection impact assessment, and establish appropriate lawful basis, consent/other processing conditions, retention and deletion controls, security and human oversight.
- Needed production changes include clinic SSO with MFA and access controls, role-specific patient assignments, verified notification delivery, encrypted storage and backups, TLS, secure media capture and handling, threat modelling, vulnerability testing, audit trails, signed releases, clinical external validation, a prospective study plan, and potentially CE conformity assessment.
- Smartphone sensor signals are *not* automatically biomarkers for HS. Activity/sleep/stress associations must be empirically justified and measured before inclusion in any prediction model. Collect the minimum necessary; do not indiscriminately capture microphones, location or biometric information.

Additional detail: [System architecture](docs/ARCHITECTURE.md), [Brand clearance](docs/NAME_CLEARANCE.md), [Clinical validation](docs/VALIDATION.md), and [Roadmap](docs/ROADMAP.md).

## Test the source

```bash
python3 -m unittest discover -s tests -v
node --check web/patient.js
node --check web/clinician.js
node --check web/i18n.js
```

The tested demonstration workflow covers separate patient/clinician sign-in, default operation without calibration, symptom submissions, alerts, clinician visit/appointment/test-result entries, and permission restrictions. **Real-device installation, visual QA and APK compilation must still be performed.**

## Repository structure

```text
hidvia/
├── README.md
├── LICENSE
├── server/app.py                     # Python/SQLite REST demo API
├── web/                              # Patient PWA + clinician browser portal
│   ├── patient.html / patient.js
│   ├── clinician.html / clinician.js
│   ├── i18n.js / styles.css
│   └── sw.js / manifest.webmanifest
├── android/                          # Native Android Java + WebView source
│   └── app/src/main/{java,assets}/
├── ml/train_model.py                 # 7-day research ML pipeline
├── tests/test_server.py              # Local end-to-end API tests
├── docs/                              # Verification, architecture, clinical plan
├── releases/README.md               # APK output location, no fabricated binary
└── .github/workflows/android-debug-apk.yml
```

## GitHub repository and online service (next research iteration)

Primary repository: **https://github.com/blas-llavero/HIDVIA**. The full project (including `server`, `web`, `ml`, `android`, `docs`, `tests` and workflow files) must be committed, excluding partner datasets, patient records and any credentials. Read **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the Render Blueprint `render.yaml`, demonstration-only HTTPS service, and deployment restrictions. The repository alone does not make the API live.

## RNA sensor / molecular data interface

The patient and clinician apps now accept simulated `hidvia-rna-v1` JSON imports; both submit to role-protected `/api/rna`. The desktop portal can attempt Web Bluetooth and Web Serial when browser/device APIs exist, and the Android app has a file importer. An Android generic GATT adapter and desktop BLE/serial adapters are included, but genuine device compatibility remains conditional on vendor UUIDs, firmware and frame encoding. Molecular values are stored separately and **never treated as proven flare predictors**. See **[docs/RNA_SENSOR.md](docs/RNA_SENSOR.md)** and `web/rna-example.json`.

## Inspect Almirall challenge files and validate the model

The earlier uploaded challenge ZIP and Word/PDF documents were **not mounted in the current build environment**. No training or validation on Almirall's actual files has been performed. Do not commit restricted clinical, image or RNA datasets to the public repository.

```bash
python3 -m pip install -r ml/requirements.txt
python3 ml/audit_challenge_data.py /private/path/to/challenge_files --output ml/challenge_schema_report.json
# Only IF the dataset genuinely contains clinically verified future flare onsets and complete patient follow-up:
python3 ml/train_model.py /private/deidentified_longitudinal_train.csv --output ml/research_model.json
python3 ml/validate_model.py /private/independent_labelled_cohort.csv ml/research_model.json --output ml/validation_report.json
```

Audit reports identify columns and modality coverage, not outcomes or model quality; private filenames may be sensitive. `ml/validate_model.py` computes AUROC, average precision, Brier score and threshold-based sensitivity/specificity but **cannot certify an independent external cohort by itself**. A cross-sectional RNA/clinical/image dataset cannot validate prospective seven-day flare prediction in the absence of follow-up outcomes. The uncalibrated app continues functioning in non-clinical illustrative mode.

## Build from source (Android) — final section

This section is intentionally placed **after** the download, installation, use, calibration, and testing instructions.

1. Install **Android Studio** with **Android SDK Platform 35**, Android SDK Build Tools, and **JDK 17**. Open the `android/` directory as an Android Studio project and let it sync. You also need internet access for the Gradle Android plugin's dependencies.
2. Synchronize the offline patient assets with the current web frontend:

   ```bash
   cp web/{patient.html,patient.js,i18n.js,styles.css,icon.svg,manifest.webmanifest} android/app/src/main/assets/
   ```

3. In Android Studio select **Build → Build App Bundle(s) / APK(s) → Build APK(s)**, or, when Gradle 8.9 is installed, run:

   ```bash
   cd android
   gradle assembleDebug
   ```

4. Find the **debug APK** at **`android/app/build/outputs/apk/debug/app-debug.apk`**. Install it on the emulator/device with:

   ```bash
   adb install -r android/app/build/outputs/apk/debug/app-debug.apk
   ```

   (Run that command from the repository root; when inside `android/`, use `adb install -r app/build/outputs/apk/debug/app-debug.apk`.)

5. **Alternative automated build:** push the entire repository, including `.github/workflows/android-debug-apk.yml`, into a repository under your control. Run **Actions → Build HIDVIA Android demo APK → Run workflow**. If successful, download the build artifact and extract the APK.
6. Test on Android 8–16 where available, including Android 15+ **gesture and three-button navigation**, compact screens, camera picker, offline startup, Android permission handling, app resume, network loss, clinic portal notifications and right-to-left layouts. Run the workflow and inspect logs if Gradle needs adjustments. No device tests or actual APK build were performed here.
7. Do not issue a release-signed APK or publish in an app store until name clearance, clinical scope, privacy and security controls, device QA and applicable regulatory requirements have been satisfied.

**License:** [MIT](LICENSE) — see attribution and partner IP limitations above.

## Launch the fictional-data web demo in your browser

**[Deploy HIDVIA Web to Render](https://render.com/deploy?repo=https://github.com/blas-llavero/HIDVIA)**. Authorize Render to access this public GitHub repository, review the free-tier/pricing choices, and enter a private `HIDVIA_DEMO_PASSWORD` when prompted. After the Blueprint deploy reports Live, open the Render-assigned HTTPS URL ending in `/patient` (patient demo) or `/clinician` (clinician demo). Use `patient@hidvia.test` or `clinician@hidvia.test` and the demo password you set. Do not use actual patient data. This deployment is ephemeral and may lose its test data after restart. The competition's six-month IHS4 model is NOT part of these interactive symptom demo scores.

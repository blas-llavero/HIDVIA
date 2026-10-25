# Deployment roadmap and implementation boundaries

## Present (0.2 demonstration)

- Functional local Python/SQLite server and clinician browser panel.
- Offline patient mobile-responsive HTML; Android wrapper source with camera/image chooser, optional sensors, local notifications, Android safe-area handling.
- Symptom check-ins, consented optional sensor snapshot, photo upload (online only), transparent default composite, optional user-specified baseline, alerts, visits, appointments and test updates.
- Ten localisable dictionaries, test cases, GitHub Actions APK build workflow.

## Phase 1 — Device and platform reliability

- Compile with Android Studio / CI; device test Android 8–16, especially Android 15/16 navigation insets.
- Remove fragile WebView local data for anything sensitive; encrypted/offline queues with explicit patient-controlled sync/delete, reliable background retry, authenticated server and secure photo handling.
- Fix supported sensor availability/permissions; evaluate CameraX capture with no gallery side-effects, EXIF stripping, standardised photo capture and explicit camera consent.
- Define clinician alert SLAs, read receipts and robust background notifications using FCM, protected push content and optional watch-mirroring testing.

## Phase 2 — Clinical and data science integration

- Parse the actual Almirall/UPC challenge longitudinal HS datasets if rights, field dictionaries and files are available, and implement dataset adapters.
- Harmonise record timestamps, define incident flares and leakage-free patient/site/time splits, confidence intervals, calibration and external evaluation.
- Add calibrated probabilistic risk reporting **only after real evaluation**, with clear uncertainty and clinical oversight.
- Revisit which optional phone and wearable signals are clinically predictive, not just measurable.

## Phase 3 — Hospital and wearable ecosystem

- Audit-grade OIDC/SSO, RBAC, scoped clinicians/patients, server-side authorization, encryption, DPIA and safety management.
- FHIR patient and appointment/results integration with hospitals; appointment/result access based on actual EHR records and authenticated clinician review.
- Android **Health Connect** for sleep, steps, heart rate and (where supported) skin temperature; appropriate patient permission prompts and provider limits.
- Garmin Connect Health API/approved SDK and Fitbit provider APIs where accessible; no unsupported assumption about direct Charge 6/Garmin notification APIs.
- Professionally review medical UI translations in all ten languages and accessibility; review RTL with real devices.

## Phase 4 — Regulatory readiness

- Trademark clearance for HIDVIA before public branding.
- Classification and conformity assessment strategy under the EU MDR and relevant AI Act rules, cybersecurity assurance, quality management, ethical clinical study and performance monitoring.
- No live patient deployment before independent approvals and clinical evidence.

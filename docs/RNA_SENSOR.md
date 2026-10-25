# RNA sensor integration — provisional interoperability contract

**Not an RNA assay, a validated biomarker or a real vendor driver.** The manufacturer, assay cartridge, measurement units, QC algorithm, device connectivity and wireless specification have not been supplied. There is no scientifically defensible universal RNA sensor Bluetooth protocol.

## Working data path

1. A **phone or clinician computer** can load a fictional, de-identified JSON reading exported by a device or simulator. The patient/clinician authenticates to the demo service and submits it to `POST /api/rna`; authenticated role-scoped history is at `GET /api/rna` (clinicians may use `?patient_id=1`). Payloads are QC-tagged and **are not used in flare prediction**.
2. On **desktop Chrome/Edge over HTTPS**, the same UI can request an optional BLE GATT service/characteristic or Web Serial port; a compatible device must emit complete UTF-8 `hidvia-rna-v1` JSON per GATT value (or one newline-terminated JSON frame per serial message). Serial currently assumes 9600 baud. No auto-discovery of unknown vendor protocols.
3. On **Android**, the file importer works in the app. The Android BLE adapter is only operational when vendor UUIDs, Android Bluetooth permissions, and JSON wire format are compatible; a vendor-specific decoder and fragmentation handling may be needed. Browser Web Bluetooth is generally unavailable from embedded Android WebView.

## Canonical research payload

See `web/rna-example.json`:

```json
{
  "schema":"hidvia-rna-v1", "sample_id":"SYNTHETIC_SAMPLE_001",
  "sampled_at":"2026-10-25T08:00:00+01:00",
  "source":"file", "device_id":"SIMULATOR_001",
  "units":"normalized_expression", "qc_pass":true,
  "markers":{"SYNTHETIC_MARKER_A":0.32,"SYNTHETIC_MARKER_B":0.87}
}
```

`patient_id` is determined from the patient session, never trusted from a patient device. A clinician must select the intended patient. No raw sequences or personally identifying sample metadata are supported. There is no interpretation of individual RNA values; they require documented assay units, QC, reproducibility and clinical relevance. **Never upload actual patient data to this demo.**

## Real-device prerequisites

Obtain exact brand/model, firmware version, Bluetooth service/characteristic UUIDs or USB protocol, encoding, framing, calibration controls, authorized access/SDK, encryption, sample provenance, and assay normalization. Integrate through a tested vendor adapter (BLE/USB/file). Only after approved datasets and a validated model are provided can molecular features be considered for scoring.

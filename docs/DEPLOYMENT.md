# Online demonstration deployment — not clinical hosting

`render.yaml` is a **Render Blueprint** which can serve the Python backend and static patient/clinician interfaces over the internet after the code is pushed to GitHub and the developer authorizes Render to access the repository. It does **not** deploy automatically by existing in the repo.

1. Push the complete project root to `https://github.com/blas-llavero/HIDVIA` (not just this README or workflow).
2. In a Render account, choose **New → Blueprint**, connect the GitHub repository and apply `render.yaml` (review any service pricing/availability). Render runs `python3 server/app.py` and supplies an HTTPS domain.
3. The app is expected at `https://<assigned-host>/patient` and clinicians at `https://<assigned-host>/clinician`. Verify `https://<assigned-host>/api/health`.
4. For the mobile app, open **Settings → Clinic connection**, paste the HTTPS origin, sign in with the configured fictional credentials. Do not enable a real hospital connection.
5. This configuration uses **ephemeral SQLite storage**, recreated/reset when instances restart, and **in-memory login sessions**, lost on restart or across replicas. Public demonstration passwords are randomly generated at deploy time with `HIDVIA_DEMO_PASSWORD`; the UI's prefilled demo password must be replaced by the deployed value. Distribute credentials privately to hackathon judges, not to patients.

**WARNING: Absolutely no identifiable patients, RNA assay output, clinical images or real records may be processed by this deployment.** The app has no regulated security controls, MFA, long-lived audited sessions, hardened authorization, database encryption, clinical audit trails, DPIA or medical-device validation. For production: OIDC, secure cookies, database persistence/encryption, RBAC, consent, logging minimization, HIPAA/GDPR DPIA and security testing.

GitHub Pages by itself cannot host the Python API, so do not advertise a Pages frontend as full working clinician integration. A hosting account is needed for the running backend; GitHub repository publication alone is not deployment.

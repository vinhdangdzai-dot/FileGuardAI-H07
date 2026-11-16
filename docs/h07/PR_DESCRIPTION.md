The MVP lacked a complete H07 evidence matrix and several management controls. This change adds server-side Admin/Auditor authorization, CSRF protection, persistent password-hash configuration, login throttling, append-only security/access events, validated log filtering, safe admin CSV export and non-overwriting SQLite backups. Existing file authorization remains independent of ML; the deployed v1 model is unchanged.

It also includes the prior workspace review fixes, source/byte-preserving reproducibility, Windows CI configuration, CWE-22 risk analysis, architecture/Activity/ERD, ten use cases and technical material for all four thesis chapters. Frozen v1/v2/regex were compared on a new 236-row public-source corpus and a separate 20-example OWASP encoding challenge, without retraining or threshold selection. Scores, per-row predictions, source/license hashes and limitations are retained.

Evidence paths use byte-preserving Git attributes: prior autocrlf normalization could invalidate recorded SHA-256 values on a fresh clone. The archived working files keep their original bytes; evidence diffs are disabled so the source/doc changes remain reviewable. Raw files and manifests remain available through the evidence links.

Validation performed locally:

- Pytest: 76 passed, 3 skipped; 15 subtests passed (sklearn version warning treated as error).
- Real TCP dashboard/CSRF: 17/17 passed.
- Real TCP download security: 33 passed, 3 symlink skips; smoke 10/10 passed.
- Repeated 4-worker TCP measurement: 144 requests / 144 log rows, no wrong status/body or secret leak, 90/90 defined policy violations blocked. This is a local fixture measurement, not a production performance claim.
- New external corpus: all methods scored 1.0; small OWASP challenge: v1/v2 scored 1.0, regex accuracy 0.8, recall 0.6, F1 0.75. This does not show v2 superiority over v1 or real-world generalization.

The matrix honestly records 11/12 minimum items met. PI 3.1 remains unmet for complete Windows symlink evidence: real symlink creation still returns WinError 1314, and the trusted-repository/TOCTOU limitation remains. The old disclosed benchmark also has 15 canonical-equivalent paths across train/test; it is not a pristine blind benchmark. Public-source labels are lexical and source-correlated.

Review `docs/MA_TRAN_H07.md` and `docs/h07/CHUONG_4.md`. This PR is draft for owner review; it does not merge into main. Local databases and actual credential files are excluded. CI is configured; remote CI success must be checked separately.

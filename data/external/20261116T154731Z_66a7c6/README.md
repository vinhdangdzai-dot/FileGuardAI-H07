# Public-source external lexical corpus

Collected UTC: 2026-11-16T15:47:31.082755+00:00. Models frozen UTC: 2026-11-16T15:44:49.433043+00:00.
400 rows; 200 suspicious + 200 benign controls.

## Sources

- SecLists LFI-Jhaddix: https://raw.githubusercontent.com/danielmiessler/SecLists/4d5e414c9631f3c12ee1ac86ff7234d848391fd3/Fuzzing/LFI/LFI-Jhaddix.txt (MIT, license preserved).
- Flask 3.1.2 repository tree: https://api.github.com/repos/pallets/flask/git/trees/2c1b30d0503cfb064f1cb252e6614a06915a362a?recursive=1 (BSD-3-Clause, license preserved).
- Background on percent/double encoding: https://community.owasp.org/Double_Encoding

## Annotation and normalization

Positive candidates are public payload lines having a parent component or
absolute/UNC/drive syntax in raw or at most two URL-decode views. Negative
controls are actual relative Flask repository filenames without those markers.
These labels express lexical intent, not filesystem access or exploit success.
Out-of-scope LFI wrappers/relative sensitive names without traversal evidence
are excluded rather than automatically called malicious or benign.

Payload whitespace is stripped and Unicode normalized NFC. Model input keeps
percent escapes, case and separators. No URL decoding of the persisted input.
CSV keeps source_original, URL, revision, line and label_reason per sample.
Exclude exact and two-decode/slash/casefold-equivalent matches to all original
10,000 rows. De-duplicate exact public strings. Canonically related external
variants may remain; their count is in external_manifest.json.

Select up to 200 per class by SHA256(path), with no model-dependent filtering.
Neither model nor validation selection reads this corpus; it is evaluation-only.
No attack requests are sent to public hosts; network use only downloads sources.

This is a source-derived, weakly annotated lexical corpus, not a representative
real-world benchmark. Public file paths are benign syntax controls, not normal
web traffic. Source and label are correlated. No claim of fully blind research
or proven real-world generalization is justified.

# Document sources

Markdown versions of the two documents, exported at each release together with the PDFs in
`docs/`. They exist so that anyone can read the text in a diff, quote a line in an issue, or
propose a correction in a pull request.

| File | PDF |
| --- | --- |
| `white-paper.md` | `docs/4D-VODS_White_Paper_v1.1.pdf` |
| `technical-note-TN-001.md` | `docs/4D-VODS_Technical_Note_TN-001.pdf` (rev. 1.1) |

The editable masters are kept by the author; accepted corrections are applied there and both
the PDF and the Markdown are re-exported. Charts appear here as images; their values are in
`figures/data/*.csv` and `results/`.

Every number quoted in these files is registered in `results/claims.json` and checked against
the results by `python -m vods check` and the test suite.

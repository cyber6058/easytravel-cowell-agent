# Passport data

Create one object per prepared passport image. Keep the file local and private.
Every printed passport field and both TD3 MRZ lines are required before normal
export.

```json
[
  {
    "recordId": "P001-01",
    "imageName": "P001-01.jpg",
    "passportNo": "T00000000",
    "idNo": "X900000000",
    "englishSurname": "CHEN",
    "englishGiven": "TEST USER",
    "sex": "M",
    "chineseSurname": "陳",
    "chineseGiven": "測試",
    "birthDate": "1990/01/01",
    "issueDate": "2020/01/01",
    "expiryDate": "2030/01/01",
    "birthPlace": "台灣",
    "nationality": "台灣",
    "mobile": "",
    "email": "",
    "taiwanCompatriotPermitNo": "",
    "issueCount": "",
    "permitStartDate": "",
    "permitEndDate": "",
    "mrzLine1": "P<TWNCHEN<<TEST<USER<<<<<<<<<<<<<<<<<<<<<<<",
    "mrzLine2": "<EXACTLY 44 CHARACTERS FROM THE PASSPORT>",
    "uncertainties": []
  }
]
```

The example values are synthetic. Do not copy them into a real record.

## Extraction rules

- Read one prepared, upright crop at a time. Do not transcribe from a whole PDF
  page containing several passports.
- Preserve printed English hyphens. Put surname and given names in separate
  fields; do not include an honorific.
- Normalize dates to `YYYY/MM/DD`; use the printed date to determine the
  century because MRZ dates contain only two-digit years.
- Use `M`, `F`, or `X` exactly as printed.
- Copy each MRZ line as exactly 44 characters. Keep `<` filler characters.
- Cross-check passport number, personal ID, English name, sex, birth date,
  expiry date, and nationality against the MRZ.
- Leave phone, email, and permit-only fields blank when absent. Never infer
  them.
- If any required character is unreadable, add a short description to
  `uncertainties`; do not guess and do not place `?` in a required field.
  Validation intentionally blocks the record until it is reviewed.
- Keep `recordId` aligned with the image produced by `passports prepare`.
  Duplicate passport numbers or personal IDs are blocking errors.

The validator reports only record IDs and field classes, not passenger values.
Normal export requires all MRZ check digits and printed/MRZ comparisons to pass.

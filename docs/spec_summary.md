# Complaint Service Hub Prototype Spec

## Distribution
Users receive only `Complaint_Service_Hub_Distribution.zip` after Windows build.
They extract the ZIP and run `Complaint_Service_Hub.exe`.

## Apps
1. Complaint Tool
   - Country-based UI language and recipients.
   - Hospital and system serial master selection.
   - One-to-one master values are auto-filled.
   - Multiple candidates remain blank and selectable by dropdown.
   - Complaint email generation by Outlook or Copy Template.
   - English-content check for complaint subject and description.
   - Default selections saved in `config/settings.json`.

2. Master ZIP Builder
   - Edit JSON masters in GUI.
   - Validate JSON.
   - Create master update ZIP.

3. Salesforce Auto Input Tool
   - Reads current complaint values.
   - Shows Salesforce input sequence from profile mapping.
   - Prototype copies mapped sequence to clipboard.
   - Final field automation will be completed after Salesforce screenshots are provided.

## ZIP update
The main app can import a master/spec ZIP. Before update it creates a backup folder.

## Externalized files
- `masters/hospital_master.json`
- `masters/recipients.json`
- `masters/field_definitions.json`
- `masters/translations.json`
- `templates/email_template.json`
- `profiles/salesforce_profile_default.json`

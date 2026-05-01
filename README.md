# Instrument Tracker

A desktop app for school band rooms to manage instrument inventory, student checkouts, and repair tracking. Built for Windows.

---

## Installation

1. Download the latest `InstrumentTracker_Setup.exe` from the [Releases](../../releases) page
2. Run the installer and follow the prompts
3. Launch **Instrument Tracker** from the desktop shortcut or Start Menu

No internet connection required. All data is stored locally on your computer.

---

## First-Time Setup

1. **Add your students** — Go to the Students page and add students manually, or import them from a spreadsheet (CSV or Excel)
2. **Add your instruments** — Go to the Instruments page and add instruments manually, or import from a spreadsheet
3. **Print QR labels** — Go to the QR Codes tab to generate and print labels for your instruments. Attach them to the cases for fast scanning

---

## Daily Use

### Checking Instruments In and Out
The **Actions tab** is your home base for daily checkout and check-in.

- **Camera mode** — point your webcam at an instrument's QR code to look it up instantly
- **Manual / Scanner mode** — type an instrument name or use a handheld barcode scanner

After scanning, you'll confirm the instrument and pick the student (for checkouts) or confirm the return (for check-ins).

### Changing Instrument Status
On the **Instruments page**, right-click any row to change its status. You can also select multiple rows (Ctrl+click or Shift+click) and right-click to update them all at once.

Available statuses:
| Status | Meaning |
|---|---|
| Available | In inventory, ready to check out |
| Checked Out | Assigned to one or more students |
| Needs Repair | Flagged for repair, still on-site |
| Out for Repair | Sent to a repair shop |
| Summer Hold | Held over summer for a specific student |

---

## Key Features

- **Multi-student checkout** — Assign one instrument to multiple students (e.g., shared instruments or section lending)
- **Repair tracking** — Log repair notes and attach invoices or photos when instruments return from repair
- **Summer Hold** — Keep an instrument reserved for a student over the summer; resume checkout in the fall with one click
- **Contracts** — Attach signed contract photos to a checkout for record-keeping
- **Reports** — Print or export checkout reports, repair lists, and Summer Hold summaries
- **Backup & Restore** — Save a copy of your database at any time from the Settings area
- **Import from spreadsheet** — Bulk-add students or instruments from CSV or Excel files

---

## Tips

- **Right-click** a row on the Instruments page to change its status — this is the fastest way to update a single instrument
- **Double-click** any row to view the full history, contracts, and notes for that instrument or student
- **Bulk Change Status** (toolbar button on Instruments page) lets you update many instruments at once, with filters to narrow down the list
- The **Recent Activity** feed on the Actions tab shows the last 20 actions across the whole system

---

## Data & Backups

Your database is stored in:
```
C:\Users\<YourName>\AppData\Roaming\Instrument Tracker\
```

It's recommended to back up regularly using the built-in backup tool, especially before major changes like importing a new student roster.

---

## Support

For issues or feature requests, open a ticket on the [Issues](../../issues) page.

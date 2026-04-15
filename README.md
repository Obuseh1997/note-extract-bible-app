# YouVersion Notes & Highlights Exporter

Export your Bible notes from [YouVersion](https://bible.com) as a clean, searchable markdown file.

## What it does

- Extracts all your **notes** (verse reference + your written reflections)
- Outputs a single `.md` file you can import into Apple Notes, Obsidian, or any markdown app
- Makes your notes **searchable** across all your Bible reading

## Privacy

- **No data is stored** anywhere — not on disk, not on a server
- Authentication happens directly between you and YouVersion's API
- This tool is open source — read the code yourself

---

## Option 1: Web App (easiest)

Visit **[note-extract-bible-app.streamlit.app](https://note-extract-bible-app.streamlit.app)** — no setup needed.

### How to get your auth token (for Google Sign-In users)

1. Open [bible.com](https://www.bible.com) in your browser and log in
2. Open Developer Tools (`F12` on Windows / `Cmd+Option+I` on Mac)
3. Go to **Application** tab → **Storage** → **Cookies** → `https://www.bible.com`
4. Find the cookie named **`yva`** (it starts with `eyJhbGci...`)
5. Click the row and copy the full value from the Value field
6. Paste it into the web app when prompted

---

## Option 2: CLI (technical users)

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage

**Google Sign-In (most users):**

```bash
python cli.py
```

Follow the prompt — paste your `yva` cookie value from bible.com DevTools (same steps as above).

**Email/password login:**

```bash
python cli.py --username your@email.com --password yourpassword
```

### Options

```
-o, --output    Output file path (default: output/youversion-export.md)
--token         Provide auth token directly (skip prompt)
--user-id       Provide user ID directly (skip auto-detection)
--username      YouVersion email (for password auth)
--password      YouVersion password (for password auth)
```

---

## Output format

```markdown
# My YouVersion Notes & Highlights
Exported: 2026-04-14

**112 notes** | **270 highlights**

---

## Notes

### 1 Samuel 16:14  <sub>2025-04-13</sub>

**My note:** Depression is a spirit.

---

### Romans 8:28  <sub>2025-03-01</sub>

**My note:** God works all things together for good.

---
```

## Requirements

- Python 3.10+
- A YouVersion account with notes

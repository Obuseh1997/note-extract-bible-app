# YouVersion Notes & Highlights Exporter

Export your Bible notes and highlights from [YouVersion](https://bible.com) as clean markdown files.

## What it does

- Extracts all your **notes** (with verse text and your written reflections)
- Extracts all your **highlights** (with verse text and color)
- Outputs a single `.md` file you can import into Apple Notes, Obsidian, or any markdown app

## Privacy

- **No data is stored** anywhere — not on disk, not on a server
- Authentication happens directly between you and YouVersion's API
- This tool is open source — read the code yourself

---

## Option 1: Web App (non-technical)

Visit the hosted Streamlit app (URL TBD) and follow the prompts.

To run it locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Option 2: CLI (technical)

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage

**If you have a YouVersion email/password:**

```bash
python cli.py --username your@email.com --password yourpassword
```

**If you use Google Sign-In:**

```bash
python cli.py
```

You'll be guided to grab your auth token from bible.com's browser cookies. Steps:

1. Open https://www.bible.com in your browser and log in
2. Open Developer Tools (F12 or Cmd+Option+I)
3. Go to **Application** tab > **Cookies** > `bible.com`
4. Find the cookie named `token` or `access_token`
5. Paste it when the CLI prompts you

### Options

```
-o, --output    Output file path (default: output/youversion-export.md)
--token         Provide auth token directly (skip prompt)
--user-id       Provide user ID directly (skip auto-detection)
--username      YouVersion email (for password auth)
--password      YouVersion password (for password auth)
```

### Environment variables

You can also set these instead of using CLI flags:

```bash
export YV_TOKEN="your-token-here"
export YV_USER_ID="12345678"
python cli.py
```

## Output format

```markdown
# My YouVersion Notes & Highlights
Exported: 2026-04-13

**5 notes** | **12 highlights**

---

## Notes

### 1 Samuel 16:14 (NLT)  <sub>2025-04-13</sub>

> Now the Spirit of the Lord had left Saul...

**My note:** Depression is a spirit.

---

## Highlights

### Psalms 34:19 (NLT) 🟡  <sub>2025-04-13</sub>

> The righteous person faces many troubles, but the Lord comes to the rescue each time.

---
```

## Requirements

- Python 3.10+
- A YouVersion account with notes/highlights

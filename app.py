"""Streamlit web UI for YouVersion Notes & Highlights Exporter."""

import asyncio

import streamlit as st

from extractor import AuthError, NetworkError, authenticate_password, extract_all
from formatter import format_markdown

st.set_page_config(
    page_title="YouVersion Export",
    page_icon="\u2702\ufe0f",
    layout="centered",
)

st.title("YouVersion Notes & Highlights Exporter")
st.markdown(
    "Export your Bible notes and highlights from YouVersion as a clean markdown file. "
    "**No data is stored** \u2014 everything happens in your browser session."
)

st.divider()

# --- Output options ---
with st.expander("Output options", expanded=False):
    group_by_book = st.checkbox(
        "Group by Bible book (recommended)",
        value=True,
        help="Groups notes under book headings in canonical order, with a table of contents. Uncheck for a flat chronological list.",
    )
    include_toc = st.checkbox(
        "Include table of contents",
        value=True,
        help="Adds a clickable TOC at the top, grouped by book.",
    )

# --- Auth Selection ---
auth_method = st.radio(
    "How do you sign into YouVersion?",
    ["Google Sign-In (token)", "Email & Password"],
    horizontal=True,
)

token = None
user_id = None

if auth_method == "Email & Password":
    with st.form("login_form"):
        username = st.text_input("YouVersion email")
        password = st.text_input("YouVersion password", type="password")
        submitted = st.form_submit_button("Connect & Export", type="primary")

    if submitted and username and password:
        with st.spinner("Authenticating..."):
            try:
                token, user_id = asyncio.run(authenticate_password(username, password))
                st.success(f"Authenticated as user {user_id}")
            except AuthError as e:
                st.error(str(e))
            except NetworkError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Authentication failed: {e}")

else:
    st.markdown("### How to get your auth token")
    st.markdown(
        """
1. Open **[bible.com](https://www.bible.com)** in a new tab and log in
2. Open **Developer Tools** (`F12` on Windows, `Cmd+Option+I` on Mac)
3. Go to the **Application** tab → **Storage** → **Cookies** → `https://www.bible.com`
4. Find the cookie named **`yva`** (its value starts with `eyJhbGci...`)
5. Click the row, copy the full value from the **Value** column
6. Paste it below and click **Export**

> **Tip:** Tokens expire quickly. If you see an "expired" error, just refresh bible.com and grab a fresh `yva` value.
        """
    )

    with st.form("token_form"):
        token_input = st.text_input(
            "Auth token (`yva` cookie value)",
            type="password",
            placeholder="eyJhbGci...",
        )
        user_id_input = st.text_input(
            "User ID",
            help="Leave blank — we'll auto-detect from the token.",
        )
        submitted = st.form_submit_button("Export", type="primary")

    if submitted and token_input:
        token = token_input.strip()

        if not user_id_input:
            try:
                import jwt
                decoded = jwt.decode(token, options={"verify_signature": False})
                user_id = decoded.get("user_id") or decoded.get("sub")
            except Exception:
                pass
        else:
            try:
                user_id = int(user_id_input)
            except ValueError:
                st.error("User ID must be a number.")

        if not user_id:
            st.error(
                "Couldn't auto-detect your user ID from the token. "
                "Paste your user ID manually above."
            )
            token = None

# --- Export ---
if token and user_id:
    progress_bar = st.progress(0, text="Starting...")
    status_text = st.empty()

    # Streamlit-aware progress callback
    # We can't know total pages in advance, so we just show counts
    def make_progress_callback():
        counts = {"note": 0, "highlight": 0, "last_page": {}}

        def cb(kind: str, page: int, items_on_page: int, total_so_far: int):
            counts[kind] = total_so_far
            counts["last_page"][kind] = page
            label = "Notes" if kind == "note" else "Highlights"
            status_text.markdown(
                f"**Fetching {label}** — page {page}, "
                f"{total_so_far} items collected so far..."
            )
            # Rough progress: jump forward as pages complete (we don't know total)
            progress_bar.progress(
                min(0.95, 0.1 + (counts["note"] + counts["highlight"]) / 500.0),
                text=f"Fetching data ({counts['note']} notes, {counts['highlight']} highlights)",
            )

        return cb

    try:
        data = asyncio.run(
            extract_all(token, int(user_id), progress=make_progress_callback())
        )
    except AuthError as e:
        progress_bar.empty()
        status_text.empty()
        st.error(str(e))
        st.stop()
    except NetworkError as e:
        progress_bar.empty()
        status_text.empty()
        st.error(str(e))
        st.stop()
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Export failed: {e}")
        st.stop()

    progress_bar.progress(1.0, text="Formatting markdown...")

    total_notes = len(data["notes"])
    total_highlights = len(data["highlights"])

    if total_notes + total_highlights == 0:
        progress_bar.empty()
        status_text.empty()
        st.warning("No notes or highlights found. Double-check your credentials.")
        st.stop()

    markdown = format_markdown(
        data,
        group_by_book=group_by_book,
        include_toc=include_toc,
    )

    progress_bar.empty()
    status_text.empty()

    st.success(
        f"Found **{total_notes} notes** and **{total_highlights} highlights**"
    )

    st.download_button(
        label="Download Markdown File",
        data=markdown,
        file_name="youversion-export.md",
        mime="text/markdown",
        type="primary",
    )

    with st.expander("Preview export", expanded=False):
        st.markdown(markdown)

"""Streamlit web UI for YouVersion Notes & Highlights Exporter."""

import asyncio

import streamlit as st

from extractor import authenticate_password, extract_all
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

# --- Auth Selection ---
auth_method = st.radio(
    "How do you sign into YouVersion?",
    ["Email & Password", "Google Sign-In (token)"],
    horizontal=True,
)

token = None
user_id = None

if auth_method == "Email & Password":
    with st.form("login_form"):
        username = st.text_input("YouVersion email")
        password = st.text_input("YouVersion password", type="password")
        submitted = st.form_submit_button("Connect & Export")

    if submitted and username and password:
        with st.spinner("Authenticating..."):
            try:
                token, user_id = asyncio.run(authenticate_password(username, password))
                st.success(f"Authenticated (user {user_id})")
            except Exception as e:
                st.error(f"Authentication failed: {e}")

else:
    st.markdown("""
**How to get your token:**
1. Open [bible.com](https://www.bible.com) and log in
2. Open Developer Tools (`F12` or `Cmd+Option+I`)
3. Go to **Application** tab \u2192 **Cookies** \u2192 `bible.com`
4. Find the cookie named **`yva`** (it starts with `eyJhbGci...`)
5. Paste it below
    """)

    with st.form("token_form"):
        token_input = st.text_input("Auth token", type="password")
        user_id_input = st.text_input(
            "User ID (leave blank to auto-detect from token)"
        )
        submitted = st.form_submit_button("Export")

    if submitted and token_input:
        token = token_input.strip()

        # Try to extract user_id from JWT
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
                "Could not detect user ID from token. "
                "Please enter it manually above."
            )
            token = None

# --- Export ---
if token and user_id:
    with st.spinner("Fetching your notes and highlights..."):
        try:
            data = asyncio.run(extract_all(token, int(user_id)))
        except Exception as e:
            st.error(f"Export failed: {e}")
            st.stop()

    total_notes = len(data["notes"])
    total_highlights = len(data["highlights"])

    if total_notes + total_highlights == 0:
        st.warning("No notes or highlights found. Double-check your credentials.")
        st.stop()

    st.success(
        f"Found **{total_notes} notes** and **{total_highlights} highlights**"
    )

    markdown = format_markdown(data)

    # Preview
    with st.expander("Preview export", expanded=True):
        st.markdown(markdown)

    # Download
    st.download_button(
        label="Download Markdown File",
        data=markdown,
        file_name="youversion-export.md",
        mime="text/markdown",
        type="primary",
    )

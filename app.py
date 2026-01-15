import streamlit as st
from fetcher import SubstackFetcher
from orchestrator import run_download
from logger import setup_logger

logger = setup_logger(__name__)

st.set_page_config(page_title="Substack Downloader", page_icon="📚")

st.title("📚 Substack Downloader")
st.markdown("Download posts from your favorite Substack newsletter and compile them into a book.")

# Mode selection
mode = st.radio(
    "Mode",
    ("Create New", "Update Existing EPUB"),
    horizontal=True,
    help="Create a new book or update an existing EPUB with new posts"
)

col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input("Enter Substack URL", placeholder="https://newsletter.pragmaticengineer.com")
with col2:
    if mode == "Create New":
        limit = st.number_input("Limit (0 for all)", min_value=0, value=0, step=10)
    else:
        limit = 0  # Always check all posts in update mode

format_option = st.selectbox(
    "Output Format",
    ("PDF", "EPUB", "JSON", "HTML", "TXT", "Markdown"),
    index=1 if mode == "Update Existing EPUB" else 0,
    disabled=mode == "Update Existing EPUB",
    help="Update mode only works with EPUB format" if mode == "Update Existing EPUB" else None
)

use_cache = st.checkbox(
    "Use cache",
    value=False,
    help="Cache fetched content to speed up repeat downloads"
)

with st.expander("🔐 Advanced: Authentication for Paywalled Content"):
    st.markdown("""
    **Need to download paywalled content?** You'll need your Substack authentication cookie.

    ### How to find your cookie:

    **Chrome / Edge:**
    1. Go to any Substack site where you're logged in
    2. Press `F12` or right-click → "Inspect"
    3. Go to **Application** tab → **Cookies** → `https://substack.com`
    4. Find `substack.sid` and copy its **Value**

    **Firefox:**
    1. Go to any Substack site where you're logged in
    2. Press `F12` or right-click → "Inspect"
    3. Go to **Storage** tab → **Cookies** → `https://substack.com`
    4. Find `substack.sid` and copy its **Value**

    **Safari:**
    1. Enable Developer menu: Preferences → Advanced → "Show Develop menu"
    2. Go to any Substack site where you're logged in
    3. Develop → Show Web Inspector → Storage → Cookies → `substack.com`
    4. Find `substack.sid` and copy its **Value**

    ⚠️ **Security Note:** Your cookie is sensitive! It will be:
    - Used only for this download session
    - Never stored or logged
    - Transmitted only over HTTPS
    - Kept in memory only (not saved to disk)
    """)

    cookie = st.text_input(
        "Substack Cookie (substack.sid)",
        placeholder="Paste the substack.sid value here",
        type="password",
        help="Format: a long string of random characters like 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'"
    )

    if st.button("Check Status"):
        if not cookie:
            st.warning("⚠️ Please enter a cookie first.")
        else:
            with st.spinner("Verifying..."):
                try:
                    verify_fetcher = SubstackFetcher(
                        url="https://substack.com",
                        cookie=cookie,
                        enable_cache=False,
                    )
                    if verify_fetcher.verify_auth():
                        st.success("✅ Session Valid: Logged in")
                    else:
                        st.error("❌ Session Invalid: Please check your cookie")
                except Exception as e:
                    logger.exception("Error checking auth status")
                    st.error(f"Error checking status: {e}")

button_label = "Update EPUB" if mode == "Update Existing EPUB" else "Download & Compile"

if st.button(button_label):
    if not url:
        st.error("Please enter a valid URL.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def status_callback(message):
                    st.write(message)

                def progress_callback(current, total, title):
                    if total:
                        status_text.text(f"Processing {current}/{total}: {title}")
                        progress_bar.progress(current / total)

                result = run_download(
                    url=url,
                    cookie=cookie,
                    mode=mode,
                    limit=limit,
                    format_option=format_option,
                    use_cache=use_cache,
                    status_callback=status_callback,
                    progress_callback=progress_callback,
                )

                if result.status == "missing_epub":
                    st.error(result.message)
                    status.update(label="Failed", state="error")
                    st.stop()
                if result.status == "no_new_posts":
                    st.info(result.message)
                    status.update(label="Already up to date", state="complete")
                    st.stop()
                if result.status == "no_posts":
                    st.error(result.message)
                    status.update(label="Failed", state="error")
                    st.stop()

                # Success message
                if mode == "Update Existing EPUB":
                    status.update(label="Updated!", state="complete", expanded=False)
                    st.success(f"Successfully added {len(result.cleaned_posts)} new post(s) to {result.filename}!")
                else:
                    status.update(label="Done!", state="complete", expanded=False)
                    st.success(f"Successfully compiled {result.filename}!")

                # 4. Download Button
                with open(result.output_path, "rb") as f:
                    download_label = "Download Updated EPUB" if mode == "Update Existing EPUB" else f"Download {format_option}"
                    st.download_button(
                        label=download_label,
                        data=f,
                        file_name=result.filename,
                        mime=result.mime_type
                    )
                        
            except Exception as e:
                logger.exception("Processing failed")
                st.error(f"An error occurred: {e}")
                status.update(label="Error", state="error")

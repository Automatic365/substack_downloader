import streamlit as st
from fetcher import SubstackFetcher
from orchestrator import run_download
from logger import setup_logger

logger = setup_logger(__name__)

st.set_page_config(page_title="Substack Downloader", page_icon="⚡")

# --- EXECUTIVE THEME INJECTION ---
st.markdown("""
<style>
    /* 
       THEME: EXECUTIVE MIDNIGHT
       - Background: #141428 (Analyzed from exec.png)
       - Card BG: #1E1E32
       - Text: #E2E8F0
       - Primary: #3B82F6 (Royal Blue)
    */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #141428 !important;
        color: #E2E8F0 !important;
    }

    /* Headings */
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    h1 {
        background: linear-gradient(90deg, #FFFFFF, #94A3B8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 0.5rem;
    }

    /* Cards / Containers */
    .stApp > header { background-color: #141428 !important; }
    
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input {
        background-color: #1E1E32 !important;
        color: #FFFFFF !important;
        border: 1px solid #33334D !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
    }
    .stTextInput > div > div > input:focus, 
    .stNumberInput > div > div > input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
    }

    /* Selectbox & Radio */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1E1E32 !important;
        border: 1px solid #33334D !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
    }

    /* Primary Button (Gradient) */
    .stButton button {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
        transition: transform 0.1s ease, box-shadow 0.1s ease !important;
        width: 100%;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.3) !important;
    }
    .stButton button:active {
        transform: translateY(0);
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1E1E32 !important;
        border-radius: 8px !important;
        border: 1px solid #33334D !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #3B82F6, #60A5FA) !important;
    }

    /* Helper Text */
    .stMarkdown p, .stText {
        color: #94A3B8 !important; /* Slate-400 */
    }

    /* Divider */
    hr { border-color: #33334D !important; }

</style>
""", unsafe_allow_html=True)

st.title("Substack Downloader")
st.markdown("Download posts from your favorite Substack newsletter and compile them into a book.")

# Mode selection
mode = st.radio(
    "Mode",
    ("Create New", "Update Existing EPUB"),
    horizontal=True,
    help="Create a new book or update an existing EPUB with new posts"
)

# Use columns for layout
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

with st.expander("⚙️ Configuration"):
    c1, c2, c3 = st.columns(3)
    with c1:
        use_cache = st.checkbox("Enable Cache", value=False)
    with c2:
        use_concurrency = st.checkbox("Concurrent Fetching", value=True)
    with c3:
        pass # spacer
    
    c4, c5 = st.columns(2)
    with c4:
        max_concurrent = st.slider("Max Threads", 1, 10, 5)
    with c5:
        batch_size = st.number_input("Batch Size", min_value=10, value=50, step=10)

with st.expander("🔐 Authentication (Paywalled Content)"):
    st.info("Required only for premium newsletters. Your cookie is not stored.")
    cookie = st.text_input(
        "Substack Cookie (substack.sid)",
        placeholder="eyJ...",
        type="password"
    )
    if st.button("Verify Session"):
        if not cookie:
            st.warning("Please enter a cookie first.")
        else:
            with st.spinner("Verifying..."):
                try:
                    verify_fetcher = SubstackFetcher("https://substack.com", cookie=cookie, enable_cache=False)
                    if verify_fetcher.verify_auth():
                        st.success("Session Valid")
                    else:
                        st.error("Session Invalid")
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")
button_label = "Update EPUB" if mode == "Update Existing EPUB" else "Download & Compile"

# Big action button
if st.button(button_label):
    if not url:
        st.error("Please enter a valid URL.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def status_callback(message):
                    status_text.write(message)

                def progress_callback(current, total, title):
                    if total:
                        status_text.text(f"{title} ({current}/{total})")
                        progress_bar.progress(current / total)

                result = run_download(
                    url=url,
                    cookie=cookie,
                    mode=mode,
                    limit=limit,
                    format_option=format_option,
                    use_cache=use_cache,
                    use_concurrency=use_concurrency,
                    max_concurrent=max_concurrent,
                    batch_size=batch_size,
                    status_callback=status_callback,
                    progress_callback=progress_callback,
                )

                if result.status == "missing_epub":
                    st.error(result.message)
                    status.update(label="Failed", state="error")
                    st.stop()
                if result.status == "no_new_posts":
                    st.info(result.message)
                    status.update(label="Up to date", state="complete")
                    st.stop()
                if result.status == "no_posts":
                    st.error(result.message)
                    status.update(label="Failed", state="error")
                    st.stop()

                if mode == "Update Existing EPUB":
                    status.update(label="Complete", state="complete", expanded=False)
                    st.success(f"Added {len(result.cleaned_posts)} posts to {result.filename}!")
                else:
                    status.update(label="Complete", state="complete", expanded=False)
                    st.success(f"Compiled {result.filename}!")

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
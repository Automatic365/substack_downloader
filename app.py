import streamlit as st
from fetcher import SubstackFetcher
from orchestrator import run_download
from logger import setup_logger

logger = setup_logger(__name__)

st.set_page_config(page_title="Substack Breach Protocol", page_icon="💻")

# --- CSS INJECTION FOR HACKER AESTHETIC ---
st.markdown("""
<style>
    /* Global Font & Colors */
    body {
        color: #00FF41 !important;
        background-color: #000000 !important;
        font-family: 'Courier New', Courier, monospace !important;
    }
    .stApp {
        background-color: #000000;
    }

    /* CRT Scanline Effect Overlay */
    .scanlines {
        position: fixed;
        left: 0;
        top: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        z-index: 9999;
        background: linear-gradient(
            to bottom,
            rgba(255,255,255,0),
            rgba(255,255,255,0) 50%,
            rgba(0,0,0,0.2) 50%,
            rgba(0,0,0,0.2)
        );
        background-size: 100% 4px;
        box-shadow: inset 0 0 100px rgba(0,0,0,0.9);
    }
    
    /* Headers with Glow */
    h1, h2, h3, h4, h5, h6 {
        color: #00FF41 !important;
        text-shadow: 0 0 5px #00FF41;
        font-family: 'Courier New', Courier, monospace !important;
        text-transform: uppercase;
        border-bottom: 2px solid #00FF41;
        padding-bottom: 5px;
    }

    /* Input Fields - Brutalist */
    .stTextInput input, .stNumberInput input {
        background-color: #000000 !important;
        color: #00FF41 !important;
        border: 1px solid #00FF41 !important;
        border-radius: 0px !important;
        font-family: 'Courier New', Courier, monospace !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        box-shadow: 0 0 10px #00FF41 !important;
        border-color: #00FF41 !important;
    }

    /* Buttons - Solid Block Style */
    .stButton button {
        background-color: transparent !important;
        color: #00FF41 !important;
        border: 2px solid #00FF41 !important;
        border-radius: 0px !important;
        font-family: 'Courier New', Courier, monospace !important;
        text-transform: uppercase;
        font-weight: bold;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background-color: #00FF41 !important;
        color: #000000 !important;
        box-shadow: 0 0 15px #00FF41;
    }
    .stButton button:active {
        transform: translate(2px, 2px);
    }

    /* Radio Buttons & Checkboxes */
    .stRadio label, .stCheckbox label {
        color: #00FF41 !important;
        font-family: 'Courier New', Courier, monospace !important;
    }

    /* Select Box */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #000000 !important;
        border-color: #00FF41 !important;
        border-radius: 0px !important;
        color: #00FF41 !important;
    }

    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #00FF41 !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #0d1117 !important;
        color: #00FF41 !important;
        border: 1px solid #00FF41 !important;
        border-radius: 0px !important;
    }
    
    /* Status Container */
    .stStatusWidget {
        border: 1px solid #00FF41 !important;
        background-color: #000000 !important;
    }
</style>
<div class="scanlines"></div>
""", unsafe_allow_html=True)

st.title(">_ SUBSTACK_BREACH_PROTOCOL v2.0")
st.markdown("INITIALIZING CONNECTION... READY TO EXTRACT DATA.")

# Mode selection
mode = st.radio(
    "SELECT_OPERATION_MODE",
    ("INIT_NEW_DB", "UPDATE_EXISTING_DB"),
    horizontal=True,
    help="Define objective: Create new compilation or update existing archive."
)

col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input("TARGET_URL", placeholder="https://newsletter.example.com")
with col2:
    if mode == "INIT_NEW_DB":
        limit = st.number_input("FETCH_LIMIT (0=ALL)", min_value=0, value=0, step=10)
    else:
        limit = 0  # Always check all posts in update mode

format_option = st.selectbox(
    "PAYLOAD_FORMAT",
    ("PDF", "EPUB", "JSON", "HTML", "TXT", "Markdown"),
    index=1 if mode == "UPDATE_EXISTING_DB" else 0,
    disabled=mode == "UPDATE_EXISTING_DB",
    help="Update protocol only compatible with EPUB format." if mode == "UPDATE_EXISTING_DB" else None
)

use_cache = st.checkbox(
    "ENABLE_LOCAL_CACHE",
    value=False,
    help="Store intercepted packets locally to accelerate future operations."
)

use_concurrency = st.checkbox(
    "ENABLE_MULTI_THREADING",
    value=True,
    help="Execute parallel extraction threads."
)

max_concurrent = st.slider(
    "THREAD_COUNT",
    min_value=1,
    max_value=10,
    value=5,
    help="High concurrency may trigger target defense mechanisms (rate limits)."
)

batch_size = st.number_input(
    "BATCH_SIZE",
    min_value=10,
    value=50,
    step=10,
    help="Partition size for memory management."
)

with st.expander("🔐 [SECURE_ACCESS] AUTHENTICATION_TOKENS"):
    st.markdown("""
    **RESTRICTED AREA**
    Authorization required for premium content extraction.

    ### [INSTRUCTION_SET] TOKEN_EXTRACTION:

    **CHROME / EDGE:**
    1. NAVIGATE to target domain.
    2. INITIATE DevTools (`F12`).
    3. ACCESS **Application** > **Cookies**.
    4. EXTRACT `substack.sid`.

    **FIREFOX:**
    1. NAVIGATE to target domain.
    2. INITIATE DevTools (`F12`).
    3. ACCESS **Storage** > **Cookies**.
    4. EXTRACT `substack.sid`.

    **SAFARI:**
    1. ACCESS **Develop** > **Show Web Inspector**.
    2. LOCATE **Storage** > **Cookies**.
    3. EXTRACT `substack.sid`.

    ⚠️ **[WARNING]**: Token is volatile. Stored in RAM only.
    """)

    cookie = st.text_input(
        "AUTH_TOKEN (substack.sid)",
        placeholder="INSERT ENCRYPTED STRING...",
        type="password",
        help="Format: JWT-like string."
    )

    if st.button("VERIFY_ACCESS"):
        if not cookie:
            st.warning("⚠️ [ERROR] NULL_TOKEN_DETECTED.")
        else:
            with st.spinner("HANDSHAKING..."):
                try:
                    verify_fetcher = SubstackFetcher(
                        url="https://substack.com",
                        cookie=cookie,
                        enable_cache=False,
                    )
                    if verify_fetcher.verify_auth():
                        st.success("✅ [ACCESS_GRANTED] IDENTITY CONFIRMED.")
                    else:
                        st.error("❌ [ACCESS_DENIED] INVALID TOKEN.")
                except Exception as e:
                    logger.exception("Error checking auth status")
                    st.error(f"[SYSTEM_FAILURE] {e}")

button_label = "EXECUTE_UPDATE" if mode == "UPDATE_EXISTING_DB" else "EXECUTE_DOWNLOAD"

if st.button(button_label):
    if not url:
        st.error("[ERROR] TARGET_URL_MISSING.")
    else:
        with st.status("[SYSTEM] INITIATING SEQUENCE...", expanded=True) as status:
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def status_callback(message):
                    st.write(f"> {message}")

                def progress_callback(current, total, title):
                    if total:
                        status_text.text(f"PROCESSING_NODE {current}/{total}: {title}")
                        progress_bar.progress(current / total)

                result = run_download(
                    url=url,
                    cookie=cookie,
                    mode="Update Existing EPUB" if mode == "UPDATE_EXISTING_DB" else "Create New",
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
                    st.error(f"[FAILURE] {result.message}")
                    status.update(label="OPERATION_ABORTED", state="error")
                    st.stop()
                if result.status == "no_new_posts":
                    st.info(f"[INFO] {result.message}")
                    status.update(label="SYSTEM_SYNCED", state="complete")
                    st.stop()
                if result.status == "no_posts":
                    st.error(f"[FAILURE] {result.message}")
                    status.update(label="OPERATION_ABORTED", state="error")
                    st.stop()

                # Success message
                if mode == "UPDATE_EXISTING_DB":
                    status.update(label="UPDATE_COMPLETE", state="complete", expanded=False)
                    st.success(f"[SUCCESS] INJECTED {len(result.cleaned_posts)} NEW PACKETS INTO {result.filename}!")
                else:
                    status.update(label="COMPILATION_COMPLETE", state="complete", expanded=False)
                    st.success(f"[SUCCESS] ARTIFACT GENERATED: {result.filename}!")

                # 4. Download Button
                with open(result.output_path, "rb") as f:
                    download_label = "RETRIEVE_ARTIFACT"
                    st.download_button(
                        label=download_label,
                        data=f,
                        file_name=result.filename,
                        mime=result.mime_type
                    )
                        
            except Exception as e:
                logger.exception("Processing failed")
                st.error(f"[CRITICAL_ERROR] {e}")
                status.update(label="SYSTEM_CRASH", state="error")
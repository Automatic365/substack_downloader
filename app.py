import streamlit as st
import os
import time
from fetcher import SubstackFetcher
from parser import SubstackParser
from compiler import SubstackCompiler

st.set_page_config(page_title="Substack Downloader", page_icon="📚")

st.title("📚 Substack Downloader")
st.markdown("Download posts from your favorite Substack newsletter and compile them into a book.")

col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input("Enter Substack URL", placeholder="https://newsletter.pragmaticengineer.com")
with col2:
    limit = st.number_input("Limit (0 for all)", min_value=0, value=0, step=10)

format_option = st.selectbox(
    "Output Format",
    ("PDF", "EPUB", "JSON", "HTML", "TXT", "Markdown"),
    index=0
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

if st.button("Download & Compile"):
    if not url:
        st.error("Please enter a valid URL.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                # 1. Fetch Metadata
                st.write("Fetching post list from Archive API...")
                fetcher = SubstackFetcher(url, cookie=cookie)
                newsletter_title = fetcher.get_newsletter_title()
                
                fetch_limit = None if limit == 0 else limit
                metadata_list = fetcher.fetch_archive_metadata(limit=fetch_limit)
                
                if not metadata_list:
                    st.error("No posts found. Please check the URL.")
                    status.update(label="Failed", state="error")
                else:
                    st.write(f"Found {len(metadata_list)} posts from **{newsletter_title}**.")
                    
                    # 2. Fetch Content & Parse
                    st.write("Downloading and cleaning content (this may take a while)...")
                    parser_tool = SubstackParser()
                    cleaned_posts = []
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, meta in enumerate(metadata_list):
                        status_text.text(f"Processing {i+1}/{len(metadata_list)}: {meta['title']}")
                        
                        # Fetch full content
                        content = fetcher.fetch_post_content(meta['link'])
                        
                        # Parse
                        cleaned_content = parser_tool.parse_content(content)
                        
                        cleaned_posts.append({
                            'title': meta['title'],
                            'pub_date': meta['pub_date'],
                            'content': cleaned_content
                        })
                        
                        progress_bar.progress((i + 1) / len(metadata_list))
                        time.sleep(0.1) # Slight delay to be nice
                    
                    # 3. Compile
                    if format_option in ["PDF", "EPUB"]:
                        st.write(f"Compiling {format_option} (processing videos & images)...")
                    else:
                        st.write(f"Compiling {format_option}...")
                    compiler = SubstackCompiler()
                    
                    # Generate filename from title
                    safe_title = "".join(c for c in newsletter_title if c.isalnum() or c in (' ', '_', '-')).strip()
                    safe_title = safe_title.replace(" ", "_")
                    
                    format_map = {
                        "PDF": "pdf",
                        "EPUB": "epub",
                        "JSON": "json",
                        "HTML": "html",
                        "TXT": "txt",
                        "Markdown": "md"
                    }
                    file_ext = format_map[format_option]
                    filename = f"{safe_title}.{file_ext}"
                    
                    if format_option == "PDF":
                        output_path = compiler.compile_to_pdf(cleaned_posts, filename=filename)
                        mime_type = "application/pdf"
                    elif format_option == "EPUB":
                        output_path = compiler.compile_to_epub(cleaned_posts, filename=filename)
                        mime_type = "application/epub+zip"
                    elif format_option == "JSON":
                        output_path = compiler.compile_to_json(cleaned_posts, filename=filename)
                        mime_type = "application/json"
                    elif format_option == "HTML":
                        output_path = compiler.compile_to_html(cleaned_posts, filename=filename)
                        mime_type = "text/html"
                    elif format_option == "TXT":
                        output_path = compiler.compile_to_txt(cleaned_posts, filename=filename)
                        mime_type = "text/plain"
                    elif format_option == "Markdown":
                        output_path = compiler.compile_to_md(cleaned_posts, filename=filename)
                        mime_type = "text/markdown"
                    
                    status.update(label="Done!", state="complete", expanded=False)
                    st.success(f"Successfully compiled {filename}!")
                    
                    # 4. Download Button
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label=f"Download {format_option}",
                            data=f,
                            file_name=filename,
                            mime=mime_type
                        )
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
                status.update(label="Error", state="error")

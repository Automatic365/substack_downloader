import streamlit as st
import os
import time
from fetcher import SubstackFetcher
from parser import SubstackParser
from compiler import SubstackCompiler
from epub_tracker import EpubTracker

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
                    verify_fetcher = SubstackFetcher(url="https://substack.com", cookie=cookie)
                    if verify_fetcher.verify_auth():
                        st.success("✅ Session Valid: Logged in")
                    else:
                        st.error("❌ Session Invalid: Please check your cookie")
                except Exception as e:
                    st.error(f"Error checking status: {e}")

button_label = "Update EPUB" if mode == "Update Existing EPUB" else "Download & Compile"

if st.button(button_label):
    if not url:
        st.error("Please enter a valid URL.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                # 1. Fetch Metadata
                st.write("Fetching newsletter information...")
                fetcher = SubstackFetcher(url, cookie=cookie)
                newsletter_title = fetcher.get_newsletter_title()
                newsletter_author = fetcher.get_newsletter_author()

                # Generate filename from title (used for both modes)
                safe_title = "".join(c for c in newsletter_title if c.isalnum() or c in (' ', '_', '-')).strip()
                safe_title = safe_title.replace(" ", "_")
                epub_filename = f"{safe_title}.epub"
                epub_path = os.path.join("output", epub_filename)

                # Check update mode
                if mode == "Update Existing EPUB":
                    tracker = EpubTracker(epub_path)
                    if not tracker.exists():
                        st.error(f"No existing EPUB found at {epub_path}. Please create one first using 'Create New' mode.")
                        status.update(label="Failed", state="error")
                        st.stop()

                    st.write(f"Checking for new posts in **{newsletter_title}** by {newsletter_author}...")
                    all_metadata = fetcher.fetch_archive_metadata(limit=None)
                    metadata_list = tracker.get_new_posts(all_metadata)

                    if not metadata_list:
                        st.info("No new posts found! Your EPUB is up to date.")
                        status.update(label="Already up to date", state="complete")
                        st.stop()

                    st.write(f"Found **{len(metadata_list)} new post(s)** to add!")
                else:
                    # Create new mode
                    st.write("Fetching post list from Archive API...")
                    fetch_limit = None if limit == 0 else limit
                    metadata_list = fetcher.fetch_archive_metadata(limit=fetch_limit)

                    if not metadata_list:
                        st.error("No posts found. Please check the URL.")
                        status.update(label="Failed", state="error")
                        st.stop()

                    st.write(f"Found {len(metadata_list)} posts from **{newsletter_title}** by {newsletter_author}.")

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
                        'content': cleaned_content,
                        'link': meta['link']  # Store link for tracking
                    })

                    progress_bar.progress((i + 1) / len(metadata_list))
                    time.sleep(0.1) # Slight delay to be nice

                # 3. Compile
                if format_option in ["PDF", "EPUB"] or mode == "Update Existing EPUB":
                    st.write(f"Compiling EPUB (processing videos & images)...")
                else:
                    st.write(f"Compiling {format_option}...")
                compiler = SubstackCompiler(base_url=url)

                format_map = {
                    "PDF": "pdf",
                    "EPUB": "epub",
                    "JSON": "json",
                    "HTML": "html",
                    "TXT": "txt",
                    "Markdown": "md"
                }

                if mode == "Update Existing EPUB" or format_option == "EPUB":
                    # EPUB with metadata
                    file_ext = "epub"
                    filename = epub_filename
                    output_path = compiler.compile_to_epub(
                        cleaned_posts,
                        filename=filename,
                        title=newsletter_title,
                        author=newsletter_author,
                        update_existing=(mode == "Update Existing EPUB")
                    )
                    mime_type = "application/epub+zip"

                    # Update tracker with all post links
                    if mode == "Update Existing EPUB":
                        # Load existing tracker and append new links
                        tracker = EpubTracker(epub_path)
                        existing_data = tracker.load()
                        all_links = existing_data['post_links'] + [p['link'] for p in cleaned_posts]
                        tracker.save(newsletter_title, newsletter_author, url, all_links)
                    else:
                        # Create new tracker
                        tracker = EpubTracker(output_path)
                        tracker.save(newsletter_title, newsletter_author, url, [p['link'] for p in cleaned_posts])

                elif format_option == "PDF":
                    file_ext = "pdf"
                    filename = f"{safe_title}.{file_ext}"
                    output_path = compiler.compile_to_pdf(cleaned_posts, filename=filename)
                    mime_type = "application/pdf"
                elif format_option == "JSON":
                    file_ext = "json"
                    filename = f"{safe_title}.{file_ext}"
                    output_path = compiler.compile_to_json(cleaned_posts, filename=filename)
                    mime_type = "application/json"
                elif format_option == "HTML":
                    file_ext = "html"
                    filename = f"{safe_title}.{file_ext}"
                    output_path = compiler.compile_to_html(cleaned_posts, filename=filename)
                    mime_type = "text/html"
                elif format_option == "TXT":
                    file_ext = "txt"
                    filename = f"{safe_title}.{file_ext}"
                    output_path = compiler.compile_to_txt(cleaned_posts, filename=filename)
                    mime_type = "text/plain"
                elif format_option == "Markdown":
                    file_ext = "md"
                    filename = f"{safe_title}.{file_ext}"
                    output_path = compiler.compile_to_md(cleaned_posts, filename=filename)
                    mime_type = "text/markdown"

                # Success message
                if mode == "Update Existing EPUB":
                    status.update(label="Updated!", state="complete", expanded=False)
                    st.success(f"Successfully added {len(cleaned_posts)} new post(s) to {filename}!")
                else:
                    status.update(label="Done!", state="complete", expanded=False)
                    st.success(f"Successfully compiled {filename}!")

                # 4. Download Button
                with open(output_path, "rb") as f:
                    download_label = "Download Updated EPUB" if mode == "Update Existing EPUB" else f"Download {format_option}"
                    st.download_button(
                        label=download_label,
                        data=f,
                        file_name=filename,
                        mime=mime_type
                    )
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
                status.update(label="Error", state="error")

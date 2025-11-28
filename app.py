import streamlit as st
import os
import time
from fetcher import SubstackFetcher
from parser import SubstackParser
from compiler import SubstackCompiler

st.set_page_config(page_title="Substack Downloader", page_icon="📚")

st.title("📚 Substack Downloader")
st.markdown("Download posts from your favorite Substack newsletter and compile them into a PDF book.")

col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input("Enter Substack URL", placeholder="https://newsletter.pragmaticengineer.com")
with col2:
    limit = st.number_input("Limit (0 for all)", min_value=0, value=0, step=10)

if st.button("Download & Compile"):
    if not url:
        st.error("Please enter a valid URL.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                # 1. Fetch Metadata
                st.write("Fetching post list from Archive API...")
                fetcher = SubstackFetcher(url)
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
                    st.write("Compiling PDF...")
                    compiler = SubstackCompiler()
                    
                    # Generate filename from title
                    safe_title = "".join(c for c in newsletter_title if c.isalnum() or c in (' ', '_', '-')).strip()
                    safe_title = safe_title.replace(" ", "_")
                    filename = f"{safe_title}.pdf"
                    
                    pdf_path = compiler.compile_to_pdf(cleaned_posts, filename=filename)
                    
                    status.update(label="Done!", state="complete", expanded=False)
                    st.success(f"Successfully compiled {filename}!")
                    
                    # 4. Download Button
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="Download PDF",
                            data=f,
                            file_name=filename,
                            mime="application/pdf"
                        )
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
                status.update(label="Error", state="error")

import os
import json
import markdownify
import requests
import uuid
from datetime import datetime
from bs4 import BeautifulSoup
from fpdf import FPDF, HTMLMixin
from ebooklib import epub

class PDF(FPDF, HTMLMixin):
    pass

class SubstackCompiler:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.images_dir = os.path.join(self.output_dir, "images")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)

    def sanitize_text(self, text):
        """
        Replaces characters not supported by Latin-1 encoding.
        """
        replacements = {
            '\u2018': "'", '\u2019': "'",  # Smart quotes
            '\u201c': '"', '\u201d': '"',  # Smart double quotes
            '\u2013': '-', '\u2014': '-',  # Dashes
            '\u2026': '...',               # Ellipsis
            '\u00a0': ' ',                 # Non-breaking space
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        # Encode to latin-1 and decode back to ignore other errors
        return text.encode('latin-1', 'replace').decode('latin-1')

    def download_image(self, img_url):
        """
        Downloads an image and returns the local path.
        """
        filepath = None
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }

            response = requests.get(img_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            # Determine extension from Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'image/png' in content_type:
                ext = 'png'
            elif 'image/gif' in content_type:
                ext = 'gif'
            elif 'image/svg' in content_type:
                ext = 'svg'
            elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = 'jpg'
            else:
                # Fallback to URL or default
                if '.png' in img_url: ext = 'png'
                elif '.gif' in img_url: ext = 'gif'
                elif '.svg' in img_url: ext = 'svg'
                else: ext = 'jpg'

            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(self.images_dir, filename)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)

            return filepath, filename
        except requests.exceptions.Timeout:
            print(f"Timeout downloading image {img_url}")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except requests.exceptions.RequestException as e:
            print(f"Failed to download image {img_url}: {e}")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except IOError as e:
            print(f"Failed to write image {img_url}: {e} (disk full?)")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except Exception as e:
            print(f"Unexpected error downloading image {img_url}: {type(e).__name__}: {e}")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None

    def process_html_images(self, html_content, for_epub=False, epub_book=None, verbose=True):
        """
        Parses HTML, downloads images, and updates src attributes.
        For PDF: Updates src to absolute local path.
        For EPUB: Updates src to relative filename and adds image to book.

        Args:
            html_content: HTML string containing images
            for_epub: Whether processing for EPUB (vs PDF)
            epub_book: EpubBook object (required if for_epub=True)
            verbose: Print download progress

        Returns:
            HTML string with updated image src attributes
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')

        if not images:
            return str(soup)

        downloaded_count = 0
        failed_count = 0

        if verbose:
            print(f"  Found {len(images)} image(s) to download...")

        for img in images:
            src = img.get('src')
            if not src:
                continue

            # Skip data URIs (embedded images)
            if src.startswith('data:'):
                if verbose:
                    print(f"  Skipping embedded data URI image")
                continue

            if verbose:
                print(f"  Downloading: {src[:80]}...")

            local_path, filename = self.download_image(src)
            if local_path:
                downloaded_count += 1
                if for_epub and epub_book:
                    # Add image to EPUB
                    with open(local_path, 'rb') as f:
                        img_content = f.read()

                    epub_img = epub.EpubImage()
                    epub_img.uid = filename
                    epub_img.file_name = f"images/{filename}"

                    # Fix MIME types
                    ext = filename.split('.')[-1]
                    if ext == 'jpg':
                        media_type = 'image/jpeg'
                    elif ext == 'svg':
                        media_type = 'image/svg+xml'
                    else:
                        media_type = f"image/{ext}"

                    epub_img.media_type = media_type
                    epub_img.content = img_content
                    epub_book.add_item(epub_img)

                    # Update src to relative path in EPUB
                    img['src'] = f"images/{filename}"
                else:
                    # Update src to absolute local path for PDF
                    img['src'] = local_path

                # Clean up attributes: keep only src and alt
                # Substack includes many data attributes and classes that might confuse EPUB readers
                alt = img.get('alt', '')
                img.attrs = {
                    'src': img['src'],
                    'alt': alt
                }
            else:
                # Image download failed
                failed_count += 1
                if verbose:
                    print(f"  ⚠️  Failed to download image, keeping original URL")

        if verbose and (downloaded_count > 0 or failed_count > 0):
            print(f"  ✓ Downloaded {downloaded_count} image(s), {failed_count} failed")

        return str(soup)

    def process_html_videos(self, html_content, verbose=True):
        """
        Converts video embeds to clickable links since PDFs/EPUBs can't play videos.

        Handles:
        - <video> tags
        - <iframe> embeds (YouTube, Vimeo, etc.)
        - Substack video embeds

        Args:
            html_content: HTML string containing videos
            verbose: Print conversion progress

        Returns:
            HTML string with videos replaced by clickable links
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        video_count = 0

        # Find all video tags
        videos = soup.find_all('video')
        for video in videos:
            video_count += 1

            # Try to get video source
            video_url = None
            source = video.find('source')
            if source and source.get('src'):
                video_url = source.get('src')
            elif video.get('src'):
                video_url = video.get('src')

            if video_url:
                # Create clickable link to replace video
                link_text = f"🎬 Click to watch video"
                new_tag = soup.new_tag('p', style='background: #f0f0f0; padding: 10px; border-left: 4px solid #FF6B6B;')
                a_tag = soup.new_tag('a', href=video_url)
                a_tag.string = link_text
                new_tag.append(a_tag)
                new_tag.append(soup.new_string(f" ({video_url[:50]}...)"))
                video.replace_with(new_tag)

                if verbose:
                    print(f"  📹 Converted video to link: {video_url[:60]}...")
            else:
                # No URL found, just add a note
                note = soup.new_tag('p', style='background: #fff3cd; padding: 10px;')
                note.string = "📹 Video content (URL not available)"
                video.replace_with(note)

        # Find all iframe embeds (YouTube, Vimeo, etc.)
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if not src:
                continue

            # Check if it's a video embed
            video_platforms = ['youtube.com', 'youtube-nocookie.com', 'youtu.be', 'vimeo.com', 'wistia.com', 'loom.com', 'substack.com/embed']
            is_video = any(platform in src for platform in video_platforms)

            if is_video:
                video_count += 1

                # Extract clean URL
                video_url = src

                # For YouTube, convert embed URL to watch URL
                if 'youtube.com/embed/' in src or 'youtube-nocookie.com/embed/' in src:
                    # Extract video ID from either youtube.com or youtube-nocookie.com
                    if 'youtube-nocookie.com/embed/' in src:
                        video_id = src.split('youtube-nocookie.com/embed/')[-1].split('?')[0]
                    else:
                        video_id = src.split('youtube.com/embed/')[-1].split('?')[0]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                elif 'youtu.be/' in src:
                    video_url = src.replace('youtu.be/', 'youtube.com/watch?v=')

                # Determine platform name
                if 'youtube' in src or 'youtu.be' in src:
                    platform = "YouTube"
                elif 'vimeo' in src:
                    platform = "Vimeo"
                elif 'loom' in src:
                    platform = "Loom"
                elif 'wistia' in src:
                    platform = "Wistia"
                else:
                    platform = "Video"

                # Create clickable link
                link_text = f"🎬 Watch on {platform}"
                new_tag = soup.new_tag('p', style='background: #f0f0f0; padding: 10px; border-left: 4px solid #FF6B6B; margin: 10px 0;')
                a_tag = soup.new_tag('a', href=video_url, target='_blank')
                a_tag.string = link_text
                new_tag.append(a_tag)
                new_tag.append(soup.new_tag('br'))
                small = soup.new_tag('small', style='color: #666;')
                small.string = f"Link: {video_url[:70]}..."
                new_tag.append(small)
                iframe.replace_with(new_tag)

                if verbose:
                    print(f"  📹 Converted {platform} embed to link: {video_url[:60]}...")

        if verbose and video_count > 0:
            print(f"  ✓ Converted {video_count} video(s) to clickable links")

        return str(soup)

    def compile_to_pdf(self, posts, filename="substack_book.pdf"):
        """
        Compiles a list of posts into a single PDF file with a Table of Contents.
        """
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        filepath = os.path.join(self.output_dir, filename)
        
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Title
        pdf.set_font("Helvetica", size=24, style="B")
        pdf.cell(0, 20, "Substack Archive", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)

        # Table of Contents
        pdf.set_font("Helvetica", size=16, style="B")
        pdf.cell(0, 10, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=12)
        
        for post in posts:
            title = self.sanitize_text(post['title'])
            date_str = post['pub_date'].strftime("%Y-%m-%d")
            pdf.cell(0, 8, f"{date_str} - {title}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.add_page()

        # Content
        for post in posts:
            title = self.sanitize_text(post['title'])
            date_str = post['pub_date'].strftime("%B %d, %Y")
            content = post['content']
            
            # Process videos (convert to clickable links)
            content = self.process_html_videos(content)

            # Process images for PDF
            content = self.process_html_images(content, for_epub=False)

            # Post Header
            pdf.set_font("Helvetica", size=18, style="B")
            pdf.multi_cell(0, 10, title)
            pdf.set_font("Helvetica", size=10, style="I")
            pdf.cell(0, 10, date_str, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            
            # Post Content
            try:
                content = self.sanitize_text(content)
                pdf.write_html(content)
            except Exception as e:
                print(f"Warning: Could not render HTML for post '{title}': {e}")
                pdf.set_font("Helvetica", size=12)
                pdf.multi_cell(0, 5, "(Content could not be rendered due to complex HTML formatting)")
            
            pdf.add_page()

        print(f"Generating PDF: {filepath}...")
        pdf.output(filepath)
        return filepath

    def compile_to_epub(self, posts, filename="substack_book.epub"):
        if not filename.endswith('.epub'):
            filename += '.epub'
        filepath = os.path.join(self.output_dir, filename)

        book = epub.EpubBook()
        book.set_identifier('id123456')
        book.set_title('Substack Archive')
        book.set_language('en')

        # Create chapters
        chapters = []
        for i, post in enumerate(posts):
            title = post['title']
            date_str = post['pub_date'].strftime("%B %d, %Y")
            
            # Process videos and images for EPUB
            content = post['content']
            content = self.process_html_videos(content)
            content = self.process_html_images(content, for_epub=True, epub_book=book)

            full_content = f"<h1>{title}</h1><p><i>{date_str}</i></p>{content}"

            chapter = epub.EpubHtml(title=title, file_name=f'chap_{i+1}.xhtml', lang='en')
            chapter.content = full_content
            book.add_item(chapter)
            chapters.append(chapter)

        # Define Table of Contents
        book.toc = (epub.Link('intro.xhtml', 'Introduction', 'intro'),
                    (epub.Section('Posts'), chapters))

        # Add default NCX and Nav file
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Define CSS style
        style = 'body { font-family: Times, serif; } img { max-width: 100%; }'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)

        # Basic spine
        book.spine = ['nav'] + chapters

        epub.write_epub(filepath, book, {})
        print(f"Generating EPUB: {filepath}...")
        return filepath

    def compile_to_json(self, posts, filename="substack_book.json"):
        if not filename.endswith('.json'):
            filename += '.json'
        filepath = os.path.join(self.output_dir, filename)

        # Convert datetime objects to string
        serializable_posts = []
        for post in posts:
            p = post.copy()
            p['pub_date'] = p['pub_date'].isoformat()
            serializable_posts.append(p)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_posts, f, indent=4, ensure_ascii=False)
        
        print(f"Generating JSON: {filepath}...")
        return filepath

    def compile_to_html(self, posts, filename="substack_book.html"):
        if not filename.endswith('.html'):
            filename += '.html'
        filepath = os.path.join(self.output_dir, filename)

        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Substack Archive</title>
            <style>
                body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                article { margin-bottom: 50px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }
                h1 { color: #333; }
                .meta { color: #666; font-style: italic; }
                img { max-width: 100%; height: auto; }
            </style>
        </head>
        <body>
            <h1>Substack Archive</h1>
        """

        for post in posts:
            title = post['title']
            date_str = post['pub_date'].strftime("%B %d, %Y")
            content = post['content']
            
            # For HTML output, we could also download images, but linking to remote is usually fine for HTML.
            # However, if we want a self-contained offline HTML, we should download.
            # Let's stick to remote for HTML to keep it simple, or use the same logic if requested.
            # The prompt asked for "downloads aren't pulling down pictures", implying offline access.
            # Let's use the process_html_images for HTML too, but maybe just use relative paths?
            # Actually, let's keep HTML simple for now as the user complained about "downloads" which usually implies PDF/EPUB.
            
            html_content += f"""
            <article>
                <h2>{title}</h2>
                <p class="meta">{date_str}</p>
                <div>{content}</div>
            </article>
            """

        html_content += "</body></html>"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Generating HTML: {filepath}...")
        return filepath

    def compile_to_txt(self, posts, filename="substack_book.txt"):
        if not filename.endswith('.txt'):
            filename += '.txt'
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            for post in posts:
                title = post['title']
                date_str = post['pub_date'].strftime("%B %d, %Y")
                text_content = markdownify.markdownify(post['content'], strip=['a', 'img'])
                
                f.write(f"{title}\n")
                f.write(f"{date_str}\n")
                f.write("="*len(title) + "\n\n")
                f.write(text_content)
                f.write("\n\n" + "-"*50 + "\n\n")

        print(f"Generating TXT: {filepath}...")
        return filepath

    def compile_to_md(self, posts, filename="substack_book.md"):
        if not filename.endswith('.md'):
            filename += '.md'
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Substack Archive\n\n")
            for post in posts:
                title = post['title']
                date_str = post['pub_date'].strftime("%B %d, %Y")
                md_content = markdownify.markdownify(post['content'])
                
                f.write(f"## {title}\n")
                f.write(f"*{date_str}*\n\n")
                f.write(md_content)
                f.write("\n\n---\n\n")

        print(f"Generating Markdown: {filepath}...")
        return filepath

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
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }
            
            response = requests.get(img_url, headers=headers, stream=True)
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
                    f.write(chunk)
            
            return filepath, filename
        except Exception as e:
            print(f"Failed to download image {img_url}: {e}")
            return None, None

    def process_html_images(self, html_content, for_epub=False, epub_book=None):
        """
        Parses HTML, downloads images, and updates src attributes.
        For PDF: Updates src to absolute local path.
        For EPUB: Updates src to relative filename and adds image to book.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        
        for img in images:
            src = img.get('src')
            if not src:
                continue
                
            local_path, filename = self.download_image(src)
            if local_path:
                if for_epub and epub_book:
                    # Add image to EPUB
                    with open(local_path, 'rb') as f:
                        img_content = f.read()
                    
                    epub_img = epub.EpubImage()
                    epub_img.uid = filename
                    epub_img.file_name = f"images/{filename}"
                    epub_img.media_type = f"image/{filename.split('.')[-1]}"
                    epub_img.content = img_content
                    epub_book.add_item(epub_img)
                    
                    # Update src to relative path in EPUB
                    img['src'] = f"images/{filename}"
                else:
                    # Update src to absolute local path for PDF
                    img['src'] = local_path
                    
                # Remove srcset and other attributes that might confuse renderers
                if img.has_attr('srcset'): del img['srcset']
                if img.has_attr('loading'): del img['loading']
                
                # Ensure width/height don't break layout (optional, but good for PDF)
                # img['width'] = "100%" # FPDF2 doesn't like percentage width in HTML attributes sometimes
                if img.has_attr('width'): del img['width']
                if img.has_attr('height'): del img['height']
                
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
            
            # Process images for EPUB
            content = post['content']
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

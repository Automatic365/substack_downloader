"""Compiler package facade."""
import os

from config import OUTPUT_DIR
from compiler.formats import EPUBFormatter, HTMLFormatter, PDFFormatter, TextFormatter
from compiler.media import MediaProcessor
from compiler.utils import sanitize_text


class SubstackCompiler:
    def __init__(self, output_dir=None, base_url=None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.images_dir = os.path.join(self.output_dir, "images")
        self.base_url = base_url

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)

        self.media_processor = MediaProcessor(self.images_dir, base_url=self.base_url)

        self.pdf_formatter = PDFFormatter(self.media_processor, output_dir=self.output_dir)
        self.epub_formatter = EPUBFormatter(self.media_processor, output_dir=self.output_dir, base_url=self.base_url)
        self.html_formatter = HTMLFormatter(output_dir=self.output_dir)
        self.text_formatter = TextFormatter(output_dir=self.output_dir)

    def sanitize_text(self, text):
        return sanitize_text(text)

    def download_image(self, img_url):
        return self.media_processor.download_image(img_url)

    def process_html_images(self, html_content, for_epub=False, epub_book=None, verbose=True):
        return self.media_processor.process_html_images(
            html_content,
            for_epub=for_epub,
            epub_book=epub_book,
            verbose=verbose,
        )

    def process_html_videos(self, html_content, verbose=True, base_url=None):
        return self.media_processor.process_html_videos(
            html_content,
            verbose=verbose,
            base_url=base_url,
        )

    def compile_to_pdf(self, posts, filename="substack_book.pdf"):
        return self.pdf_formatter.compile(posts, filename=filename)

    def compile_to_epub(
        self,
        posts,
        filename="substack_book.epub",
        title="Substack Archive",
        author="Unknown Author",
        update_existing=False,
    ):
        return self.epub_formatter.compile(
            posts,
            filename=filename,
            title=title,
            author=author,
            update_existing=update_existing,
        )

    def compile_to_json(self, posts, filename="substack_book.json"):
        return self.text_formatter.compile_json(posts, filename=filename)

    def compile_to_html(self, posts, filename="substack_book.html"):
        return self.html_formatter.compile(posts, filename=filename)

    def compile_to_txt(self, posts, filename="substack_book.txt"):
        return self.text_formatter.compile_txt(posts, filename=filename)

    def compile_to_md(self, posts, filename="substack_book.md"):
        return self.text_formatter.compile_md(posts, filename=filename)

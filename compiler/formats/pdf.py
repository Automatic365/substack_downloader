"""PDF formatting for Substack posts."""
import os

from fpdf import FPDF, HTMLMixin

from logger import setup_logger
from compiler.utils import sanitize_text, normalize_posts

logger = setup_logger(__name__)


class PDF(FPDF, HTMLMixin):
    pass


class PDFFormatter:
    def __init__(self, media_processor, output_dir="output"):
        self.media_processor = media_processor
        self.output_dir = output_dir

    def compile(self, posts, filename="substack_book.pdf"):
        normalized_posts = normalize_posts(posts)
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        filepath = os.path.join(self.output_dir, filename)

        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font("Helvetica", size=24, style="B")
        pdf.cell(0, 20, "Substack Archive", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)

        pdf.set_font("Helvetica", size=16, style="B")
        pdf.cell(0, 10, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=12)

        for post in normalized_posts:
            title = sanitize_text(post['title'])
            date_str = post['pub_date'].strftime("%Y-%m-%d")
            pdf.cell(0, 8, f"{date_str} - {title}", new_x="LMARGIN", new_y="NEXT")

        pdf.add_page()

        for post in normalized_posts:
            title = sanitize_text(post['title'])
            date_str = post['pub_date'].strftime("%B %d, %Y")
            content = post['content']

            content = self.media_processor.process_html_videos(content)
            content = self.media_processor.process_html_images(content, for_epub=False)

            pdf.set_font("Helvetica", size=18, style="B")
            pdf.multi_cell(0, 10, title)
            pdf.set_font("Helvetica", size=10, style="I")
            pdf.cell(0, 10, date_str, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            try:
                content = sanitize_text(content)
                pdf.write_html(content)
            except Exception as exc:
                logger.warning("Could not render HTML for post '%s': %s", title, exc)
                pdf.set_font("Helvetica", size=12)
                pdf.multi_cell(0, 5, "(Content could not be rendered due to complex HTML formatting)")

            pdf.add_page()

        logger.info("Generating PDF: %s", filepath)
        pdf.output(filepath)
        return filepath

import os
from datetime import datetime
from fpdf import FPDF, HTMLMixin

class PDF(FPDF, HTMLMixin):
    pass

class SubstackCompiler:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

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

    def compile_to_pdf(self, posts, filename="substack_book.pdf"):
        """
        Compiles a list of posts into a single PDF file with a Table of Contents.
        Using FPDF2 for pure Python PDF generation.
        """
        # Ensure filename ends with .pdf
        if not filename.endswith('.pdf'):
            filename = filename.replace('.html', '') + '.pdf'

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
            content = post['content'] # Content is HTML, handled by write_html
            
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
            
        print(f"Successfully compiled {len(posts)} posts to {filepath}")
        return filepath

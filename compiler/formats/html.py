"""HTML formatting for Substack posts."""
import os

from compiler.utils import normalize_posts
from logger import setup_logger

logger = setup_logger(__name__)


class HTMLFormatter:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def compile(self, posts, filename="substack_book.html"):
        normalized_posts = normalize_posts(posts)
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

        for post in normalized_posts:
            title = post['title']
            date_str = post['pub_date'].strftime("%B %d, %Y")
            content = post['content']

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

        logger.info("Generating HTML: %s", filepath)
        return filepath

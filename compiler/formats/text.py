"""Text-based formatters for Substack posts."""
import json
import os

import markdownify

from compiler.utils import normalize_posts
from logger import setup_logger

logger = setup_logger(__name__)


class TextFormatter:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def compile_json(self, posts, filename="substack_book.json"):
        normalized_posts = normalize_posts(posts)
        if not filename.endswith('.json'):
            filename += '.json'
        filepath = os.path.join(self.output_dir, filename)

        serializable_posts = []
        for post in normalized_posts:
            p = post.copy()
            p['pub_date'] = p['pub_date'].isoformat()
            serializable_posts.append(p)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_posts, f, indent=4, ensure_ascii=False)

        logger.info("Generating JSON: %s", filepath)
        return filepath

    def compile_txt(self, posts, filename="substack_book.txt"):
        normalized_posts = normalize_posts(posts)
        if not filename.endswith('.txt'):
            filename += '.txt'
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            for post in normalized_posts:
                title = post['title']
                date_str = post['pub_date'].strftime("%B %d, %Y")
                text_content = markdownify.markdownify(post['content'], strip=['a', 'img'])

                f.write(f"{title}\n")
                f.write(f"{date_str}\n")
                f.write("=" * len(title) + "\n\n")
                f.write(text_content)
                f.write("\n\n" + "-" * 50 + "\n\n")

        logger.info("Generating TXT: %s", filepath)
        return filepath

    def compile_md(self, posts, filename="substack_book.md"):
        normalized_posts = normalize_posts(posts)
        if not filename.endswith('.md'):
            filename += '.md'
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Substack Archive\n\n")
            for post in normalized_posts:
                title = post['title']
                date_str = post['pub_date'].strftime("%B %d, %Y")
                md_content = markdownify.markdownify(post['content'])

                f.write(f"## {title}\n")
                f.write(f"*{date_str}*\n\n")
                f.write(md_content)
                f.write("\n\n---\n\n")

        logger.info("Generating Markdown: %s", filepath)
        return filepath

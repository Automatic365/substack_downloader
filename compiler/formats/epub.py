"""EPUB formatting for Substack posts."""
import os

from ebooklib import epub

from logger import setup_logger
from compiler.utils import normalize_posts

logger = setup_logger(__name__)


class EPUBFormatter:
    def __init__(self, media_processor, output_dir="output", base_url=None):
        self.media_processor = media_processor
        self.output_dir = output_dir
        self.base_url = base_url

    def compile(self, posts, filename="substack_book.epub", title="Substack Archive", author="Unknown Author", update_existing=False):
        normalized_posts = normalize_posts(posts)
        if not filename.endswith('.epub'):
            filename += '.epub'
        filepath = os.path.join(self.output_dir, filename)

        if update_existing and os.path.exists(filepath):
            logger.info("Loading existing EPUB: %s", filepath)
            book = epub.read_epub(filepath)

            existing_chapters = [
                item for item in book.get_items()
                if isinstance(item, epub.EpubHtml) and item.file_name.startswith('chap_')
            ]
            next_chapter_num = len(existing_chapters) + 1
            logger.info(
                "Found %s existing chapter(s), starting from chapter %s",
                len(existing_chapters),
                next_chapter_num,
            )
        else:
            logger.info("Creating new EPUB: %s", filepath)
            book = epub.EpubBook()
            book_id = f"substack-{title.replace(' ', '-').lower()}"
            book.set_identifier(book_id)
            book.set_title(title)
            book.set_language('en')
            book.add_author(author)

            existing_chapters = []
            next_chapter_num = 1

        new_chapters = []
        for i, post in enumerate(normalized_posts):
            post_title = post['title']
            date_str = post['pub_date'].strftime("%B %d, %Y")

            content = post['content']
            content = self.media_processor.process_html_videos(content, base_url=self.base_url)
            content = self.media_processor.process_html_images(content, for_epub=True, epub_book=book)

            full_content = f"<h1>{post_title}</h1><p><i>{date_str}</i></p>{content}"

            chapter = epub.EpubHtml(
                title=post_title,
                file_name=f'chap_{next_chapter_num + i}.xhtml',
                lang='en',
            )
            chapter.content = full_content
            book.add_item(chapter)
            new_chapters.append(chapter)

        all_chapters = existing_chapters + new_chapters

        book.toc = (
            epub.Link('intro.xhtml', 'Introduction', 'intro'),
            (epub.Section('Posts'), all_chapters),
        )

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        style = 'body { font-family: Times, serif; } img { max-width: 100%; }'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)

        book.spine = ['nav'] + all_chapters

        epub.write_epub(filepath, book, {})
        if update_existing:
            logger.info("Updated EPUB with %s new chapter(s): %s", len(new_chapters), filepath)
        else:
            logger.info("Generated EPUB with %s chapter(s): %s", len(all_chapters), filepath)
        return filepath

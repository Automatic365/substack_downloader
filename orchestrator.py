"""Orchestration logic for downloading and compiling Substack posts."""
from dataclasses import dataclass
import os
from typing import Callable, List, Optional

from compiler import SubstackCompiler
from config import OUTPUT_DIR
from epub_tracker import EpubTracker
from fetcher import SubstackFetcher
from logger import setup_logger
from parser import parse_content
from utils import sanitize_filename

logger = setup_logger(__name__)


StatusCallback = Optional[Callable[[str], None]]
ProgressCallback = Optional[Callable[[int, int, str], None]]


@dataclass
class OrchestratorResult:
    status: str
    message: str
    output_path: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    cleaned_posts: Optional[List] = None
    newsletter_title: Optional[str] = None
    newsletter_author: Optional[str] = None


def _notify_status(callback: StatusCallback, message: str) -> None:
    if callback:
        callback(message)


def _notify_progress(callback: ProgressCallback, current: int, total: int, title: str) -> None:
    if callback:
        callback(current, total, title)


def run_download(
    url: str,
    cookie: Optional[str],
    mode: str,
    limit: int,
    format_option: str,
    use_cache: bool = False,
    status_callback: StatusCallback = None,
    progress_callback: ProgressCallback = None,
) -> OrchestratorResult:
    fetcher = SubstackFetcher(url, cookie=cookie, enable_cache=use_cache)

    _notify_status(status_callback, "Fetching newsletter information...")
    newsletter_title = fetcher.get_newsletter_title()
    newsletter_author = fetcher.get_newsletter_author()

    safe_title = sanitize_filename(newsletter_title).replace(" ", "_")
    epub_filename = f"{safe_title}.epub"
    epub_path = os.path.join(OUTPUT_DIR, epub_filename)

    if mode == "Update Existing EPUB":
        tracker = EpubTracker(epub_path)
        if not tracker.exists():
            return OrchestratorResult(
                status="missing_epub",
                message=f"No existing EPUB found at {epub_path}. Please create one first using 'Create New' mode.",
                newsletter_title=newsletter_title,
                newsletter_author=newsletter_author,
            )

        _notify_status(status_callback, f"Checking for new posts in {newsletter_title}...")
        all_metadata = fetcher.fetch_archive_metadata(limit=None)
        metadata_list = tracker.get_new_posts(all_metadata)

        if not metadata_list:
            return OrchestratorResult(
                status="no_new_posts",
                message="No new posts found! Your EPUB is up to date.",
                newsletter_title=newsletter_title,
                newsletter_author=newsletter_author,
            )
    else:
        _notify_status(status_callback, "Fetching post list from Archive API...")
        fetch_limit = None if limit == 0 else limit
        metadata_list = fetcher.fetch_archive_metadata(limit=fetch_limit)

        if not metadata_list:
            return OrchestratorResult(
                status="no_posts",
                message="No posts found. Please check the URL.",
                newsletter_title=newsletter_title,
                newsletter_author=newsletter_author,
            )

    _notify_status(status_callback, "Downloading and cleaning content (this may take a while)...")
    cleaned_posts = []

    total = len(metadata_list)
    for i, meta in enumerate(metadata_list):
        _notify_progress(progress_callback, i + 1, total, meta.title)
        content = fetcher.fetch_post_content(meta.link)
        meta.content = parse_content(content)
        cleaned_posts.append(meta)

    compiler = SubstackCompiler(base_url=url)
    format_map = {
        "PDF": ("pdf", "application/pdf"),
        "EPUB": ("epub", "application/epub+zip"),
        "JSON": ("json", "application/json"),
        "HTML": ("html", "text/html"),
        "TXT": ("txt", "text/plain"),
        "Markdown": ("md", "text/markdown"),
    }

    if mode == "Update Existing EPUB" or format_option == "EPUB":
        file_ext, mime_type = format_map["EPUB"]
        filename = epub_filename
        output_path = compiler.compile_to_epub(
            cleaned_posts,
            filename=filename,
            title=newsletter_title,
            author=newsletter_author,
            update_existing=(mode == "Update Existing EPUB"),
        )

        tracker = EpubTracker(output_path)
        if mode == "Update Existing EPUB":
            existing_data = tracker.load()
            all_links = existing_data['post_links'] + [p.link for p in cleaned_posts]
            tracker.save(newsletter_title, newsletter_author, url, all_links)
        else:
            tracker.save(newsletter_title, newsletter_author, url, [p.link for p in cleaned_posts])
    else:
        file_ext, mime_type = format_map[format_option]
        filename = f"{safe_title}.{file_ext}"
        if format_option == "PDF":
            output_path = compiler.compile_to_pdf(cleaned_posts, filename=filename)
        elif format_option == "JSON":
            output_path = compiler.compile_to_json(cleaned_posts, filename=filename)
        elif format_option == "HTML":
            output_path = compiler.compile_to_html(cleaned_posts, filename=filename)
        elif format_option == "TXT":
            output_path = compiler.compile_to_txt(cleaned_posts, filename=filename)
        else:
            output_path = compiler.compile_to_md(cleaned_posts, filename=filename)

    return OrchestratorResult(
        status="ok",
        message="Success",
        output_path=output_path,
        filename=filename,
        mime_type=mime_type,
        cleaned_posts=cleaned_posts,
        newsletter_title=newsletter_title,
        newsletter_author=newsletter_author,
    )

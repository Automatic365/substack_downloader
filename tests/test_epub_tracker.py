import json
import os
import tempfile

from epub_tracker import EpubTracker


def test_tracker_load_missing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = os.path.join(tmpdir, "book.epub")
        tracker = EpubTracker(epub_path)
        data = tracker.load()

        assert data["post_links"] == []
        assert data["last_updated"] is None


def test_tracker_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = os.path.join(tmpdir, "book.epub")
        tracker = EpubTracker(epub_path)

        tracker.save("Title", "Author", "https://example.com", ["a", "b"])
        data = tracker.load()

        assert data["title"] == "Title"
        assert data["author"] == "Author"
        assert data["url"] == "https://example.com"
        assert data["post_links"] == ["a", "b"]
        assert data["last_updated"] is not None


def test_tracker_get_new_posts_handles_dicts_and_objects():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = os.path.join(tmpdir, "book.epub")
        tracker = EpubTracker(epub_path)
        tracker.save("Title", "Author", "https://example.com", ["existing"])

        class DummyPost:
            def __init__(self, link):
                self.link = link

        posts = [
            {"link": "existing"},
            {"link": "new"},
            DummyPost("newer"),
        ]

        new_posts = tracker.get_new_posts(posts)
        assert len(new_posts) == 2


def test_tracker_exists_requires_epub_and_tracker():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = os.path.join(tmpdir, "book.epub")
        tracker = EpubTracker(epub_path)

        assert tracker.exists() is False

        with open(epub_path, "wb") as f:
            f.write(b"stub")
        assert tracker.exists() is False

        tracker.save("Title", "Author", "https://example.com", [])
        assert tracker.exists() is True


def test_tracker_load_handles_bad_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = os.path.join(tmpdir, "book.epub")
        tracker = EpubTracker(epub_path)
        with open(tracker.tracker_path, "w", encoding="utf-8") as f:
            f.write("not json")

        data = tracker.load()
        assert data["post_links"] == []

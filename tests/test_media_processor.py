import os
import tempfile
import requests
import requests_mock

from compiler.media import MediaProcessor


def test_process_html_videos_relative_url_uses_base():
    html = """
    <div>
        <video>
            <source src="/api/v1/video/abc" />
        </video>
    </div>
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        media = MediaProcessor(images_dir=tmpdir, base_url="https://example.substack.com")
        result = media.process_html_videos(html, base_url=None)
        assert "https://example.substack.com/api/v1/video/abc" in result


def test_process_html_videos_youtube_iframe():
    html = """
    <iframe src="https://www.youtube.com/embed/abcd1234"></iframe>
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        media = MediaProcessor(images_dir=tmpdir)
        result = media.process_html_videos(html)
        assert "youtube.com/watch?v=abcd1234" in result


def test_download_image_skips_oversize_content_length():
    with tempfile.TemporaryDirectory() as tmpdir:
        media = MediaProcessor(images_dir=tmpdir)
        with requests_mock.Mocker() as m:
            m.get(
                "https://example.com/large.png",
                content=b"data",
                headers={"Content-Length": str(20 * 1024 * 1024), "Content-Type": "image/png"},
            )
            path, filename = media.download_image("https://example.com/large.png")
            assert path is None
            assert filename is None


    def test_download_image_aborts_large_stream():
        with tempfile.TemporaryDirectory() as tmpdir:
            media = MediaProcessor(images_dir=tmpdir)

        class Response:
            headers = {"Content-Type": "image/png"}

            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size=8192):
                yield b"a" * (6 * 1024 * 1024)
                yield b"b" * (6 * 1024 * 1024)

        def fake_get(*args, **kwargs):
            return Response()

        original_get = requests.get
        requests.get = fake_get
        try:
            path, filename = media.download_image("https://example.com/stream.png")
            assert path is None
            assert filename is None
        finally:
            requests.get = original_get


def test_process_html_images_keeps_original_on_failure():
    html = """
    <div>
        <img src="https://example.com/missing.png" />
    </div>
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        media = MediaProcessor(images_dir=tmpdir)
        with requests_mock.Mocker() as m:
            m.get("https://example.com/missing.png", status_code=404)
            result = media.process_html_images(html, for_epub=False, verbose=False)
            assert "https://example.com/missing.png" in result

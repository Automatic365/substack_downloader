import pytest
import os
import json
import tempfile
import shutil
import requests
import requests_mock
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from compiler import SubstackCompiler


class TestSubstackCompilerInit:
    """Tests for SubstackCompiler initialization"""

    def test_init_creates_output_directory(self):
        """Test that output directory is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "test_output")
            compiler = SubstackCompiler(output_dir=output_dir)

            assert os.path.exists(output_dir)
            assert compiler.output_dir == output_dir

    def test_init_creates_images_directory(self):
        """Test that images directory is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "test_output")
            compiler = SubstackCompiler(output_dir=output_dir)

            images_dir = os.path.join(output_dir, "images")
            assert os.path.exists(images_dir)
            assert compiler.images_dir == images_dir

    def test_init_default_output_directory(self):
        """Test default output directory name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                compiler = SubstackCompiler()
                assert compiler.output_dir == "output"
            finally:
                os.chdir(original_cwd)


class TestSanitizeText:
    """Tests for sanitize_text method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    def test_sanitize_smart_single_quotes(self, compiler):
        """Test conversion of smart single quotes"""
        text = "It\u2018s a test\u2019"
        result = compiler.sanitize_text(text)
        assert result == "It's a test'"

    def test_sanitize_smart_double_quotes(self, compiler):
        """Test conversion of smart double quotes"""
        text = '\u201cHello World\u201d'
        result = compiler.sanitize_text(text)
        assert result == '"Hello World"'

    def test_sanitize_em_dash(self, compiler):
        """Test conversion of em dash"""
        text = "Test\u2014text"
        result = compiler.sanitize_text(text)
        assert result == "Test-text"

    def test_sanitize_en_dash(self, compiler):
        """Test conversion of en dash"""
        text = "Test\u2013text"
        result = compiler.sanitize_text(text)
        assert result == "Test-text"

    def test_sanitize_ellipsis(self, compiler):
        """Test conversion of ellipsis"""
        text = "Wait\u2026"
        result = compiler.sanitize_text(text)
        assert result == "Wait..."

    def test_sanitize_non_breaking_space(self, compiler):
        """Test conversion of non-breaking space"""
        text = "Hello\u00a0World"
        result = compiler.sanitize_text(text)
        assert result == "Hello World"

    def test_sanitize_multiple_replacements(self, compiler):
        """Test multiple character replacements in one string"""
        text = "\u201cIt\u2018s great\u2019\u201d\u2014really\u2026"
        result = compiler.sanitize_text(text)
        assert result == '"It\'s great\'"-really...'

    def test_sanitize_regular_text_unchanged(self, compiler):
        """Test that regular ASCII text is unchanged"""
        text = "Regular text with no special characters"
        result = compiler.sanitize_text(text)
        assert result == text


class TestDownloadImage:
    """Tests for download_image method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    def test_download_image_png(self, compiler):
        """Test downloading PNG image"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image.png',
                  content=b'fake image data',
                  headers={'Content-Type': 'image/png'})

            local_path, filename = compiler.download_image('https://example.com/image.png')

            assert local_path is not None
            assert filename.endswith('.png')
            assert os.path.exists(local_path)
            with open(local_path, 'rb') as f:
                assert f.read() == b'fake image data'

    def test_download_image_jpg(self, compiler):
        """Test downloading JPG image"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image.jpg',
                  content=b'fake jpg data',
                  headers={'Content-Type': 'image/jpeg'})

            local_path, filename = compiler.download_image('https://example.com/image.jpg')

            assert local_path is not None
            assert filename.endswith('.jpg')
            assert os.path.exists(local_path)

    def test_download_image_gif(self, compiler):
        """Test downloading GIF image"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image.gif',
                  content=b'fake gif data',
                  headers={'Content-Type': 'image/gif'})

            local_path, filename = compiler.download_image('https://example.com/image.gif')

            assert local_path is not None
            assert filename.endswith('.gif')

    def test_download_image_svg(self, compiler):
        """Test downloading SVG image"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image.svg',
                  content=b'<svg></svg>',
                  headers={'Content-Type': 'image/svg+xml'})

            local_path, filename = compiler.download_image('https://example.com/image.svg')

            assert local_path is not None
            assert filename.endswith('.svg')

    def test_download_image_fallback_to_url_extension(self, compiler):
        """Test fallback to URL extension when Content-Type is missing"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/photo.png',
                  content=b'image data',
                  headers={'Content-Type': 'application/octet-stream'})

            local_path, filename = compiler.download_image('https://example.com/photo.png')

            assert local_path is not None
            assert filename.endswith('.png')

    def test_download_image_default_jpg_extension(self, compiler):
        """Test default to .jpg when no Content-Type or extension"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image123',
                  content=b'image data',
                  headers={})

            local_path, filename = compiler.download_image('https://example.com/image123')

            assert local_path is not None
            assert filename.endswith('.jpg')

    def test_download_image_network_error(self, compiler):
        """Test handling network error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image.png',
                  exc=requests.exceptions.ConnectionError)

            local_path, filename = compiler.download_image('https://example.com/image.png')

            assert local_path is None
            assert filename is None

    def test_download_image_404_error(self, compiler):
        """Test handling 404 error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/missing.png', status_code=404)

            local_path, filename = compiler.download_image('https://example.com/missing.png')

            assert local_path is None
            assert filename is None

    def test_download_image_unique_filenames(self, compiler):
        """Test that downloaded images get unique filenames"""
        with requests_mock.Mocker() as m:
            m.get('https://example.com/image.png',
                  content=b'image data',
                  headers={'Content-Type': 'image/png'})

            path1, filename1 = compiler.download_image('https://example.com/image.png')
            path2, filename2 = compiler.download_image('https://example.com/image.png')

            assert filename1 != filename2  # UUID should make them unique
            assert os.path.exists(path1)
            assert os.path.exists(path2)


class TestProcessHtmlImages:
    """Tests for process_html_images method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    def test_process_html_no_images(self, compiler):
        """Test processing HTML with no images"""
        html = '<div><p>No images here</p></div>'
        result = compiler.process_html_images(html)

        assert 'No images here' in result
        assert '<img' not in result

    def test_process_html_with_image_for_pdf(self, compiler):
        """Test processing HTML with image for PDF"""
        html = '<div><img src="https://example.com/test.png" alt="test"></div>'

        with requests_mock.Mocker() as m:
            m.get('https://example.com/test.png',
                  content=b'image data',
                  headers={'Content-Type': 'image/png'})

            result = compiler.process_html_images(html, for_epub=False)

            assert '<img' in result
            # Should have absolute path to local file
            assert compiler.images_dir in result
            assert '.png' in result

    def test_process_html_image_without_src(self, compiler):
        """Test handling image tag without src attribute"""
        html = '<div><img alt="no source"></div>'
        result = compiler.process_html_images(html)

        # Should not crash, just skip the image
        assert '<img' in result

    def test_process_html_failed_image_download(self, compiler):
        """Test handling failed image download"""
        html = '<div><img src="https://example.com/missing.png"></div>'

        with requests_mock.Mocker() as m:
            m.get('https://example.com/missing.png', status_code=404)

            result = compiler.process_html_images(html)

            # Should still return HTML, just with original src
            assert '<img' in result

    def test_process_html_multiple_images(self, compiler):
        """Test processing multiple images"""
        html = '''<div>
            <img src="https://example.com/img1.png">
            <img src="https://example.com/img2.jpg">
        </div>'''

        with requests_mock.Mocker() as m:
            m.get('https://example.com/img1.png',
                  content=b'image1',
                  headers={'Content-Type': 'image/png'})
            m.get('https://example.com/img2.jpg',
                  content=b'image2',
                  headers={'Content-Type': 'image/jpeg'})

            result = compiler.process_html_images(html)

            # Should have updated both images
            assert result.count('<img') == 2
            assert '.png' in result
            assert '.jpg' in result


class TestCompileToJson:
    """Tests for compile_to_json method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    @pytest.fixture
    def sample_posts(self):
        return [
            {
                'title': 'Post 1',
                'link': 'https://example.com/p/post-1',
                'pub_date': datetime(2024, 1, 1),
                'description': 'First post',
                'content': '<p>Content 1</p>'
            },
            {
                'title': 'Post 2',
                'link': 'https://example.com/p/post-2',
                'pub_date': datetime(2024, 1, 2),
                'description': 'Second post',
                'content': '<p>Content 2</p>'
            }
        ]

    def test_compile_to_json_creates_file(self, compiler, sample_posts):
        """Test that JSON file is created"""
        filename = 'test.json'
        compiler.compile_to_json(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        assert os.path.exists(filepath)

    def test_compile_to_json_content(self, compiler, sample_posts):
        """Test JSON file content"""
        filename = 'test.json'
        compiler.compile_to_json(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]['title'] == 'Post 1'
        assert data[1]['title'] == 'Post 2'

    def test_compile_to_json_datetime_serialization(self, compiler, sample_posts):
        """Test that datetime objects are serialized"""
        filename = 'test.json'
        compiler.compile_to_json(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Datetime should be converted to string
        assert isinstance(data[0]['pub_date'], str)
        assert '2024-01-01' in data[0]['pub_date']

    def test_compile_to_json_empty_posts(self, compiler):
        """Test compiling empty post list"""
        filename = 'empty.json'
        compiler.compile_to_json([], filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)

        assert data == []


class TestCompileToHtml:
    """Tests for compile_to_html method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    @pytest.fixture
    def sample_posts(self):
        return [
            {
                'title': 'First Post',
                'link': 'https://example.com/p/first',
                'pub_date': datetime(2024, 1, 1),
                'content': '<p>First content</p>'
            }
        ]

    def test_compile_to_html_creates_file(self, compiler, sample_posts):
        """Test that HTML file is created"""
        filename = 'test.html'
        compiler.compile_to_html(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        assert os.path.exists(filepath)

    def test_compile_to_html_contains_posts(self, compiler, sample_posts):
        """Test that HTML contains post content"""
        filename = 'test.html'
        compiler.compile_to_html(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        assert 'First Post' in content
        assert 'First content' in content

    def test_compile_to_html_valid_structure(self, compiler, sample_posts):
        """Test that HTML has valid structure"""
        filename = 'test.html'
        compiler.compile_to_html(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        assert '<html>' in content or '<!DOCTYPE html>' in content
        assert '</html>' in content


class TestCompileToTxt:
    """Tests for compile_to_txt method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    @pytest.fixture
    def sample_posts(self):
        return [
            {
                'title': 'Text Post',
                'link': 'https://example.com/p/text',
                'pub_date': datetime(2024, 1, 1),
                'content': '<p>Text content with <strong>bold</strong></p>'
            }
        ]

    def test_compile_to_txt_creates_file(self, compiler, sample_posts):
        """Test that TXT file is created"""
        filename = 'test.txt'
        compiler.compile_to_txt(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        assert os.path.exists(filepath)

    def test_compile_to_txt_strips_html(self, compiler, sample_posts):
        """Test that HTML tags are stripped"""
        filename = 'test.txt'
        compiler.compile_to_txt(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        assert 'Text Post' in content
        assert '<p>' not in content
        assert '<strong>' not in content


class TestCompileToMd:
    """Tests for compile_to_md method"""

    @pytest.fixture
    def compiler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SubstackCompiler(output_dir=tmpdir)

    @pytest.fixture
    def sample_posts(self):
        return [
            {
                'title': 'Markdown Post',
                'link': 'https://example.com/p/md',
                'pub_date': datetime(2024, 1, 1),
                'content': '<h1>Heading</h1><p>Paragraph with <strong>bold</strong></p>'
            }
        ]

    def test_compile_to_md_creates_file(self, compiler, sample_posts):
        """Test that MD file is created"""
        filename = 'test.md'
        compiler.compile_to_md(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        assert os.path.exists(filepath)

    def test_compile_to_md_converts_to_markdown(self, compiler, sample_posts):
        """Test that HTML is converted to markdown"""
        filename = 'test.md'
        compiler.compile_to_md(sample_posts, filename)

        filepath = os.path.join(compiler.output_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        assert 'Markdown Post' in content
        # Markdownify should convert HTML to markdown
        assert '<h1>' not in content
        assert '<p>' not in content

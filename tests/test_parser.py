import pytest
from parser import SubstackParser


class TestSubstackParser:
    """Tests for SubstackParser class"""

    @pytest.fixture
    def parser(self):
        return SubstackParser()

    def test_parse_empty_content(self, parser):
        """Test parsing empty content returns empty string"""
        result = parser.parse_content("")
        assert result == ""

    def test_parse_none_content(self, parser):
        """Test parsing None returns empty string"""
        result = parser.parse_content(None)
        assert result == ""

    def test_parse_removes_subscription_widget(self, parser):
        """Test that subscription widget is removed"""
        html = '''
        <div>
            <p>Real content</p>
            <div class="subscription-widget-wrap">Subscribe now!</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Real content' in result
        assert 'subscription-widget-wrap' not in result
        assert 'Subscribe now!' not in result

    def test_parse_removes_share_dialog(self, parser):
        """Test that share dialog is removed"""
        html = '''
        <div>
            <p>Article content</p>
            <div class="share-dialog">Share this post</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Article content' in result
        assert 'share-dialog' not in result
        assert 'Share this post' not in result

    def test_parse_removes_share_button(self, parser):
        """Test that share button is removed"""
        html = '''
        <div>
            <p>Content here</p>
            <button class="share-button">Share</button>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Content here' in result
        assert 'share-button' not in result

    def test_parse_removes_post_footer(self, parser):
        """Test that post footer is removed"""
        html = '''
        <div>
            <p>Main content</p>
            <div class="post-footer">Footer info</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Main content' in result
        assert 'post-footer' not in result
        assert 'Footer info' not in result

    def test_parse_removes_comments_section(self, parser):
        """Test that comments section is removed"""
        html = '''
        <div>
            <p>Article text</p>
            <div class="comments-section">Comments here</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Article text' in result
        assert 'comments-section' not in result
        assert 'Comments here' not in result

    def test_parse_removes_subscribe_footer(self, parser):
        """Test that subscribe footer is removed"""
        html = '''
        <div>
            <p>Newsletter content</p>
            <div class="subscribe-footer">Subscribe to continue</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Newsletter content' in result
        assert 'subscribe-footer' not in result

    def test_parse_removes_divs_with_subscribe_in_class(self, parser):
        """Test that divs with 'subscribe' in class name are removed"""
        html = '''
        <div>
            <p>Content</p>
            <div class="subscribe-button-container">Subscribe</div>
            <div class="newsletter-subscribe-form">Form here</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Content' in result
        assert 'subscribe-button-container' not in result
        assert 'newsletter-subscribe-form' not in result

    def test_parse_removes_divs_with_share_in_class(self, parser):
        """Test that divs with 'share' in class name are removed"""
        html = '''
        <div>
            <p>Article</p>
            <div class="share-buttons-wrapper">Share buttons</div>
            <div class="social-share">Social</div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Article' in result
        assert 'share-buttons-wrapper' not in result
        assert 'social-share' not in result

    def test_parse_removes_all_buttons(self, parser):
        """Test that all button elements are removed"""
        html = '''
        <div>
            <p>Text content</p>
            <button>Click me</button>
            <button class="subscribe">Subscribe</button>
            <button id="share-btn">Share</button>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Text content' in result
        assert '<button' not in result
        assert 'Click me' not in result

    def test_parse_removes_subscribe_links(self, parser):
        """Test that subscribe links are removed"""
        html = '''
        <div>
            <p>Main text</p>
            <div>
                <a href="/subscribe">Subscribe to newsletter</a>
            </div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Main text' in result
        # The link with "subscribe" should be removed
        assert 'Subscribe to newsletter' not in result

    def test_parse_preserves_regular_links(self, parser):
        """Test that regular links without 'subscribe' are preserved"""
        html = '''
        <div>
            <p>Check out <a href="/other">this link</a></p>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Check out' in result
        assert 'this link' in result
        assert '<a href="/other">' in result

    def test_parse_removes_nested_unwanted_elements(self, parser):
        """Test removal of nested unwanted elements"""
        html = '''
        <div>
            <p>Content</p>
            <div class="post-footer">
                <div class="share-dialog">
                    <button>Share</button>
                </div>
            </div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Content' in result
        assert 'post-footer' not in result
        assert 'share-dialog' not in result
        assert '<button' not in result

    def test_parse_preserves_essential_content(self, parser):
        """Test that essential content elements are preserved"""
        html = '''
        <div>
            <h1>Article Title</h1>
            <p>Paragraph one</p>
            <p>Paragraph two with <strong>bold</strong> and <em>italic</em></p>
            <img src="image.jpg" alt="description">
            <ul>
                <li>List item 1</li>
                <li>List item 2</li>
            </ul>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Article Title' in result
        assert 'Paragraph one' in result
        assert 'Paragraph two' in result
        assert '<strong>bold</strong>' in result
        assert '<em>italic</em>' in result
        assert '<img' in result
        assert 'image.jpg' in result
        assert '<ul>' in result
        assert 'List item 1' in result

    def test_parse_multiple_subscribe_elements(self, parser):
        """Test removing multiple subscribe elements"""
        html = '''
        <div>
            <p>Article</p>
            <div class="subscription-widget-wrap">Widget 1</div>
            <div class="subscribe-footer">Footer</div>
            <div class="newsletter-subscribe">Form</div>
            <p>More content</p>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Article' in result
        assert 'More content' in result
        assert 'subscription-widget-wrap' not in result
        assert 'subscribe-footer' not in result
        assert 'newsletter-subscribe' not in result

    def test_parse_case_insensitive_subscribe_link(self, parser):
        """Test that subscribe link removal is case-insensitive"""
        html = '''
        <div>
            <p>Text</p>
            <div><a href="/sub">SUBSCRIBE NOW</a></div>
            <div><a href="/sub">Subscribe Now</a></div>
            <div><a href="/sub">subscribe now</a></div>
        </div>
        '''
        result = parser.parse_content(html)

        assert 'Text' in result
        # All variations should be removed
        assert 'SUBSCRIBE' not in result
        assert 'Subscribe Now' not in result

    def test_parse_complex_real_world_html(self, parser):
        """Test parsing complex real-world-like HTML"""
        html = '''
        <div class="available-content">
            <h1>The Future of AI</h1>
            <p>This is a fascinating article about AI.</p>
            <img src="ai-image.jpg" alt="AI visualization">
            <p>More content here with <a href="https://example.com">external link</a>.</p>

            <div class="subscription-widget-wrap">
                <h3>Like this content?</h3>
                <button>Subscribe now</button>
            </div>

            <p>Final paragraph.</p>

            <div class="post-footer">
                <div class="share-dialog">
                    <button class="share-button">Share on Twitter</button>
                    <button class="share-button">Share on Facebook</button>
                </div>
                <div class="comments-section">
                    <h3>Comments</h3>
                </div>
            </div>
        </div>
        '''
        result = parser.parse_content(html)

        # Should preserve
        assert 'The Future of AI' in result
        assert 'fascinating article' in result
        assert 'ai-image.jpg' in result
        assert 'More content here' in result
        assert 'external link' in result
        assert 'Final paragraph' in result

        # Should remove
        assert 'subscription-widget-wrap' not in result
        assert 'Subscribe now' not in result
        assert 'post-footer' not in result
        assert 'share-dialog' not in result
        assert 'Share on Twitter' not in result
        assert 'comments-section' not in result

    def test_parse_empty_div_structure(self, parser):
        """Test parsing when all content would be removed"""
        html = '''
        <div class="subscription-widget-wrap">
            <button>Subscribe</button>
        </div>
        '''
        result = parser.parse_content(html)

        # Should be mostly empty, just the outer tags
        assert 'subscription-widget-wrap' not in result
        assert 'Subscribe' not in result

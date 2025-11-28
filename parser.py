from bs4 import BeautifulSoup

class SubstackParser:
    def parse_content(self, html_content):
        """
        Cleans the HTML content by removing unwanted elements.
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove common unwanted elements
        selectors_to_remove = [
            '.subscription-widget-wrap',
            '.share-dialog',
            '.share-button',
            '.post-footer',
            '.comments-section',
            '.subscribe-footer',
            'div[class*="subscribe"]', 
            'div[class*="share"]',     
            'button',                  
        ]

        for selector in selectors_to_remove:
            for element in soup.select(selector):
                element.decompose()

        # Remove "Subscribe" links often found at the end
        for a in soup.find_all('a', string=lambda text: text and "subscribe" in text.lower()):
            if a.parent.name == 'div' or 'button' in a.get('class', []):
                a.decompose()

        return str(soup)

from bs4 import BeautifulSoup


def parse_content(html_content):
    """
    Cleans the HTML content by removing unwanted elements.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')

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

    for a in soup.find_all('a', string=lambda text: text and "subscribe" in text.lower()):
        if a.parent.name == 'div' or 'button' in a.get('class', []):
            a.decompose()

    return str(soup)

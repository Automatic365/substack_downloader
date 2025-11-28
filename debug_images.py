import requests
from bs4 import BeautifulSoup

url = "https://newsletter.pragmaticengineer.com/p/code-security-for-software-engineers"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

images = soup.find_all('img')
for img in images[:5]:
    print(f"Image: {img.attrs}")

# Substack Downloader

A tool to download Substack newsletters and compile them into a book. This project provides both a Command Line Interface (CLI) and a Streamlit Web Interface.

## Features

- **Full Archive Support**: Fetches posts from the Substack archive API.
- **Multiple Output Formats**: Compile to PDF, EPUB, JSON, HTML, TXT, or Markdown.
- **Web Interface**: Easy-to-use web UI powered by Streamlit.
- **CLI**: efficient command-line tool for automation.
- **Customizable**: Limit the number of posts to download.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/Automatic365/substack_downloader.git
    cd substack_downloader
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Web Interface (Streamlit)

Run the Streamlit app:

```bash
python3 -m streamlit run app.py
```

Then open your browser to the URL provided (usually `http://localhost:8501`). Enter the Substack URL, select your desired output format, and click "Download & Compile".

### Command Line Interface (CLI)

Run the script directly from the terminal:

```bash
python main.py <SUBSTACK_URL> [OPTIONS]
```

**Options:**

- `url`: The URL of the Substack (e.g., `https://newsletter.pragmaticengineer.com`)
- `--output`: Output filename (default: `<Newsletter_Title>.<format>`)
- `--limit`: Limit the number of posts to download
- `--format`: Output format (choices: `pdf`, `epub`, `json`, `html`, `txt`, `md`; default: `pdf`)
- `--cookie`: Deprecated. Use `SUBSTACK_COOKIE` environment variable instead (required for paywalled posts)

**Examples:**

Download all posts as PDF:
```bash
python main.py https://newsletter.pragmaticengineer.com
```

Download paywalled posts (requires cookie):
```bash
SUBSTACK_COOKIE="substack.sid=YOUR_COOKIE_HERE" python main.py https://newsletter.pragmaticengineer.com
```

Download the last 10 posts as EPUB:
```bash
python main.py https://newsletter.pragmaticengineer.com --limit 10 --format epub
```

Download as Markdown:
```bash
python main.py https://newsletter.pragmaticengineer.com --format md
```

## Dependencies

- `requests`
- `beautifulsoup4`
- `lxml`
- `fpdf2`
- `streamlit`
- `markdownify`
- `EbookLib`

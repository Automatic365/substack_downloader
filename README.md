# Substack Downloader

A tool to download Substack newsletters and compile them into a PDF book. This project provides both a Command Line Interface (CLI) and a Streamlit Web Interface.

## Features

- **Full Archive Support**: Fetches posts from the Substack archive API.
- **PDF Compilation**: Compiles downloaded posts into a single, clean PDF.
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
streamlit run app.py
```

Then open your browser to the URL provided (usually `http://localhost:8501`). Enter the Substack URL and click "Download & Compile".

### Command Line Interface (CLI)

Run the script directly from the terminal:

```bash
python main.py <SUBSTACK_URL> [OPTIONS]
```

**Examples:**

Download all posts:
```bash
python main.py https://newsletter.pragmaticengineer.com
```

Download the last 10 posts:
```bash
python main.py https://newsletter.pragmaticengineer.com --limit 10
```

Specify output filename:
```bash
python main.py https://newsletter.pragmaticengineer.com --output my_book.pdf
```

## Dependencies

- `requests`
- `beautifulsoup4`
- `lxml`
- `fpdf2`
- `streamlit`

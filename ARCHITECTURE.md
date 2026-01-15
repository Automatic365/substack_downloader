# Architecture

## Overview

Substack Downloader fetches posts from a Substack newsletter, cleans the HTML, and compiles the result into multiple output formats. It exposes both a CLI and a Streamlit UI.

## Modules

- `fetcher.py`: Network access to Substack. Fetches archive metadata and post HTML with retries, caching, and concurrency. Returns `models.Post` objects.
- `parser.py`: `parse_content()` cleans HTML by removing unwanted UI elements.
- `compiler/`: Package that transforms cleaned posts into output formats.
  - `compiler/__init__.py`: `SubstackCompiler` facade.
  - `compiler/media.py`: Image downloading and video embed conversion.
  - `compiler/formats/*`: Per-format emitters for PDF, EPUB, HTML, JSON, TXT, Markdown.
  - `compiler/utils.py`: Shared helpers for post normalization and sanitization.
- `orchestrator.py`: Shared orchestration for the Streamlit UI.
- `main.py`: CLI entrypoint.
- `app.py`: Streamlit UI.

## Data Flow

1. `SubstackFetcher` loads archive metadata and post HTML.
2. `parse_content()` removes subscription UI, share widgets, and buttons.
3. `SubstackCompiler` delegates to formatters, optionally downloading images and rewriting video embeds.
4. CLI/Streamlit writes output files and returns download paths.

## Configuration

All runtime settings are centralized in `config.py` and can be overridden with environment variables.

## Extension Points

- Add new output formats by implementing a formatter in `compiler/formats/` and wiring it into the facade.
- Add new content selectors in `config.py`.
- Add new orchestration flows in `orchestrator.py` without touching UI code.

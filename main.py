import argparse
import time
from fetcher import SubstackFetcher
from parser import SubstackParser
from compiler import SubstackCompiler

def main():
    parser = argparse.ArgumentParser(description="Download and compile Substack posts.")
    parser.add_argument("url", help="The URL of the Substack (e.g., https://example.substack.com)")
    parser.add_argument("--output", default=None, help="Output filename (default: <Newsletter_Title>.<format>)")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of posts to download")
    parser.add_argument("--format", choices=['pdf', 'epub', 'json', 'html', 'txt', 'md'], default='pdf', help="Output format (default: pdf)")
    
    args = parser.parse_args()
    
    # 1. Fetch Metadata
    fetcher = SubstackFetcher(args.url)
    newsletter_title = fetcher.get_newsletter_title()
    print(f"Fetching archive for: {newsletter_title}")
    
    metadata_list = fetcher.fetch_archive_metadata(limit=args.limit)
    
    if not metadata_list:
        print("No posts found or error fetching feed.")
        return

    # Determine output filename
    if args.output:
        output_filename = args.output
    else:
        safe_title = "".join(c for c in newsletter_title if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_title = safe_title.replace(" ", "_")
        output_filename = f"{safe_title}.{args.format}"

    # 2. Fetch Content & Parse
    parser_tool = SubstackParser()
    cleaned_posts = []
    
    print(f"Downloading and processing {len(metadata_list)} posts...")
    for i, meta in enumerate(metadata_list):
        print(f"[{i+1}/{len(metadata_list)}] {meta['title']}")
        content = fetcher.fetch_post_content(meta['link'])
        cleaned_content = parser_tool.parse_content(content)
        
        cleaned_posts.append({
            'title': meta['title'],
            'pub_date': meta['pub_date'],
            'content': cleaned_content
        })
        time.sleep(0.1)

    # 3. Compile
    compiler = SubstackCompiler()
    
    if args.format == 'pdf':
        compiler.compile_to_pdf(cleaned_posts, filename=output_filename)
    elif args.format == 'epub':
        compiler.compile_to_epub(cleaned_posts, filename=output_filename)
    elif args.format == 'json':
        compiler.compile_to_json(cleaned_posts, filename=output_filename)
    elif args.format == 'html':
        compiler.compile_to_html(cleaned_posts, filename=output_filename)
    elif args.format == 'txt':
        compiler.compile_to_txt(cleaned_posts, filename=output_filename)
    elif args.format == 'md':
        compiler.compile_to_md(cleaned_posts, filename=output_filename)
    
    print(f"Done! Saved to {output_filename}")

if __name__ == "__main__":
    main()

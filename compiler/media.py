"""
Media processing for images and video embeds.
"""
import os
import uuid

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

from config import IMAGE_CHUNK_SIZE, MAX_IMAGE_SIZE, USER_AGENT
from logger import setup_logger

logger = setup_logger(__name__)


class MediaProcessor:
    def __init__(self, images_dir: str, base_url: str = None):
        self.images_dir = images_dir
        self.base_url = base_url
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)

    def download_image(self, img_url):
        """
        Download an image and return the local path and filename.
        """
        filepath = None
        try:
            headers = {
                'User-Agent': USER_AGENT,
            }

            response = requests.get(img_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            content_length = response.headers.get('Content-Length')
            if content_length:
                try:
                    if int(content_length) > MAX_IMAGE_SIZE:
                        logger.warning(
                            "Skipping image %s (size %s exceeds limit %s)",
                            img_url,
                            content_length,
                            MAX_IMAGE_SIZE,
                        )
                        return None, None
                except ValueError:
                    logger.debug("Invalid Content-Length header for %s", img_url)

            content_type = response.headers.get('Content-Type', '').lower()
            if 'image/png' in content_type:
                ext = 'png'
            elif 'image/gif' in content_type:
                ext = 'gif'
            elif 'image/svg' in content_type:
                ext = 'svg'
            elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = 'jpg'
            else:
                if '.png' in img_url:
                    ext = 'png'
                elif '.gif' in img_url:
                    ext = 'gif'
                elif '.svg' in img_url:
                    ext = 'svg'
                else:
                    ext = 'jpg'

            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(self.images_dir, filename)

            with open(filepath, 'wb') as f:
                bytes_written = 0
                for chunk in response.iter_content(chunk_size=IMAGE_CHUNK_SIZE):
                    if chunk:
                        bytes_written += len(chunk)
                        if bytes_written > MAX_IMAGE_SIZE:
                            logger.warning(
                                "Skipping image %s (download exceeded limit %s)",
                                img_url,
                                MAX_IMAGE_SIZE,
                            )
                            raise ValueError("Image exceeds size limit")
                        f.write(chunk)

            return filepath, filename
        except requests.exceptions.Timeout:
            logger.error("Timeout downloading image %s", img_url)
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to download image %s: %s", img_url, exc)
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except IOError as exc:
            logger.error("Failed to write image %s: %s (disk full?)", img_url, exc)
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except ValueError as exc:
            logger.warning("Skipping image %s: %s", img_url, exc)
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None
        except Exception as exc:
            logger.error(
                "Unexpected error downloading image %s: %s: %s",
                img_url,
                type(exc).__name__,
                exc,
            )
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return None, None

    def process_html_images(self, html_content, for_epub=False, epub_book=None, verbose=True):
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')

        if not images:
            return str(soup)

        downloaded_count = 0
        failed_count = 0

        if verbose:
            logger.info("Found %s image(s) to download", len(images))

        for img in images:
            src = img.get('src')
            if not src:
                continue

            if src.startswith('data:'):
                if verbose:
                    logger.info("Skipping embedded data URI image")
                continue

            if verbose:
                logger.info("Downloading image: %s", src[:80])

            local_path, filename = self.download_image(src)
            if local_path:
                downloaded_count += 1
                if for_epub and epub_book:
                    try:
                        with open(local_path, 'rb') as f:
                            img_content = f.read()

                        epub_img = epub.EpubImage()
                        epub_img.uid = filename
                        epub_img.file_name = f"images/{filename}"

                        ext = filename.split('.')[-1].lower()
                        if ext in ('jpg', 'jpeg'):
                            media_type = 'image/jpeg'
                        elif ext == 'svg':
                            media_type = 'image/svg+xml'
                        elif ext == 'png':
                            media_type = 'image/png'
                        elif ext == 'gif':
                            media_type = 'image/gif'
                        elif ext == 'webp':
                            media_type = 'image/webp'
                        else:
                            media_type = f"image/{ext}"

                        epub_img.media_type = media_type
                        epub_img.content = img_content
                        epub_book.add_item(epub_img)

                        img['src'] = f"images/{filename}"

                        if verbose:
                            logger.info("Added image to EPUB: %s", filename)
                    except Exception as exc:
                        logger.warning("Error adding image to EPUB: %s", exc)
                        failed_count += 1
                        downloaded_count -= 1
                else:
                    img['src'] = local_path

                alt = img.get('alt', '')
                img.attrs = {
                    'src': img['src'],
                    'alt': alt,
                }
            else:
                failed_count += 1
                if verbose:
                    logger.warning("Failed to download image, keeping original URL")

        if verbose and (downloaded_count > 0 or failed_count > 0):
            logger.info(
                "Downloaded %s image(s), %s failed",
                downloaded_count,
                failed_count,
            )

        return str(soup)

    def process_html_videos(self, html_content, verbose=True, base_url=None):
        soup = BeautifulSoup(html_content, 'html.parser')
        video_count = 0

        videos = soup.find_all('video')
        for video in videos:
            video_count += 1

            video_url = None
            sources = video.find_all('source')

            for source in sources:
                src = source.get('src')
                if src and 'type=mp4' in src:
                    video_url = src
                    break

            if not video_url:
                for source in sources:
                    src = source.get('src')
                    if src:
                        video_url = src
                        break

            if not video_url and video.get('src'):
                video_url = video.get('src')

            if video_url:
                if video_url.startswith('/'):
                    if base_url:
                        video_url = base_url.rstrip('/') + video_url
                    elif self.base_url:
                        video_url = self.base_url.rstrip('/') + video_url
                    else:
                        poster = video.get('poster', '')
                        if poster and poster.startswith('http'):
                            from urllib.parse import urlparse
                            parsed = urlparse(poster)
                            video_url = f"{parsed.scheme}://{parsed.netloc}{video_url}"

                if '/api/v1/video/' in video_url:
                    link_text = "🎬 Click to watch Substack video"
                    note_text = "(May require login to view)"
                else:
                    link_text = "🎬 Click to watch video"
                    note_text = ""

                new_tag = soup.new_tag('p', style='background: #f0f0f0; padding: 10px; border-left: 4px solid #FF6B6B;')
                a_tag = soup.new_tag('a', href=video_url)
                a_tag.string = link_text
                new_tag.append(a_tag)

                if note_text:
                    new_tag.append(soup.new_tag('br'))
                    small = soup.new_tag('small', style='color: #666;')
                    small.string = note_text
                    new_tag.append(small)

                video.replace_with(new_tag)

                if verbose:
                    logger.info("Converted video to link: %s", video_url[:60])
            else:
                note = soup.new_tag('p', style='background: #fff3cd; padding: 10px;')
                note.string = "📹 Video content (URL not available)"
                video.replace_with(note)

        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if not src:
                continue

            video_platforms = ['youtube.com', 'youtube-nocookie.com', 'youtu.be', 'vimeo.com', 'wistia.com', 'loom.com', 'substack.com/embed']
            is_video = any(platform in src for platform in video_platforms)

            if is_video:
                video_count += 1
                video_url = src

                if 'youtube.com/embed/' in src or 'youtube-nocookie.com/embed/' in src:
                    if 'youtube-nocookie.com/embed/' in src:
                        video_id = src.split('youtube-nocookie.com/embed/')[-1].split('?')[0]
                    else:
                        video_id = src.split('youtube.com/embed/')[-1].split('?')[0]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                elif 'youtu.be/' in src:
                    video_url = src.replace('youtu.be/', 'youtube.com/watch?v=')

                if 'youtube' in src or 'youtu.be' in src:
                    platform = "YouTube"
                elif 'vimeo' in src:
                    platform = "Vimeo"
                elif 'loom' in src:
                    platform = "Loom"
                elif 'wistia' in src:
                    platform = "Wistia"
                else:
                    platform = "Video"

                link_text = f"🎬 Watch on {platform}"
                new_tag = soup.new_tag('p', style='background: #f0f0f0; padding: 10px; border-left: 4px solid #FF6B6B; margin: 10px 0;')
                a_tag = soup.new_tag('a', href=video_url, target='_blank')
                a_tag.string = link_text
                new_tag.append(a_tag)
                new_tag.append(soup.new_tag('br'))
                small = soup.new_tag('small', style='color: #666;')
                small.string = f"Link: {video_url[:70]}..."
                new_tag.append(small)
                iframe.replace_with(new_tag)

                if verbose:
                    logger.info("Converted %s embed to link: %s", platform, video_url[:60])

        if verbose and video_count > 0:
            logger.info("Converted %s video(s) to clickable links", video_count)

        return str(soup)

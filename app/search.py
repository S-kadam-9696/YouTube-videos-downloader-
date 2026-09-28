"""YouTube search module using yt-dlp."""

import json
from typing import List, Dict, Any, Optional
from yt_dlp import YoutubeDL


def search_youtube(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search YouTube for videos matching the query.
    
    Args:
        query: Search query or YouTube URL
        max_results: Maximum number of results to return
    
    Returns:
        List of search results with metadata
    """
    
    # If it looks like a YouTube URL, extract and get info for that video
    if "youtube.com" in query or "youtu.be" in query or query.startswith("http"):
        try:
            return _get_video_info(query)
        except Exception as e:
            # Fall back to search if URL extraction fails
            print(f"Could not extract info from URL: {e}")
    
    # Otherwise, perform a search
    return _search_videos(query, max_results)


def _get_video_info(url: str) -> List[Dict[str, Any]]:
    """Extract metadata for a single YouTube video/URL."""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            result = {
                'id': info.get('id', ''),
                'title': info.get('title', 'Untitled'),
                'url': url,
                'channel': info.get('channel', info.get('uploader', 'Unknown')),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'view_count': info.get('view_count'),
            }
            
            return [result]
    except Exception as e:
        raise Exception(f"Failed to get video info: {str(e)}")


def _search_videos(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search YouTube for videos using yt-dlp."""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'default_search': 'ytsearch',
            'playlist_items': f'1-{max_results}',
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            results = []
            if info and 'entries' in info:
                for entry in info['entries'][:max_results]:
                    if entry:
                        result = {
                            'id': entry.get('id', ''),
                            'title': entry.get('title', 'Untitled'),
                            'url': entry.get('url', f"https://www.youtube.com/watch?v={entry.get('id', '')}"),
                            'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                            'duration': entry.get('duration'),
                            'thumbnail': entry.get('thumbnail'),
                            'view_count': entry.get('view_count'),
                        }
                        results.append(result)
            
            return results
    except Exception as e:
        raise Exception(f"Search failed: {str(e)}")

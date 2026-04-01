#!/usr/bin/env python3
"""
Download video and extract audio from YouTube
Optimized for Video Dubbing Pipeline
"""

import os
import sys
import argparse
from pathlib import Path
import yt_dlp
import subprocess

class VideoDownloader:
    def __init__(self, output_dir="./downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def download_video(self, youtube_url: str, video_name: str = None):
        """
        Download video từ YouTube đầy đủ chất lượng
        - Giữ lại .mp4 nguyên bản
        - Tách audio thành .wav riêng
        """
        try:
            # Auto generate video name if not provided
            if not video_name:
                video_name = "video"
            
            video_path = self.output_dir / f"{video_name}.mp4"
            audio_path = self.output_dir / f"{video_name}.wav"
            
            print(f"[*] Đang download: {youtube_url}")
            print(f"[*] Destination: {self.output_dir}")
            
            # yt-dlp options
            ydl_opts = {
                'format': 'best[ext=mp4]/best',  # Download MP4 format
                'outtmpl': str(self.output_dir / f"{video_name}.%(ext)s"),
                'quiet': False,
                'no_warnings': False,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                    'nopostprocessor': False,
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                downloaded_file = ydl.prepare_filename(info)
            
            print(f"[✓] Video downloaded: {video_path}")
            print(f"[✓] Audio extracted: {audio_path}")
            
            return str(video_path), str(audio_path)
            
        except Exception as e:
            print(f"[✗] Error: {str(e)}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Download video and audio from YouTube"
    )
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument(
        "--name", 
        default="video",
        help="Output file name (default: video)"
    )
    parser.add_argument(
        "--output-dir",
        default="./downloads",
        help="Output directory (default: ./downloads)"
    )
    
    args = parser.parse_args()
    
    downloader = VideoDownloader(output_dir=args.output_dir)
    video_file, audio_file = downloader.download_video(args.url, args.name)
    
    print("\n" + "="*50)
    print("✓ Bước 1 hoàn tất!")
    print(f"  - Video: {video_file}")
    print(f"  - Audio: {audio_file}")
    print("="*50)

if __name__ == "__main__":
    main()

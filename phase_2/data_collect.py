import os
import subprocess

def download_playlist(theme_name, playlist_url):
    # Create output folder for this topic
    output_dir = f"data/{theme_name}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # yt-dlp command arguments
    cmd = [
        "yt-dlp",
        "--cookies", "www.youtube.com_cookies.txt",
        # 1. Real browser impersonation (requires curl_cffi)
        "--impersonate", "chrome",
        # 2. Use Android client (no GVS PO token required)
        "--extractor-args", "youtube:player_client=android,web",
        # 3. Video quality and format
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        # 4. Other stability-related parameters
        "--sleep-interval", "10",
        "--max-sleep-interval", "30",
        "--no-check-certificates",
        "--write-auto-subs",
        "--sub-lang", "en,zh-Hant",
        "--output", f"{output_dir}/%(title)s.%(ext)s",
        playlist_url
    ]
    
    print(f"🚀 Starting to download videos for topic [{theme_name}]...")
    # Run subprocess and catch any errors
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error while downloading [{theme_name}]: {e}")

# Define your topics and playlist URLs
playlists = {
    # "physics": "https://www.youtube.com/playlist?list=PLSQl0a2vh4HC-daPugvP8kL_zuE3u_3Zr",
    "chemistry": "https://www.youtube.com/watch?v=gGalnVpaom8&list=PLSQl0a2vh4HBnhjPgsJU2y1UhMwcYmb5u"
}

if __name__ == "__main__":
    for theme, url in playlists.items():
        download_playlist(theme, url)
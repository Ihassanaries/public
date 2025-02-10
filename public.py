from googleapiclient.discovery import build
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Initialize YouTube API
def initialize_youtube(api_key):
    return build('youtube', 'v3', developerKey=AIzaSyB2Dbul8LJQjAR-eFF307RjzLj9id8OO1I)

# Fetch videos uploaded in the last 7 days
def fetch_recent_videos(youtube, keywords):
    search_response = youtube.search().list(
        q=' '.join(keywords),
        part='id,snippet',
        type='video',
        publishedAfter=(datetime.utcnow() - timedelta(days=7)).isoformat() + "Z",
        maxResults=50
    ).execute()
    return search_response.get('items', [])

# Fetch video statistics
def fetch_video_stats(youtube, video_ids):
    if not video_ids:
        return []
    stats_response = youtube.videos().list(
        part='statistics,snippet',
        id=','.join(video_ids)
    ).execute()
    return stats_response.get('items', [])

# Fetch channel statistics
def fetch_channel_stats(youtube, channel_ids):
    if not channel_ids:
        return []
    channels_response = youtube.channels().list(
        part='statistics',
        id=','.join(channel_ids)
    ).execute()
    return channels_response.get('items', [])

# Calculate outlier score
def calculate_outlier_score(video_views, channel_avg_views, channel_std_dev_views):
    if channel_std_dev_views == 0:
        return 0  # Avoid division by zero
    z_score = (video_views - channel_avg_views) / channel_std_dev_views
    percentile = 100 * (1 - 0.5 * (1 + np.math.erf(z_score / np.sqrt(2))))
    return round(percentile, 2)

# Main function
def main():
    api_key = input("Enter your YouTube API Key: ").strip()
    youtube = initialize_youtube(api_key)

    # Ask user for 3+ keywords
    keywords = []
    while len(keywords) < 3:
        keyword = input(f"Enter keyword {len(keywords) + 1}: ").strip()
        if keyword:
            keywords.append(keyword)
        else:
            print("Keyword cannot be empty. Please try again.")

    # Fetch recent videos
    videos = fetch_recent_videos(youtube, keywords)
    if not videos:
        print("No videos found for the given keywords in the past 7 days.")
        return

    video_ids = [video['id']['videoId'] for video in videos if 'videoId' in video['id']]
    channel_ids = list(set([video['snippet'].get('channelId', '') for video in videos]))

    # Fetch video & channel statistics
    video_stats = fetch_video_stats(youtube, video_ids)
    channel_stats = fetch_channel_stats(youtube, channel_ids)

    # Convert to dictionary for fast lookup
    channel_data = {ch['id']: ch for ch in channel_stats if 'id' in ch}

    video_data = []
    for video in video_stats:
        channel_id = video['snippet'].get('channelId', '')
        if not channel_id or channel_id not in channel_data:
            continue

        channel_info = channel_data[channel_id]
        channel_subs = int(channel_info['statistics'].get('subscriberCount', 0))
        video_views = int(video['statistics'].get('viewCount', 0))

        # Skip channels with zero subscribers
        if channel_subs == 0 or video_views < 20 * channel_subs:
            continue

        # Get recent channel videos to calculate engagement
        channel_videos_response = youtube.search().list(
            channelId=channel_id,
            part='id',
            type='video',
            maxResults=10
        ).execute()
        channel_video_ids = [item['id']['videoId'] for item in channel_videos_response.get('items', [])]
        channel_video_stats = fetch_video_stats(youtube, channel_video_ids)

        channel_views = [int(v['statistics'].get('viewCount', 0)) for v in channel_video_stats if 'statistics' in v]
        if len(channel_views) > 1:
            channel_avg_views = np.mean(channel_views)
            channel_std_dev_views = np.std(channel_views)
        else:
            channel_avg_views, channel_std_dev_views = video_views, 0  # Default values if not enough data

        # Calculate outlier score
        outlier_score = calculate_outlier_score(video_views, channel_avg_views, channel_std_dev_views)

        # Store video data
        video_data.append({
            'Title': video['snippet']['title'],
            'Channel': video['snippet']['channelTitle'],
            'Views': video_views,
            'Subscribers': channel_subs,
            'Outlier Score': outlier_score,
            'Published Date': video['snippet']['publishedAt'],
            'Video URL': f"https://www.youtube.com/watch?v={video['id']}"
        })

    # Convert to DataFrame
    df = pd.DataFrame(video_data)

    # Filter videos with an outlier score > 50
    viral_videos = df[df['Outlier Score'] > 50].sort_values(by='Views', ascending=False)

    if viral_videos.empty:
        print("No viral videos found based on the criteria.")
    else:
        print("\nTop Viral Videos:")
        print(viral_videos.to_string(index=False))  # Clean print without index

if __name__ == "__main__":
    main()

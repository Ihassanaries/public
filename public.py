from googleapiclient.discovery import build
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Function to initialize YouTube API
def initialize_youtube(AIzaSyB2Dbul8LJQjAR-eFF307RjzLj9id8OO1I):
    return build('youtube', 'v3', developerKey=api_key)

# Function to fetch videos uploaded in the last 7 days
def fetch_recent_videos(youtube, keywords):
    search_response = youtube.search().list(
        q=' '.join(keywords),
        part='id,snippet',
        type='video',
        publishedAfter=(datetime.utcnow() - timedelta(days=7)).isoformat() + "Z",
        maxResults=50
    ).execute()
    return search_response.get('items', [])

# Function to fetch video statistics
def fetch_video_stats(youtube, video_ids):
    stats_response = youtube.videos().list(
        part='statistics,snippet',
        id=','.join(video_ids)
    ).execute()
    return stats_response.get('items', [])

# Function to fetch channel statistics
def fetch_channel_stats(youtube, channel_ids):
    channels_response = youtube.channels().list(
        part='statistics',
        id=','.join(channel_ids)
    ).execute()
    return channels_response.get('items', [])

# Function to calculate outlier score
def calculate_outlier_score(video_views, channel_avg_views, channel_std_dev_views):
    if channel_std_dev_views == 0:
        return 0  # Avoid division by zero
    z_score = (video_views - channel_avg_views) / channel_std_dev_views
    percentile = 100 * (1 - 0.5 * (1 + np.math.erf(z_score / np.sqrt(2))))
    return round(percentile, 2)

# Main function
def main():
    api_key = input("Enter your YouTube API Key: ").strip()  # Ask user for API key
    youtube = initialize_youtube(api_key)  # Pass API key correctly

    # Prompt user for at least three keywords
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

    video_ids = [video['id']['videoId'] for video in videos]
    channel_ids = list(set([video['snippet']['channelId'] for video in videos]))

    # Fetch video and channel statistics
    video_stats = fetch_video_stats(youtube, video_ids)
    channel_stats = fetch_channel_stats(youtube, channel_ids)

    # Create DataFrame for analysis
    video_data = []
    channel_data = {channel['id']: channel for channel in channel_stats}

    for video in video_stats:
        channel_id = video['snippet']['channelId']
        channel_info = channel_data.get(channel_id, {})
        channel_subs = int(channel_info.get('statistics', {}).get('subscriberCount', 0))
        video_views = int(video['statistics'].get('viewCount', 0))

        # Filter for new channels where views >= 20x subscribers
        if channel_subs > 0 and video_views >= 20 * channel_subs:
            # Fetch recent videos from this channel to calculate engagement
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
                'title': video['snippet']['title'],
                'channel': video['snippet']['channelTitle'],
                'views': video_views,
                'subscribers': channel_subs,
                'outlier_score': outlier_score,
                'publish_date': video['snippet']['publishedAt'],
                'video_url': f"https://www.youtube.com/watch?v={video['id']}"
            })

    # Convert to DataFrame
    df = pd.DataFrame(video_data)

    # Filter videos with an outlier score > 50
    viral_videos = df[df['outlier_score'] > 50].sort_values(by='views', ascending=False)

    if viral_videos.empty:
        print("No viral videos found based on the criteria.")
    else:
        print("\nTop Viral Videos:")
        print(viral_videos[['title', 'channel', 'views', 'subscribers', 'outlier_score', 'publish_date', 'video_url']])

if __name__ == "__main__":
    main()

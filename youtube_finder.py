import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Your YouTube API Key
API_KEY = "AIzaSyB2Dbul8LJQjAR-eFF307RjzLj9id8OO1I"

# Function to initialize YouTube API
def initialize_youtube(api_key):
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
    if not video_ids:
        return []
    stats_response = youtube.videos().list(
        part='statistics,snippet',
        id=','.join(video_ids)
    ).execute()
    return stats_response.get('items', [])

# Function to fetch channel statistics
def fetch_channel_stats(youtube, channel_ids):
    if not channel_ids:
        return []
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

# Streamlit UI
st.title("🔍 YouTube Viral Topic Finder")
st.write("Enter at least 3 keywords to find trending videos from new channels.")

# User Input for Keywords
keywords = []
for i in range(3):
    keyword = st.text_input(f"Enter keyword {i + 1}:", key=f"keyword_{i}")
    if keyword:
        keywords.append(keyword)

# Search Button
if st.button("Find Viral Videos") and len(keywords) >= 3:
    st.write("🔄 Searching for trending videos...")

    # Initialize YouTube API
    youtube = initialize_youtube(API_KEY)

    # Fetch recent videos
    videos = fetch_recent_videos(youtube, keywords)
    if not videos:
        st.error("❌ No trending videos found in the past 7 days.")
        st.stop()

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
        st.warning("⚠️ No viral videos found based on the criteria.")
    else:
        st.success("🎉 Found viral videos!")
        st.dataframe(viral_videos)

        # Download Button
        st.download_button(
            label="📥 Download CSV",
            data=viral_videos.to_csv(index=False),
            file_name="viral_youtube_videos.csv",
            mime="text/csv"
        )


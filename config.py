"""Configuration for Focus Blocker."""

# Blocked domains - includes main domains and CDN/asset domains
BLOCKED_DOMAINS = [
    # YouTube
    "youtube.com",
    "youtu.be",
    "googlevideo.com",
    "ytimg.com",
    # X/Twitter
    "twitter.com",
    "x.com",
    "twimg.com",
    # Reddit
    "reddit.com",
    "redd.it",
    "redditmedia.com",
    "redditstatic.com",
    # Facebook
    "facebook.com",
    "fb.com",
    "fbcdn.net",
    "facebook.net",
    # Instagram
    "instagram.com",
    "cdninstagram.com",
    # TikTok
    "tiktok.com",
    "tiktokcdn.com",
    "tiktokv.com",
    # Snapchat
    "snapchat.com",
    "snap.com",
    # Pinterest
    "pinterest.com",
    "pinimg.com",
    # LinkedIn
    "linkedin.com",
    "licdn.com",
    # Tumblr
    "tumblr.com",
    "tumblr.co",
    # Discord
    "discord.com",
    "discordapp.com",
    "discord.gg",
    # Twitch
    "twitch.tv",
    "ttvnw.net",
    # Mastodon
    "mastodon.social",
    # Threads
    "threads.net",
    # Bluesky
    "bsky.app",
    "bsky.social",
    # Vimeo
    "vimeo.com",
    "vimeocdn.com",
    # Microsoft Teams
    "teams.microsoft.com",
    "teams.live.com",
    # News Aggregators
    "news.ycombinator.com",
    "digg.com",
    "flipboard.com",
    # Entertainment/Time Sinks
    "imgur.com",
    "9gag.com",
    "dailymotion.com",
    "open.spotify.com",
    "netflix.com",
    # Dating Apps
    "tinder.com",
    "bumble.com",
    "hinge.co",
]

# Time window when sites are ALLOWED (24-hour format)
# Sites are blocked OUTSIDE this window
ALLOWED_START_HOUR = 20  # 8:00 PM
ALLOWED_END_HOUR = 22  # 10:00 PM

# Upstream DNS server for non-blocked queries
UPSTREAM_DNS = "8.8.8.8"
UPSTREAM_DNS_PORT = 53

# Local DNS server settings
DNS_HOST = "127.0.0.1"  # Listen on localhost only
DNS_PORT = 53

# Block response - returns this IP for blocked domains
BLOCK_IP = "0.0.0.0"

# Block response for IPv6 (AAAA)
# "::" is the IPv6 "unspecified" address; connections to it will fail.
BLOCK_IPV6 = "::"

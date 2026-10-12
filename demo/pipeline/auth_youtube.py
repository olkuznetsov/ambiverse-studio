"""Demo stand-in for auth_youtube.py (upload-token consent). See auth_analytics.py."""
from _demo import pause, say

say("Please visit this URL to authorize this application: "
    "https://accounts.google.com/o/oauth2/auth?client_id=DEMO&scope=youtube.upload"
    "  (demo — not a real consent link)")
pause(2)
say("\n[demo] No OAuth app in demo mode — nothing to authorize, nothing saved.")

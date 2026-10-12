"""Demo stand-in for auth_analytics.py.

The real script prints a Google consent URL and waits on localhost:8765 for the
OAuth redirect; Studio streams that URL into the job log. Demo mode has no OAuth
app, so this shows the same flow and exits without saving anything.
"""
from _demo import pause, say

say("Open this URL to grant read-only analytics access:\n")
say("https://accounts.google.com/o/oauth2/auth?client_id=DEMO&scope=yt-analytics.readonly"
    "&redirect_uri=http://localhost:8765/  (demo — not a real consent link)")
pause(2)
say("\n[demo] No OAuth app in demo mode — nothing to authorize, nothing saved.")

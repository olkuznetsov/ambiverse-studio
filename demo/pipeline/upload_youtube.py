"""Demo stand-in for upload_youtube.upload — prints the real tagged chunk progress
(`[upload] N%`) and returns a fake video id. Nothing is uploaded."""
from _demo import fake_id, say, upload_bar


def upload(video_path, thumbnail_path, title, description, tags,
           localizations=None, default_language="en", publish_at=None):
    say(f"Uploading {title!r}" + (f" (scheduled {publish_at})" if publish_at else ""))
    upload_bar()
    video_id = fake_id()
    say(f"Uploaded: https://youtu.be/{video_id}  (demo — nothing left this machine)")
    return video_id

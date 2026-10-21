"""Free delivery of the nightly post: send text + chart to your own Telegram, post from the phone.

No X API, no card. Create a bot with @BotFather, send it one message, read your chat id from
https://api.telegram.org/bot<TOKEN>/getUpdates, put both in config under post.telegram.
Standard library only.
"""
from __future__ import annotations

import json
import mimetypes
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = "https://api.telegram.org/bot{token}/{method}"


def intent_url(text: str) -> str:
    """A link that opens X's composer with the text filled in; the image is attached by hand."""
    return "https://x.com/intent/post?" + urllib.parse.urlencode({"text": text})


def _multipart(fields: dict, file_field: str, path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
            f"filename=\"{path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
    out += path.read_bytes()
    out += f"\r\n--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def send_telegram(token: str, chat_id: str, text: str, photo: Path | None) -> dict:
    """Send the chart as a photo with the post text as caption, then the text alone for copying."""
    if photo is not None:
        body, ctype = _multipart({"chat_id": chat_id, "caption": text}, "photo", photo)
        req = urllib.request.Request(API.format(token=token, method="sendPhoto"), data=body,
                                     headers={"Content-Type": ctype})
    else:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(API.format(token=token, method="sendMessage"), data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read())
    # a second, plain message so long-press-copy on the phone grabs only the post text
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text + "\n\n" + intent_url(text),
                                   "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(urllib.request.Request(API.format(token=token, method="sendMessage"), data=data),
                                timeout=60):
        pass
    return res

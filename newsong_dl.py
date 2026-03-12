#!/usr/bin/env python3
"""
newsong_dl.py — Telegram helper for newsong (inline query mode).

Two modes, called by the parent Bash script:

  python3 newsong_dl.py search "O Rangrez"
    → runs client.inline_query("deezload2bot", query)
    → prints TRACK:<n>:<title> — <description> lines (up to 10)
    → saves query to /tmp/newsong_inline_results (JSON)

  python3 newsong_dl.py download 2 ~/off-music
    → re-runs inline_query with saved query
    → calls results[1].click("deezload2bot")
    → waits for text confirmation, then FLAC document
    → downloads with PROGRESS:<cur>:<tot> lines
    → prints SAVED:<path> as final line

Errors go to stderr. Exit 0 on success, 1 on failure.
"""

import sys
import os
import json
import asyncio
import time
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# Telegram credentials (Telegram Desktop app)
# ─────────────────────────────────────────────
API_ID   = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT      = "deezload2bot"
SESSION  = os.path.expanduser("~/.newsong_session")
RESULTS_CACHE = "/tmp/newsong_inline_results"

INLINE_RETRIES     = 3    # retry inline_query up to 3 times
INLINE_RETRY_SLEEP = 4    # seconds between retries
FLAC_TIMEOUT       = 120  # total seconds to wait for FLAC document
FLAC_RETRY_AFTER   = 30   # if no FLAC after this, re-click once


def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)


async def inline_query_with_retry(client, query):
    """Run inline_query with retries for BotResponseTimeoutError."""
    for attempt in range(INLINE_RETRIES):
        try:
            results = await client.inline_query(BOT, query)
            return results
        except Exception as e:
            if attempt < INLINE_RETRIES - 1:
                eprint(f"⚠ Inline query attempt {attempt+1} failed, retrying in {INLINE_RETRY_SLEEP}s...")
                await asyncio.sleep(INLINE_RETRY_SLEEP)
            else:
                eprint(f"❌ Bot not responding. Try again in a moment.")
                sys.exit(1)


# ─────────────────────────────────────────────
# Auto-configure bot quality to FLAC
# ─────────────────────────────────────────────
FLAC_QUALITY_FLAG = os.path.expanduser("~/.newsong_flac_set")


async def ensure_flac_quality(client):
    """Send /settings to bot and navigate to FLAC quality. Non-fatal if it fails."""
    try:
        from telethon.tl.types import ReplyInlineMarkup

        sent_at = datetime.now(timezone.utc)
        await client.send_message(BOT, "/settings")

        async def wait_for_keyboard(timeout=15):
            deadline = time.time() + timeout
            while time.time() < deadline:
                async for msg in client.iter_messages(BOT, limit=5):
                    if msg.date < sent_at:
                        break
                    if msg.out:
                        continue
                    if msg.reply_markup and isinstance(msg.reply_markup, ReplyInlineMarkup):
                        return msg
                await asyncio.sleep(1)
            return None

        # Step 1: wait for settings menu
        settings_msg = await wait_for_keyboard(15)
        if not settings_msg:
            print("\u26a0\ufe0f  Could not reach @deezload2bot settings. Set quality to FLAC manually.", flush=True)
            return

        # Step 2: find and click "Audio Quality" button
        clicked = False
        for row in settings_msg.reply_markup.rows:
            for btn in row.buttons:
                if "quality" in btn.text.lower() or "audio" in btn.text.lower():
                    sent_at = datetime.now(timezone.utc)
                    await settings_msg.click(text=btn.text)
                    clicked = True
                    break
            if clicked:
                break

        if not clicked:
            print("\u26a0\ufe0f  Could not find Audio Quality button. Set quality to FLAC manually.", flush=True)
            return

        # Step 3: wait for quality submenu
        quality_msg = await wait_for_keyboard(15)
        if not quality_msg:
            print("\u26a0\ufe0f  Quality submenu did not appear. Set quality to FLAC manually.", flush=True)
            return

        # Step 4: find and click "FLAC" button
        clicked = False
        for row in quality_msg.reply_markup.rows:
            for btn in row.buttons:
                if "flac" in btn.text.lower():
                    await quality_msg.click(text=btn.text)
                    clicked = True
                    break
            if clicked:
                break

        if not clicked:
            print("\u26a0\ufe0f  FLAC option not found in quality menu. Set quality to FLAC manually.", flush=True)
            return

        await asyncio.sleep(2)
        print("QUALITY_SET", flush=True)
        # Persist flag only after confirmed success
        open(FLAC_QUALITY_FLAG, "w").close()

    except Exception as e:
        eprint(f"\u26a0\ufe0f  Could not auto-configure FLAC quality: {e}")


# ─────────────────────────────────────────────
# Mode 1 — Search: inline_query, print tracks
# ─────────────────────────────────────────────
async def do_search(client, query):
    results = await inline_query_with_retry(client, query)

    if not results or len(results) == 0:
        eprint(f'❌ No results for "{query}"')
        sys.exit(1)

    # Print up to 10 tracks
    items = []
    for i, r in enumerate(results[:10], 1):
        title = r.result.title or ""
        desc  = r.result.description or ""
        display = f"{title} — {desc}" if desc else title
        print(f"TRACK:{i}:{display}", flush=True)
        items.append({"title": title, "description": desc})

    # Save query + count for download mode.
    # We save the query string (not the result objects) because Telethon's
    # InlineResult holds a client reference that can't survive across
    # separate process invocations. Download mode re-runs the query.
    cache = {"query": query, "count": len(items)}
    with open(RESULTS_CACHE, "w") as f:
        json.dump(cache, f)


# ─────────────────────────────────────────────
# Mode 2 — Download: click result, get FLAC
# ─────────────────────────────────────────────
async def do_download(client, selection, output_dir):
    from telethon.tl.types import DocumentAttributeFilename

    # Load cached query
    try:
        with open(RESULTS_CACHE, "r") as f:
            cache = json.load(f)
    except (OSError, json.JSONDecodeError):
        eprint("❌ No search cache found. Run search first.")
        sys.exit(1)

    query = cache["query"]
    idx = selection - 1

    # Re-run inline query to get clickable results
    results = await inline_query_with_retry(client, query)

    if not results or len(results) <= idx:
        eprint("❌ Could not retrieve results. Try searching again.")
        sys.exit(1)

    sent_at = datetime.now(timezone.utc)

    # Click the selected result — sends it as "via @deezload2bot".
    # The FLAC arrives as an outgoing audio message (msg.audio=True,
    # msg.document=True, mime_type=audio/x-flac).
    print("[3/4] ⏳ Waiting for @deezload2bot...", flush=True)
    sent_msg = await results[idx].click(BOT)

    flac_msg = None

    def is_audio(msg):
        """Check if a message carries an audio/flac file."""
        if msg.audio:
            return True
        if msg.document:
            mime = getattr(msg.document, "mime_type", "") or ""
            if "flac" in mime:
                return True
            for a in getattr(msg.document, "attributes", []):
                fn = getattr(a, "file_name", "") or ""
                if fn.lower().endswith(".flac"):
                    return True
        return False

    # Case 1: the click() return already carries the audio
    if sent_msg and is_audio(sent_msg):
        eprint(f"[debug] click() returned audio directly (id={sent_msg.id})")
        flac_msg = sent_msg

    # Case 2: poll recent messages (including our own outgoing ones)
    if flac_msg is None:
        from datetime import timedelta
        flac_wait_start = time.time()
        retried = False
        check_after = sent_at - timedelta(seconds=5)

        while time.time() - flac_wait_start < FLAC_TIMEOUT:
            async for msg in client.iter_messages(BOT, limit=10):
                if msg.date < check_after:
                    break
                if is_audio(msg):
                    eprint(f"[debug] found audio in poll (id={msg.id}, out={msg.out})")
                    flac_msg = msg
                    break
            if flac_msg:
                break

            # Bot quirk: if 30s pass with no FLAC, re-click once
            elapsed = time.time() - flac_wait_start
            if elapsed > FLAC_RETRY_AFTER and not retried:
                print("🔄 Bot is slow — retrying...", flush=True)
                try:
                    retry_msg = await results[idx].click(BOT)
                    if retry_msg and is_audio(retry_msg):
                        flac_msg = retry_msg
                        break
                except Exception:
                    pass
                retried = True

            await asyncio.sleep(3)

    if flac_msg is None:
        eprint(f"❌ Timed out ({FLAC_TIMEOUT}s) — @deezload2bot did not send the FLAC.")
        eprint("   Possible causes:")
        eprint("   • You haven't joined @deezload2bot's channel — open Telegram and do this manually")
        eprint("   • The bot is down or rate-limiting — try again in a minute")
        eprint("   • The track isn't available on Deezer")
        sys.exit(1)

    # Extract filename from DocumentAttributeFilename or audio attributes
    filename = "download.flac"
    if flac_msg.document:
        for attr in flac_msg.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break

    # Hand off to tdl for fast parallel download
    print(f"TDL_MSGID:{flac_msg.id}", flush=True)
    print(f"TDL_FILENAME:{filename}", flush=True)
    print(f"TDL_FILESIZE:{flac_msg.document.size}", flush=True)


# ─────────────────────────────────────────────
# Mode 3 — Link: send URL, get FLAC
# ─────────────────────────────────────────────
async def do_link(client, link_url):
    from telethon.tl.types import DocumentAttributeFilename
    from telethon import errors

    sent_at = datetime.now(timezone.utc)

    # Send the link as a plain message
    try:
        await client.send_message(BOT, link_url)
    except errors.FloodWaitError as fw:
        eprint(f"⏳ Rate limited. Waiting {fw.seconds}s...")
        await asyncio.sleep(fw.seconds)
        await client.send_message(BOT, link_url)

    print("[1/2] ⏳ Waiting for @deezload2bot...", flush=True)

    def is_audio(msg):
        """Check if a message carries an audio/flac file."""
        if msg.audio:
            return True
        if msg.document:
            mime = getattr(msg.document, "mime_type", "") or ""
            if "flac" in mime:
                return True
            for a in getattr(msg.document, "attributes", []):
                fn = getattr(a, "file_name", "") or ""
                if fn.lower().endswith(".flac"):
                    return True
        return False

    flac_msg = None
    retried = False
    flac_wait_start = time.time()
    check_after = sent_at - __import__("datetime").timedelta(seconds=5)

    while time.time() - flac_wait_start < FLAC_TIMEOUT:
        async for msg in client.iter_messages(BOT, limit=10):
            if msg.date < check_after:
                break
            if is_audio(msg):
                flac_msg = msg
                break
        if flac_msg:
            break

        # If 35s pass with no FLAC, resend the link once
        elapsed = time.time() - flac_wait_start
        if elapsed > 35 and not retried:
            print("🔄 Bot is slow — resending link...", flush=True)
            try:
                await client.send_message(BOT, link_url)
            except Exception:
                pass
            retried = True

        await asyncio.sleep(3)

    if flac_msg is None:
        eprint(f"❌ Timed out ({FLAC_TIMEOUT}s) — @deezload2bot did not send the FLAC.")
        eprint("   Possible causes:")
        eprint("   • You haven't joined @deezload2bot's channel — open Telegram and do this manually")
        eprint("   • The bot is down or rate-limiting — try again in a minute")
        eprint("   • The track/link isn't available on Deezer")
        sys.exit(1)

    # Extract filename
    filename = "download.flac"
    if flac_msg.document:
        for attr in flac_msg.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break

    print(f"TDL_MSGID:{flac_msg.id}", flush=True)
    print(f"TDL_FILENAME:{filename}", flush=True)
    print(f"TDL_FILESIZE:{flac_msg.document.size}", flush=True)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from telethon import TelegramClient
    except ImportError:
        eprint("❌ Telethon not installed. Run: pip install telethon --break-system-packages")
        sys.exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    client = TelegramClient(SESSION, API_ID, API_HASH)

    async def run():
        await client.start()
        try:
            # Ensure FLAC quality before download/link (stdout flows through
            # read_python_output in the bash script, so signals are visible)
            if mode in ("download", "link") and not os.path.exists(FLAC_QUALITY_FLAG):
                await ensure_flac_quality(client)

            if mode == "search":
                if len(sys.argv) < 3:
                    eprint(f"Usage: {sys.argv[0]} search <query>")
                    sys.exit(1)
                await do_search(client, " ".join(sys.argv[2:]))

            elif mode == "download":
                if len(sys.argv) < 4:
                    eprint(f"Usage: {sys.argv[0]} download <n> <output_dir>")
                    sys.exit(1)
                await do_download(client, int(sys.argv[2]), sys.argv[3])

            elif mode == "link":
                if len(sys.argv) < 3:
                    eprint(f"Usage: {sys.argv[0]} link <url>")
                    sys.exit(1)
                await do_link(client, sys.argv[2])

            else:
                eprint(f"Usage: {sys.argv[0]} search <query>")
                eprint(f"       {sys.argv[0]} download <n> <output_dir>")
                eprint(f"       {sys.argv[0]} link <url>")
                sys.exit(1)
        finally:
            await client.disconnect()

    asyncio.run(run())

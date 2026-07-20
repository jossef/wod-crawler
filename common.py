import os
import time
import requests


def send_telegram_workout(
    token: str,
    chat_id: str,
    workout: dict,
    max_retries: int = 5,
):
    """
    Send a workout in this structure:
    {
        "date": "2026-07-19",
        "content": "...",
        "image": "https://...",
        "url": "https://..."
    }
    """

    date = workout.get("date", "")
    content = workout.get("content", "")
    image_url = workout.get("image")
    workout_url = workout.get("url")

    message_parts = []

    if date:
        message_parts.append(f"🏋️ Workout: {date}")

    if content:
        message_parts.append(content)

    if workout_url:
        message_parts.append(f"Full workout:\n{workout_url}")

    text = "\n\n".join(message_parts)

    # Telegram photo captions are limited to 1,024 characters.
    # If the workout is longer, send the image first and text separately.
    if image_url and len(text) <= 1024:
        return _send_telegram_request(
            token=token,
            method="sendPhoto",
            payload={
                "chat_id": chat_id,
                "photo": image_url,
                "caption": text,
            },
            max_retries=max_retries,
        )

    results = []

    if image_url:
        results.append(
            _send_telegram_request(
                token=token,
                method="sendPhoto",
                payload={
                    "chat_id": chat_id,
                    "photo": image_url,
                },
                max_retries=max_retries,
            )
        )

    # Telegram messages are limited to 4,096 characters.
    for chunk in split_telegram_message(text):
        results.append(
            _send_telegram_request(
                token=token,
                method="sendMessage",
                payload={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
                max_retries=max_retries,
            )
        )

    return results


def _send_telegram_request(
    token: str,
    method: str,
    payload: dict,
    max_retries: int,
):
    url = f"https://api.telegram.org/bot{token}/{method}"

    for attempt in range(max_retries):
        resp = requests.post(url, json=payload, timeout=30)

        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(
                f"Telegram returned invalid JSON: "
                f"HTTP {resp.status_code}: {resp.text}"
            )

        if data.get("ok"):
            return data

        if resp.status_code == 429:
            retry_after = data.get("parameters", {}).get("retry_after", 5)
            print(f"Rate limited, waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        raise RuntimeError(f"Telegram API error: {data}")

    raise RuntimeError(f"Failed after {max_retries} attempts.")


def split_telegram_message(text: str, limit: int = 4096) -> list[str]:
    """Split long messages while preferring newline boundaries."""
    chunks = []

    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)

        if split_at <= 0:
            split_at = limit

        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    return chunks
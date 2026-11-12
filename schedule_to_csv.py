#!/usr/bin/env python3

import csv
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

import yaml

TALK_DURATION_MINUTES = 15
QUESTION_DURATION_MINUTES = 4
FALLBACK_STANDALONE_DURATION_MINUTES = 10  # used for the final standalone row


def parse_time(time_str: str, base_date: date) -> datetime:
    """
    Parse times like '9:00 AM' into a datetime on an arbitrary date.
    """
    return datetime.strptime(
        f"{base_date.isoformat()} {time_str}",
        "%Y-%m-%d %I:%M %p",
    )


def fmt_duration(minutes: int) -> str:
    return str(timedelta(minutes=minutes))


def fmt_start(dt: datetime) -> str:
    # Cross-platform time formatting without leading zero on the hour
    s = dt.strftime("%I:%M %p")
    return s.lstrip("0")


def is_session_container(item: dict) -> bool:
    """
    Session headers are the items that contain talks and are not meant to
    become their own rows in the CSV.
    """
    return bool(item.get("talks"))


def main(yaml_path: str, csv_path: str) -> None:
    yaml_file = Path(yaml_path)
    csv_file = Path(csv_path)

    with yaml_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    schedule = data.get("schedule", [])
    base_date = date(2026, 1, 1)  # arbitrary date just for time arithmetic

    rows = []

    for i, item in enumerate(schedule):
        name = item.get("name", "").strip()
        start_time = item.get("start_time")
        if not start_time:
            continue

        # If this item is a session container, expand its talks.
        if is_session_container(item):
            current = parse_time(start_time, base_date)

            for talk in item.get("talks", []):
                title = talk.get("title", "").strip()
                speaker = talk.get("author", "").strip()

                rows.append(
                    {
                        "Start": fmt_start(current),
                        "Duration": fmt_duration(TALK_DURATION_MINUTES),
                        "Title": title,
                        "Speaker": speaker,
                    }
                )

                current += timedelta(minutes=TALK_DURATION_MINUTES)

                rows.append(
                    {
                        "Start": fmt_start(current),
                        "Duration": fmt_duration(QUESTION_DURATION_MINUTES),
                        "Title": "Questions",
                        "Speaker": "",
                    }
                )

                current += timedelta(minutes=QUESTION_DURATION_MINUTES)

            continue

        # Standalone items: welcome, breaks, lunch, closing, etc.
        # We keep them unless they look like a pure session header.
        if name.lower().startswith("session "):
            continue

        current = parse_time(start_time, base_date)

        # Try to infer duration from the next top-level item's start time.
        duration_minutes = None
        for j in range(i + 1, len(schedule)):
            nxt = schedule[j]
            nxt_start = nxt.get("start_time")
            if nxt_start:
                next_dt = parse_time(nxt_start, base_date)
                duration_minutes = max(
                    int((next_dt - current).total_seconds() // 60), 0
                )
                break

        if duration_minutes is None:
            duration_minutes = FALLBACK_STANDALONE_DURATION_MINUTES

        rows.append(
            {
                "Start": fmt_start(current),
                "Duration": fmt_duration(duration_minutes),
                "Title": name,
                "Speaker": item.get("chair", "") or "",
            }
        )

    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Start", "Duration", "Title", "Speaker"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python yaml_to_csv.py schedule.yaml output.csv")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])

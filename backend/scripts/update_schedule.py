"""Update the hackathon schedule for May 30, 2026."""

import json
import sqlite3

DATABASE_URL = "dev.db"
HACKATHON_ID = "f87baecd-67ef-4fa7-ae7d-39c2bc13c788"

# May 30, 2026 Event Day Schedule
SCHEDULE = [
    {
        "datetime": "2026-05-30T09:00:00",
        "title": "Check-in and opening ceremony",
        "description": "Welcome to Hack the Valley! Check in and get ready for the event.",
        "location": "Main Auditorium",
    },
    {
        "datetime": "2026-05-30T09:30:00",
        "title": "Hacking begins",
        "description": "Start building your projects!",
        "location": "Hacking Areas",
    },
    {
        "datetime": "2026-05-30T11:00:00",
        "title": "Mentor office hours",
        "description": "Get help and guidance from industry mentors.",
        "location": "Mentor Lounge",
    },
    {
        "datetime": "2026-05-30T12:30:00",
        "title": "Lunch + networking",
        "description": "Enjoy lunch and connect with fellow hackers.",
        "location": "Dining Hall",
    },
    {
        "datetime": "2026-05-30T14:00:00",
        "title": "Project check-ins",
        "description": "Mid-event progress check with organizers.",
        "location": "Check-in Stations",
    },
    {
        "datetime": "2026-05-30T15:30:00",
        "title": "Project submissions close",
        "description": "Final deadline to submit your projects.",
        "location": "Online",
    },
    {
        "datetime": "2026-05-30T16:00:00",
        "title": "Live demos and judging",
        "description": "Present your projects to the judges.",
        "location": "Main Auditorium",
    },
    {
        "datetime": "2026-05-30T17:00:00",
        "title": "Awards and closing",
        "description": "Winners announced and closing ceremony.",
        "location": "Main Auditorium",
    },
]


def update_schedule():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Verify hackathon exists
    cursor.execute("SELECT id, name FROM hackathons WHERE id = ?", (HACKATHON_ID,))
    row = cursor.fetchone()
    if not row:
        print(f"Hackathon with ID {HACKATHON_ID} not found!")
        conn.close()
        return

    print(f"Updating schedule for: {row[1]}")

    # Update the schedule
    schedule_json = json.dumps(SCHEDULE)
    cursor.execute("UPDATE hackathons SET schedule = ? WHERE id = ?", (schedule_json, HACKATHON_ID))
    conn.commit()

    # Verify update
    cursor.execute("SELECT schedule FROM hackathons WHERE id = ?", (HACKATHON_ID,))
    updated = cursor.fetchone()
    if updated and updated[0]:
        parsed = json.loads(updated[0])
        print(f"\nSuccessfully updated schedule with {len(parsed)} events:")
        for event in parsed:
            print(f"  - {event['datetime']}: {event['title']}")
    else:
        print("Failed to update schedule!")

    conn.close()


if __name__ == "__main__":
    update_schedule()

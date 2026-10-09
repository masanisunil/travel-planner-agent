import psycopg
from psycopg.types.json import Jsonb


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS roam_saved_trips (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    destination TEXT NOT NULL,
    duration INTEGER NOT NULL,
    trip_date DATE NOT NULL,
    budget TEXT NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def _connection(database_url):
    if not database_url:
        raise ValueError("Missing database configuration")
    return psycopg.connect(database_url, autocommit=True, connect_timeout=10)


def _result_payload(result):
    messages = result.get("messages", [])
    overview = messages[-1].content if messages else ""
    if not isinstance(overview, str):
        overview = str(overview)
    return {
        "itinerary": result.get("itinerary", ""),
        "flight_results": result.get("flight_results", ""),
        "train_results": result.get("train_results", ""),
        "bus_results": result.get("bus_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "overview": overview,
    }


def save_trip(database_url, trip):
    with _connection(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE)
        cursor.execute(
            """
            INSERT INTO roam_saved_trips
                (id, title, destination, duration, trip_date, budget, result)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                destination = EXCLUDED.destination,
                duration = EXCLUDED.duration,
                trip_date = EXCLUDED.trip_date,
                budget = EXCLUDED.budget,
                result = EXCLUDED.result
            """,
            (
                str(trip["id"]),
                trip.get("title") or trip["destination"],
                trip["destination"],
                trip["duration"],
                trip["date"],
                trip["budget"],
                Jsonb(_result_payload(trip["result"])),
            ),
        )


def list_trips(database_url):
    with _connection(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE)
        cursor.execute(
            """
            SELECT id, title, destination, duration, trip_date::text, budget
            FROM roam_saved_trips
            ORDER BY created_at DESC
            LIMIT 50
            """
        )
        return [
            {
                "id": row[0],
                "title": row[1],
                "destination": row[2],
                "duration": row[3],
                "date": row[4],
                "budget": row[5],
            }
            for row in cursor.fetchall()
        ]


def get_trip(database_url, trip_id):
    with _connection(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE)
        cursor.execute(
            """
            SELECT id, title, destination, duration, trip_date::text, budget, result
            FROM roam_saved_trips
            WHERE id = %s
            """,
            (str(trip_id),),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "destination": row[2],
        "duration": row[3],
        "date": row[4],
        "budget": row[5],
        "result": row[6],
    }


def rename_trip(database_url, trip_id, title):
    with _connection(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE)
        cursor.execute(
            "UPDATE roam_saved_trips SET title = %s WHERE id = %s",
            (title.strip(), str(trip_id)),
        )
        return cursor.rowcount > 0


def delete_trip(database_url, trip_id):
    with _connection(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(CREATE_TABLE)
        cursor.execute("DELETE FROM roam_saved_trips WHERE id = %s", (str(trip_id),))
        return cursor.rowcount > 0
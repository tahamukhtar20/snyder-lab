import os
import psycopg2
from faker import Faker
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

db_config = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

NUM_PARTICIPANTS = 10
faker = Faker()

def generate_dummy_participants(n):
    participants = []
    for pid in range(1, n + 1):
        name = faker.name()
        token = faker.uuid4() if pid == 1 else None
        participants.append((pid, name, token))
    return participants

def insert_participants(participants):
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        for pid, name, token in participants:
            cursor.execute("""
                INSERT INTO participant (participant_id, name, token)
                VALUES (%s, %s, %s)
                ON CONFLICT (participant_id) DO NOTHING
            """, (pid, name, token))

        conn.commit()
        cursor.close()
        conn.close()
        print(f"Inserted {len(participants)} dummy participants.")
    
    except Exception as e:
        print(f"Error inserting participants: {str(e)}")

if __name__ == "__main__":
    dummy_participants = generate_dummy_participants(NUM_PARTICIPANTS)
    insert_participants(dummy_participants)

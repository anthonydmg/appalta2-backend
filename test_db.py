from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/appalta2"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    version = result.fetchone()[0]
    print(version)
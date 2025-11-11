import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()  

RENDER_DATABASE_URL = os.getenv("RENDER_DATABASE_URL")

SQLITE_DATABASE_NAME = "check_med.db"
SQLITE_DATABASE_URL = f"sqlite:///{SQLITE_DATABASE_NAME}"


# Use the render database URL if provided, otherwise fall back to the local SQLite URL
database_url = RENDER_DATABASE_URL 
engine = create_engine(database_url)


# ✅ Dependency to get DB session in routes
def get_session() :
    with Session(engine) as session:
        yield session

# ✅ Function to create tables
def init_db():
    SQLModel.metadata.create_all(bind=engine)
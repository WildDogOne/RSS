from sqlalchemy import create_engine
import os
from app.models import Base

# Get database path
database_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'rss.db')

# Create engine
engine = create_engine(f'sqlite:///{database_path}')

def migrate():
    # Create the new table
    Base.metadata.create_all(engine, tables=[Base.metadata.tables['detailed_analyses']])

if __name__ == "__main__":
    migrate()

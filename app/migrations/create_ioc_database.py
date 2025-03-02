from sqlalchemy import create_engine, text
from app.models import Base

def create_tables(engine):
    # Create IOCs table
    Base.metadata.create_all(engine, tables=[Base.metadata.tables["iocs"]])

if __name__ == "__main__":
    engine = create_engine("sqlite:///app.db")
    create_tables(engine)
    print("Created IOCs table")

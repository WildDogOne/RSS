import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

class Database:
    """Database configuration and session management."""
    
    def __init__(self, base_path: str):
        """Initialize database with the given base path."""
        # Setup database path
        self.database_path = os.path.join(base_path, "data", "rss.db")
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        
        # Create engine and session factory
        self.engine = create_engine(f"sqlite:///{self.database_path}")
        self.SessionFactory = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a new database session."""
        return self.SessionFactory()

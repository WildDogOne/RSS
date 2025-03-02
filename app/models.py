from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Feed(Base):
    __tablename__ = 'feeds'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)
    title = Column(String(200))
    last_fetched = Column(DateTime, default=datetime.utcnow)
    is_security_feed = Column(Boolean, default=False)
    entries = relationship("FeedEntry", back_populates="feed", cascade="all, delete-orphan")

class FeedEntry(Base):
    __tablename__ = 'feed_entries'
    
    id = Column(Integer, primary_key=True)
    feed_id = Column(Integer, ForeignKey('feeds.id'))
    title = Column(String(500))
    link = Column(String(500))
    published_date = Column(DateTime)
    content = Column(Text)
    summary = Column(Text)
    feed = relationship("Feed", back_populates="entries")

class SecurityAnalysis(Base):
    __tablename__ = 'security_analyses'
    
    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey('feed_entries.id'))
    iocs = Column(Text)  # JSON string of extracted IOCs
    sigma_rule = Column(Text)  # Generated Sigma rule
    analysis_date = Column(DateTime, default=datetime.utcnow)

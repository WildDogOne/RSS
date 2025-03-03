from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)
    title = Column(String(200))
    category = Column(String(200), nullable=True)
    last_fetched = Column(DateTime, default=datetime.utcnow)
    is_security_feed = Column(Boolean, default=False)
    entries = relationship(
        "FeedEntry", back_populates="feed", cascade="all, delete-orphan"
    )


class FeedEntry(Base):
    __tablename__ = "feed_entries"

    id = Column(Integer, primary_key=True)
    feed_id = Column(Integer, ForeignKey("feeds.id"))
    title = Column(String(500))
    link = Column(String(500))
    published_date = Column(DateTime)
    content = Column(Text)
    summary = Column(Text)
    is_read = Column(Boolean, default=False)
    llm_summary = Column(Text, nullable=True)  # On-demand LLM summary
    security_analysis = relationship(
        "SecurityAnalysis", uselist=False, back_populates="entry"
    )
    detailed_analysis = relationship(
        "DetailedAnalysis", uselist=False, back_populates="entry"
    )
    feed = relationship("Feed", back_populates="entries")


class SecurityAnalysis(Base):
    __tablename__ = "security_analyses"

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("feed_entries.id"))
    iocs = Column(Text)  # JSON string of extracted IOCs
    sigma_rule = Column(Text)  # Generated Sigma rule
    analysis_date = Column(DateTime, default=datetime.utcnow)
    entry = relationship("FeedEntry", back_populates="security_analysis")


class DetailedAnalysis(Base):
    __tablename__ = "detailed_analyses"

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("feed_entries.id"))
    key_points = Column(Text)
    technical_details = Column(Text)
    impact_assessment = Column(Text)
    related_concepts = Column(Text)
    recommendations = Column(Text)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    entry = relationship("FeedEntry", back_populates="detailed_analysis")


class IOC(Base):
    __tablename__ = "iocs"

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)  # e.g., IP, URL, hash, domain
    value = Column(String(500), nullable=False)
    context = Column(Text)  # Surrounding text where IOC was found
    entry_id = Column(Integer, ForeignKey("feed_entries.id"))
    discovered_date = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(Integer)  # 1-100 score
    entry = relationship("FeedEntry", backref="iocs")

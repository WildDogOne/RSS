import feedparser
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Feed, FeedEntry, SecurityAnalysis
from app.llm_service import LLMService

class FeedService:
    def __init__(self, db_session: Session, llm_service: LLMService):
        self.db = db_session
        self.llm_service = llm_service

    def add_feed(self, url: str, is_security_feed: bool = False) -> Feed:
        existing_feed = self.db.query(Feed).filter(Feed.url == url).first()
        if existing_feed:
            if existing_feed.is_security_feed != is_security_feed:
                existing_feed.is_security_feed = is_security_feed
                self.db.commit()
            return existing_feed
        
        feed = Feed(url=url, is_security_feed=is_security_feed)
        self.db.add(feed)
        self.db.commit()
        return feed

    def update_feeds(self) -> None:
        feeds = self.db.query(Feed).all()
        for feed in feeds:
            self._process_feed(feed)

    def _process_feed(self, feed: Feed) -> None:
        parsed = feedparser.parse(feed.url)
        
        # Update feed title if available
        if 'title' in parsed.feed:
            feed.title = parsed.feed.title

        for entry in parsed.entries:
            # Check if entry already exists
            existing_entry = self.db.query(FeedEntry).filter(
                FeedEntry.feed_id == feed.id,
                FeedEntry.link == entry.link
            ).first()

            if existing_entry:
                continue

            # Create new entry
            new_entry = FeedEntry(
                feed=feed,
                title=entry.get('title', ''),
                link=entry.get('link', ''),
                published_date=datetime.fromtimestamp(
                    entry.get('published_parsed', datetime.now().timestamp())
                ),
                content=entry.get('description', '')  # or entry.get('content', [{}])[0].get('value', '')
            )

            # Generate summary
            new_entry.summary = self.llm_service.summarize_article(new_entry.content)

            self.db.add(new_entry)

            # If it's a security feed, perform security analysis
            if feed.is_security_feed:
                iocs, sigma_rule = self.llm_service.analyze_security_content(new_entry.content)
                
                security_analysis = SecurityAnalysis(
                    entry_id=new_entry.id,
                    iocs=str(iocs),
                    sigma_rule=sigma_rule
                )
                self.db.add(security_analysis)

        feed.last_fetched = datetime.utcnow()
        self.db.commit()

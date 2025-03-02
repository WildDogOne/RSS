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

    def mark_as_read(self, entry_id: int) -> None:
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            entry.is_read = True
            self.db.commit()

    def generate_llm_summary(self, entry_id: int) -> str:
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            entry.llm_summary = self.llm_service.summarize_article(entry.content)
            self.db.commit()
            return entry.llm_summary
        return None

    def get_unread_entries(self, feed_id: int, limit: int = 20) -> List[FeedEntry]:
        return self.db.query(FeedEntry).filter(
            FeedEntry.feed_id == feed_id,
            FeedEntry.is_read == False
        ).order_by(FeedEntry.published_date.desc()).limit(limit).all()

    def analyze_security(self, entry_id: int) -> dict:
        """Always perform security analysis regardless of feed type."""
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            iocs, sigma_rule = self.llm_service.analyze_security_content(entry.content)
            
            # Create or update security analysis
            if not entry.security_analysis:
                entry.security_analysis = SecurityAnalysis()
            
            entry.security_analysis.iocs = str(iocs)
            entry.security_analysis.sigma_rule = sigma_rule
            entry.security_analysis.analysis_date = datetime.utcnow()
            self.db.commit()
            
            return {"iocs": iocs, "sigma_rule": sigma_rule}
        return None

    def add_feed(self, url: str, is_security_feed: bool = False, title: str = None, category: str = None) -> Feed:
        existing_feed = self.db.query(Feed).filter(Feed.url == url).first()
        if existing_feed:
            if any([
                existing_feed.is_security_feed != is_security_feed,
                (title and existing_feed.title != title),
                (category and existing_feed.category != category)
            ]):
                existing_feed.is_security_feed = is_security_feed
                if title:
                    existing_feed.title = title
                if category:
                    existing_feed.category = category
                self.db.commit()
            return existing_feed
        
        feed = Feed(
            url=url,
            is_security_feed=is_security_feed,
            title=title,
            category=category
        )
        self.db.add(feed)
        self.db.commit()
        return feed

    def update_feeds(self) -> None:
        feeds = self.db.query(Feed).all()
        for feed in feeds:
            self._process_feed(feed)

    def remove_feed(self, feed_id: int) -> None:
        feed = self.db.query(Feed).get(feed_id)
        if feed:
            self.db.delete(feed)
            self.db.commit()

    def update_feed(self, feed_id: int, category: str = None, title: str = None) -> None:
        feed = self.db.query(Feed).get(feed_id)
        if feed:
            if category is not None:
                feed.category = category
            if title is not None:
                feed.title = title
            self.db.commit()

    def _process_feed(self, feed: Feed) -> None:
        parsed = feedparser.parse(feed.url)
        
        # Update feed title if not already set
        if not feed.title and 'title' in parsed.feed:
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

            # Always perform security analysis for new entries
            iocs, sigma_rule = self.llm_service.analyze_security_content(new_entry.content)
            
            security_analysis = SecurityAnalysis(
                entry_id=new_entry.id,
                iocs=str(iocs),
                sigma_rule=sigma_rule
            )
            self.db.add(security_analysis)

        feed.last_fetched = datetime.utcnow()
        self.db.commit()

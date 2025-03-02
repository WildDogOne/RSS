import logging
import time
import feedparser
from datetime import datetime
from typing import List, Dict
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.models import Feed, FeedEntry, SecurityAnalysis, DetailedAnalysis
from app.llm_service import LLMService

# Configure feedparser debugging
feedparser.PREFERRED_XML_PARSERS = ["html.parser"]

logger = logging.getLogger(__name__)

class FeedService:
    def __init__(self, db_session: Session, llm_service: LLMService):
        self.db = db_session
        self.llm_service = llm_service
        self.last_update = None
        
        # Enable SQLAlchemy query logging in debug mode
        if logger.getEffectiveLevel() <= logging.DEBUG:
            event.listen(self.db.bind, 'before_cursor_execute', self._log_sql)

    def _log_sql(self, conn, cursor, statement, params, context, executemany):
        """Log SQL statements when in debug mode."""
        logger.debug('Executing SQL: %s', statement)

    def add_test_feed(self) -> Feed:
        """Add a test feed for debugging."""
        test_feed_url = "https://feeds.arstechnica.com/arstechnica/security"
        logger.debug(f"Adding test feed: {test_feed_url}")
        
        return self.add_feed(
            url=test_feed_url,
            title="Ars Technica Security",
            category="Security News",
            is_security_feed=True
        )

    def mark_as_read(self, entry_id: int) -> None:
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            entry.is_read = True
            self.db.commit()
            logger.debug(f"Marked entry {entry_id} as read")

    def generate_llm_summary(self, entry_id: int) -> str:
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            logger.debug(f"Generating LLM summary for entry {entry_id}")
            entry.llm_summary = self.llm_service.summarize_article(entry.content)
            self.db.commit()
            return entry.llm_summary
        return None

    def get_latest_entries(self, feed_id: int = None, category: str = None, only_unread: bool = True, limit: int = 20) -> List[FeedEntry]:
        """Get latest entries either by feed_id or category."""
        logger.debug(f"Fetching entries - feed_id: {feed_id}, category: {category}, only_unread: {only_unread}, limit: {limit}")
        query = self.db.query(FeedEntry).join(Feed)
        
        if feed_id is not None:
            logger.debug(f"Filtering by feed_id: {feed_id}")
            query = query.filter(FeedEntry.feed_id == feed_id)
        elif category is not None:
            logger.debug(f"Filtering by category: {category}")
            query = query.filter(Feed.category == category)
            
        if only_unread:
            query = query.filter(FeedEntry.is_read == False)

        entries = query.order_by(FeedEntry.published_date.desc()).limit(limit).all()
        logger.debug(f"Found {len(entries)} entries")
        return entries

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        categories = [cat[0] for cat in self.db.query(Feed.category).distinct().all() if cat[0] is not None]
        logger.debug(f"Found categories: {categories}")
        return sorted(categories)

    def get_feeds_by_category(self) -> Dict[str, List[Feed]]:
        """Get feeds grouped by category."""
        feeds = self.db.query(Feed).order_by(Feed.category, Feed.title).all()
        result = {}
        for feed in feeds:
            category = feed.category or "Uncategorized"
            if category not in result:
                result[category] = []
            result[category].append(feed)
        logger.debug(f"Found {len(feeds)} feeds in {len(result)} categories")
        return result

    def analyze_detailed_content(self, entry_id: int) -> dict:
        """Generate detailed analysis for an entry."""
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            logger.debug(f"Performing detailed analysis for entry {entry_id}")
            analysis = self.llm_service.analyze_detailed_content(entry.content)
            
            # Parse the analysis and store in structured format
            if not entry.detailed_analysis:
                entry.detailed_analysis = DetailedAnalysis()
            
            # Store the analysis
            entry.detailed_analysis.key_points = analysis
            entry.detailed_analysis.analysis_date = datetime.utcnow()
            self.db.commit()
            
            return {"analysis": analysis}
        return None

    def analyze_security(self, entry_id: int) -> dict:
        """Always perform security analysis regardless of feed type."""
        entry = self.db.query(FeedEntry).get(entry_id)
        if entry:
            logger.debug(f"Performing security analysis for entry {entry_id}")
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
        """Add a new feed and process its entries."""
        logger.debug(f"Adding feed - URL: {url}, title: {title}, category: {category}")
        try:
            # Check for existing feed
            existing_feed = self.db.query(Feed).filter(Feed.url == url).first()
            if existing_feed:
                logger.debug(f"Feed already exists, updating if needed")
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

            # Create new feed
            feed = Feed(
                url=url,
                is_security_feed=is_security_feed,
                title=title,
                category=category
            )
            self.db.add(feed)
            self.db.commit()
            logger.debug(f"Created new feed with ID: {feed.id}")

            # Process feed immediately after adding
            self._process_feed(feed)
            return feed

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding feed: {str(e)}", exc_info=True)
            raise

    def update_feeds(self) -> None:
        logger.debug("Starting feed update")
        try:
            feeds = self.db.query(Feed).all()
            for feed in feeds:
                try:
                    self._process_feed(feed)
                except Exception as e:
                    logger.error(f"Error updating feed {feed.url}: {str(e)}", exc_info=True)
            
            self.last_update = datetime.now()
            logger.debug("Feed update completed")
        except Exception as e:
            logger.error(f"Error in update_feeds: {str(e)}", exc_info=True)

    def remove_feed(self, feed_id: int) -> None:
        feed = self.db.query(Feed).get(feed_id)
        if feed:
            logger.debug(f"Removing feed {feed_id}")
            self.db.delete(feed)
            self.db.commit()

    def update_feed(self, feed_id: int, category: str = None, title: str = None) -> None:
        logger.debug(f"Updating feed {feed_id} - new category: {category}, new title: {title}")
        feed = self.db.query(Feed).get(feed_id)
        if feed:
            if category is not None:
                feed.category = category
            if title is not None:
                feed.title = title
            self.db.commit()

    def _process_feed(self, feed: Feed) -> None:
        """Process a feed and store its entries."""
        logger.debug(f"Processing feed {feed.url}")
        try:
            # Initial feed parsing with detailed logging
            logger.debug(f"Fetching feed from {feed.url}")
            try:
                parsed = feedparser.parse(feed.url)
                
                # Log all feed attributes for debugging
                logger.debug("Feed parsing details:")
                logger.debug(f"Status: {getattr(parsed, 'status', 'unknown')}")
                logger.debug(f"Version: {getattr(parsed, 'version', 'unknown')}")
                logger.debug(f"Encoding: {getattr(parsed, 'encoding', 'unknown')}")
                logger.debug(f"Bozo: {getattr(parsed, 'bozo', 'unknown')}")
                
                if hasattr(parsed, 'bozo_exception'):
                    raise Exception(f"Feed parse error: {parsed.bozo_exception}")
                
                if not hasattr(parsed, 'feed') or not hasattr(parsed, 'entries'):
                    raise Exception(f"Invalid feed format: missing feed or entries")
                
                logger.debug(f"Feed metadata: {parsed.feed}")
                if hasattr(parsed, 'debug_message'):
                    logger.debug(f"Feedparser debug: {parsed.debug_message}")
                    
            except Exception as e:
                logger.error(f"Error parsing feed {feed.url}: {str(e)}")
                return
            
            if hasattr(parsed, 'status') and parsed.status >= 400:
                logger.error(f"Feed error: HTTP {parsed.status}")
                return

            # Update feed title if not already set
            if hasattr(parsed, 'feed'):
                if 'title' in parsed.feed:
                    if not feed.title:
                        feed.title = parsed.feed.title
                        logger.debug(f"Updated feed title to: {feed.title}")
                logger.debug(f"Feed info - Title: {getattr(parsed.feed, 'title', None)}, Link: {getattr(parsed.feed, 'link', None)}")

            if not hasattr(parsed, 'entries'):
                logger.error("No entries found in feed")
                return

            entries_added = 0
            logger.debug(f"Found {len(parsed.entries)} entries in feed")

            for entry in parsed.entries:
                try:
                    # Check if entry already exists
                    entry_link = getattr(entry, 'link', None)
                    logger.debug(f"Processing entry: {getattr(entry, 'title', 'unknown')} - {entry_link}")
                    
                    if not entry_link:
                        logger.warning(f"Entry has no link, skipping: {getattr(entry, 'title', 'unknown')}")
                        continue

                    existing_entry = self.db.query(FeedEntry).filter(
                        FeedEntry.feed_id == feed.id,
                        FeedEntry.link == entry_link
                    ).first()

                    if existing_entry:
                        logger.debug(f"Entry already exists: {getattr(entry, 'title', 'unknown')}")
                        continue

                    # Handle published date
                    published_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        logger.debug(f"Using published date: {published_date}")
                    else:
                        published_date = datetime.now()
                        logger.debug("No published_parsed date, using current time")
                    
                    # Handle content
                    content = None
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].get('value', '')
                        logger.debug("Found content in entry.content")
                    elif hasattr(entry, 'description'):
                        content = entry.description
                        logger.debug("Found content in entry.description")
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                        logger.debug("Found content in entry.summary")
                    else:
                        content = str(entry)
                        logger.debug("No content found, using entry string representation")
                    
                    new_entry = FeedEntry(
                        feed=feed,
                        title=getattr(entry, 'title', ''),
                        link=entry_link,
                        published_date=published_date,
                        content=content
                    )

                    # Add and flush to get ID
                    self.db.add(new_entry)
                    self.db.flush()
                    logger.debug(f"Added entry to session with ID: {new_entry.id}")

                    # Set initial summary
                    new_entry.summary = new_entry.content[:300] + "..."

                    # Only perform security analysis immediately for security feeds
                    if feed.is_security_feed:
                        try:
                            iocs, sigma_rule = self.llm_service.analyze_security_content(new_entry.content)
                            logger.debug("Security analysis completed")
                            
                            security_analysis = SecurityAnalysis(
                                entry_id=new_entry.id,
                                iocs=str(iocs),
                                sigma_rule=sigma_rule
                            )
                            self.db.add(security_analysis)
                        except Exception as e:
                            logger.error(f"Error in security analysis: {str(e)}")

                    entries_added += 1
                    self.db.commit()
                    logger.debug(f"Committed entry {new_entry.id}")

                except Exception as e:
                    logger.error(f"Error processing entry: {str(e)}", exc_info=True)
                    self.db.rollback()
                    continue

            logger.debug(f"Added {entries_added} new entries for feed {feed.url}")
            feed.last_fetched = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            logger.error(f"Error processing feed {feed.url}: {str(e)}", exc_info=True)
            self.db.rollback()

import os
import json
import logging
import time
import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from apscheduler.schedulers.background import BackgroundScheduler
from app.models import Base, Feed, FeedEntry, SecurityAnalysis
from app.feed_service import FeedService
from app.llm_service import LLMService

# Setup logging
class StreamToList:
    def __init__(self):
        self.logs = []
    
    def write(self, text):
        log_entry = {"timestamp": datetime.now(), "message": text.strip()}
        if log_entry["message"]:  # Only add non-empty messages
            self.logs.append(log_entry)
        return len(text)
    
    def flush(self):
        pass

    def get_logs(self, limit=None):
        logs = sorted(self.logs, key=lambda x: x["timestamp"], reverse=True)
        return logs[:limit] if limit else logs

    def clear(self):
        self.logs = []

# Create memory handler for webapp
memory_stream = StreamToList()
memory_handler = logging.StreamHandler(memory_stream)
memory_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Setup root logger with debug output capture
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove default handlers
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(console_handler)
root_logger.addHandler(memory_handler)

logger = logging.getLogger(__name__)

# Database setup
database_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'rss.db')
os.makedirs(os.path.dirname(database_path), exist_ok=True)
engine = create_engine(f'sqlite:///{database_path}')
Base.metadata.create_all(engine)
SessionFactory = sessionmaker(bind=engine)

# Load or create config file
CONFIG_FILE = os.path.join(os.path.dirname(database_path), 'config.json')
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {
        "ollama_url": "http://localhost:11434",
        "ollama_model": "mistral",
        "debug_enabled": False,
        "log_level": "INFO"
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Initialize configuration
config = load_config()
if 'ollama_url' not in st.session_state:
    st.session_state.ollama_url = config["ollama_url"]
if 'ollama_model' not in st.session_state:
    st.session_state.ollama_model = config["ollama_model"]
if 'settings_open' not in st.session_state:
    st.session_state.settings_open = False
if 'console_open' not in st.session_state:
    st.session_state.console_open = False
if 'debug_enabled' not in st.session_state:
    st.session_state.debug_enabled = config.get("debug_enabled", False)
if 'log_level' not in st.session_state:
    st.session_state.log_level = config.get("log_level", "INFO")
if 'selected_feed' not in st.session_state:
    st.session_state.selected_feed = None
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'entries'

# Set initial log level and SQLAlchemy logging
root_logger.setLevel(getattr(logging, st.session_state.log_level))

# Enable SQLAlchemy logging in debug mode
if st.session_state.debug_enabled:
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)

def update_log_settings(debug_enabled: bool, log_level: str):
    """Update logging configuration."""
    st.session_state.debug_enabled = debug_enabled
    st.session_state.log_level = log_level
    
    # Update root logger level
    root_logger.setLevel(getattr(logging, log_level))
    
    # Configure SQLAlchemy logging based on debug mode
    if debug_enabled:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    logger.debug(f"Updated log settings - debug: {debug_enabled}, level: {log_level}")
    
    # Save configuration
    save_config({
        "ollama_url": st.session_state.ollama_url,
        "ollama_model": st.session_state.ollama_model,
        "debug_enabled": debug_enabled,
        "log_level": log_level
    })

def render_header_and_controls(llm_service: LLMService, feed_service: FeedService):
    """Render header with controls."""
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.title("RSS Feed Reader")
    with col2:
        if st.button("⚙️", help="Settings"):
            st.session_state.settings_open = not st.session_state.settings_open
    with col3:
        if st.button("🔄", help="Update All Feeds"):
            with st.spinner("Updating feeds..."):
                try:
                    logger.debug("Manual feed update triggered")
                    feed_service.update_feeds()
                    st.success("Feeds updated successfully")
                except Exception as e:
                    logger.error(f"Error updating feeds: {str(e)}", exc_info=True)
                    st.error(f"Error updating feeds: {str(e)}")
                st.rerun()
    with col4:
        if st.button("🖥️", help="Toggle Console"):
            st.session_state.console_open = not st.session_state.console_open

def render_settings_modal(llm_service: LLMService, feed_service: FeedService):
    """Render settings modal with Ollama config and feed management."""
    if st.session_state.settings_open:
        st.markdown("""
            <style>
                div[data-testid="stMarkdownContainer"] div.settings-section {
                    background-color: #f8f9fa;
                    padding: 1.5rem;
                    border-radius: 0.5rem;
                    margin: 1rem 0;
                    border: 1px solid #dee2e6;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <div class="settings-section">
            <h2 style="margin-top: 0;">⚙️ Settings</h2>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            # Debug Settings first for easier access
            st.subheader("Debug Settings")
            col1, col2 = st.columns([3, 1])
            with col1:
                debug_enabled = st.checkbox("Enable Debug Mode", value=st.session_state.debug_enabled)
                log_level = st.selectbox("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"], 
                                       index=["DEBUG", "INFO", "WARNING", "ERROR"].index(st.session_state.log_level))
                # Immediately apply debug settings
                if (debug_enabled != st.session_state.debug_enabled or 
                    log_level != st.session_state.log_level):
                    update_log_settings(debug_enabled, log_level)
                    st.rerun()
            with col2:
                if st.button("🧪 Test Feed"):
                    try:
                        logger.debug("Adding test feed")
                        feed = feed_service.add_test_feed()
                        if feed:
                            st.success(f"Test feed added: {feed.title}")
                            logger.debug(f"Test feed added successfully: {feed.id}")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error adding test feed: {str(e)}", exc_info=True)
                        st.error(f"Error adding test feed: {str(e)}")
            
            st.markdown("---")

            st.subheader("Ollama Configuration")
            st.text_input("Ollama URL", value=st.session_state.ollama_url, key="new_url")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                available_models = llm_service.get_available_models()
                selected_model = st.selectbox("Model", options=available_models, 
                    index=available_models.index(st.session_state.ollama_model) if st.session_state.ollama_model in available_models else 0)
            with col2:
                if st.button("🔄 Refresh Models"):
                    st.rerun()
            
            if selected_model != st.session_state.ollama_model or st.session_state.ollama_url != st.session_state.get("new_url"):
                st.session_state.ollama_url = st.session_state.get("new_url")
                st.session_state.ollama_model = selected_model
                llm_service.update_config(st.session_state.ollama_url, selected_model)
                save_config({
                    "ollama_url": st.session_state.ollama_url,
                    "ollama_model": selected_model,
                    "debug_enabled": st.session_state.debug_enabled,
                    "log_level": st.session_state.log_level
                })

            st.subheader("Add New Feed")
            new_feed_url = st.text_input("Feed URL")
            new_feed_title = st.text_input("Feed Title (optional)")
            new_feed_category = st.text_input("Category (optional)")
            if st.button("Add Feed"):
                if new_feed_url:
                    try:
                        logger.debug(f"Adding new feed: {new_feed_url}")
                        feed = feed_service.add_feed(
                            url=new_feed_url,
                            title=new_feed_title if new_feed_title else None,
                            category=new_feed_category if new_feed_category else None
                        )
                        st.success(f"Feed added successfully{' and entries loaded' if feed else ''}")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error adding feed: {str(e)}", exc_info=True)
                        st.error(f"Error adding feed: {str(e)}")
                else:
                    st.error("Please enter a feed URL")
            
            st.subheader("Import from OPML")
            uploaded_file = st.file_uploader("Choose an OPML file", type="opml")
            if uploaded_file is not None:
                try:
                    logger.debug("Processing OPML file")
                    tree = ET.parse(uploaded_file)
                    root = tree.getroot()
                    imported_count = 0

                    # Process categories (top-level outlines)
                    for category_outline in root.findall("./body/outline"):
                        category = category_outline.get('text') or category_outline.get('title')
                        logger.debug(f"Processing category: {category}")
                        
                        # Process feeds within this category
                        for feed_outline in category_outline.findall("outline"):
                            feed_url = feed_outline.get('xmlUrl')
                            if feed_url:
                                title = feed_outline.get('text') or feed_outline.get('title')
                                logger.debug(f"Adding feed: {title} ({feed_url})")
                                feed_service.add_feed(url=feed_url, title=title, category=category)
                                imported_count += 1
                    st.success(f"Successfully imported {imported_count} feeds from OPML file!")
                except ET.ParseError:
                    logger.error("Invalid OPML file")
                    st.error("Invalid OPML file")
                except Exception as e:
                    logger.error(f"Error importing OPML: {str(e)}", exc_info=True)
                    st.error(f"Error importing OPML: {str(e)}")

def render_sidebar(feed_service: FeedService):
    """Render sidebar with feed categories."""
    st.sidebar.title("Feeds")
    
    # Reset selection button
    if st.sidebar.button("🏠 Show All"):
        logger.debug("Reset feed selection")
        st.session_state.selected_feed = None
        st.session_state.selected_category = None
        st.rerun()

    # Get feeds grouped by category
    feeds_by_category = feed_service.get_feeds_by_category()
    
    for category, feeds in feeds_by_category.items():
        st.sidebar.markdown(f"### {category}")
        
        # Category selection
        if st.sidebar.button(f"📁 All in {category}", key=f"cat_{category}"):
            logger.debug(f"Selected category: {category}")
            st.session_state.selected_category = category
            st.session_state.selected_feed = None
            st.rerun()
        
        # Individual feeds
        for feed in feeds:
            if st.sidebar.button(f"📰 {feed.title or feed.url}", key=f"feed_{feed.id}"):
                logger.debug(f"Selected feed: {feed.id} ({feed.title})")
                st.session_state.selected_feed = feed.id
                st.session_state.selected_category = None
                st.rerun()

def render_console():
    """Render debug console in right sidebar."""
    if st.session_state.console_open:
        # Add global styles for the console
        st.markdown("""
            <style>
                /* Right sidebar styling */
                section[data-testid="stSidebar"][aria-label="Console"] {
                    right: 0;
                    width: 400px !important;
                    background-color: #f8f9fa;
                    border-left: 1px solid #dee2e6;
                }
                /* Console log styling */
                div.console-log {
                    background-color: #ffffff;
                    border-radius: 4px;
                    padding: 4px 8px;
                    margin: 2px 0;
                    font-family: 'Courier New', monospace;
                    font-size: 0.8em;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
            </style>
        """, unsafe_allow_html=True)

        # Create a new sidebar for the console
        with st.sidebar:
            st.markdown("### 🖥️ Debug Console")
            if st.session_state.debug_enabled:
                # Console controls in a compact layout
                col1, col2 = st.columns([4, 1])
                with col1:
                    filter_text = st.text_input("🔍", placeholder="Filter logs...", label_visibility="collapsed")
                with col2:
                    if st.button("🗑️", help="Clear logs"):
                        memory_stream.clear()
                        st.rerun()

                # Close button in top right
                st.markdown(
                    """<div style="position: absolute; top: 0; right: 0; padding: 1rem;">
                        <button class="close-button">❌</button>
                    </div>""",
                    unsafe_allow_html=True
                )

                # Display filtered logs with improved styling
                logs = memory_stream.get_logs(limit=1000)
                for log in logs:
                    log_text = f"{log['timestamp'].strftime('%H:%M:%S')} - {log['message']}"
                    if not filter_text or filter_text.lower() in log_text.lower():
                        st.markdown(
                            f'<div class="console-log">{log_text}</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.warning("Debug logging is disabled. Enable it in Settings to view logs.")

def render_ioc_view(feed_service: FeedService):
    """Render IOC view."""
    st.header("🛡️ Indicators of Compromise")
    
    # Get all IOCs
    iocs = feed_service.get_all_iocs()
    
    if not iocs:
        st.info("No IOCs found")
        return
    
    # Display IOCs with filtering options
    ioc_types = list(set(ioc["type"] for ioc in iocs))
    selected_type = st.selectbox("Filter by type", ["All"] + ioc_types)
    
    filtered_iocs = iocs
    if selected_type != "All":
        filtered_iocs = [ioc for ioc in iocs if ioc["type"] == selected_type]
    
    for ioc in filtered_iocs:
        with st.expander(f"{ioc['type']}: {ioc['value']}", expanded=True):
            st.write(f"Found in: {ioc['article_title']}")
            if ioc['context']:
                st.markdown("**Context:**")
                st.write(ioc['context'])
            st.caption(f"Discovered: {ioc['discovered_date']}")
            st.progress(ioc['confidence_score'] / 100, text=f"Confidence: {ioc['confidence_score']}%")

def render_entries(feed_service: FeedService, db_session: Session):
    """Render feed entries based on selection."""
    # View controls
    control_cols = st.columns([2, 2, 2])
    with control_cols[0]:
        show_read = st.checkbox("Show read entries", help="Include entries that have been marked as read")
    with control_cols[1]:
        limit = st.selectbox("Entries per feed", [10, 20, 50, 100], 1, help="Maximum number of entries to show")
    with control_cols[2]:
        last_update = getattr(feed_service, 'last_update', None)
        if last_update:
            st.caption(f"Last updated: {last_update.strftime('%H:%M:%S')}")

    # Debug info in a styled container
    if st.session_state.debug_enabled:
        st.markdown("""
            <style>
                div[data-testid="stMarkdownContainer"] > div.debug-info {
                    background-color: #f0f2f6;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin: 1rem 0;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="debug-info">', unsafe_allow_html=True)
        st.markdown("#### 🐛 Debug Info")
        st.json({
            "selected_feed": st.session_state.selected_feed,
            "selected_category": st.session_state.selected_category,
            "settings_open": st.session_state.settings_open,
            "debug_enabled": st.session_state.debug_enabled,
            "log_level": st.session_state.log_level,
            "show_read": show_read,
            "limit": limit,
            "last_update": last_update.isoformat() if last_update else None
        })
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")  # Add separator

    if st.session_state.selected_feed:
        # Show entries for selected feed
        entries = feed_service.get_latest_entries(feed_id=st.session_state.selected_feed, only_unread=not show_read, limit=limit)
        feed = db_session.query(Feed).get(st.session_state.selected_feed)
        st.header(f"Latest from {feed.title or feed.url}")
    elif st.session_state.selected_category:
        # Show entries for selected category
        entries = feed_service.get_latest_entries(category=st.session_state.selected_category, only_unread=not show_read, limit=limit)
        st.header(f"Latest from {st.session_state.selected_category}")
    else:
        # Show all latest entries
        entries = feed_service.get_latest_entries(feed_id=None, category=None, only_unread=not show_read, limit=limit)
        st.header("Latest Entries")

    logger.debug(f"Displaying {len(entries) if entries else 0} entries")

    if not entries:
        st.info("No entries to display.")
        return

    for entry in entries:
        with st.expander(f"{entry.title}", expanded=True):
            st.markdown(f"*{entry.feed.category} / {entry.feed.title}* - {entry.published_date.strftime('%Y-%m-%d %H:%M')}")
            
            # Summary
            summary_col1, summary_col2 = st.columns([6, 1])
            with summary_col1:
                if entry.llm_summary:
                    st.write(entry.llm_summary)
                else:
                    st.write(entry.summary or entry.content[:300] + "...")
            with summary_col2:
                if entry.llm_summary:
                    if st.button("🔄 Refresh", key=f"refresh_summary_{entry.id}"):
                        with st.spinner("Refreshing summary..."):
                            feed_service.generate_llm_summary(entry.id)
                        st.rerun()
                else:
                    if st.button("🤖 Generate", key=f"llm_{entry.id}"):
                        with st.spinner("Generating summary..."):
                            feed_service.generate_llm_summary(entry.id)
                        st.rerun()
            
            st.markdown(f"[Read More]({entry.link})")
            
            # Security Analysis section and Button
            security_col1, security_col2 = st.columns([6, 1])
            with security_col1:
                if entry.security_analysis:
                    st.markdown("#### 🛡️ Security Analysis")
                    try:
                        iocs = eval(entry.security_analysis.iocs)
                        if iocs:
                            st.markdown("**IOCs Found:**")
                            # Create a nicely formatted table view of IOCs
                            ioc_data = []
                            for ioc in iocs:
                                ioc_data.append({
                                    "Type": ioc['type'],
                                    "Value": ioc['value'],
                                    "Confidence": f"{ioc.get('confidence', 100)}%"
                                })
                            df = pd.DataFrame(ioc_data)
                            st.table(df)
                            
                            # Show context for each IOC in expandable sections
                            st.markdown("**IOC Context:**")
                            for ioc in iocs:
                                with st.expander(f"{ioc['type']}: {ioc['value']}", expanded=False):
                                    if ioc.get('context'):
                                        st.write(ioc['context'])
                    except Exception as e:
                        st.error(f"Error displaying IOCs: {str(e)}")

                    if entry.security_analysis.sigma_rule and entry.security_analysis.sigma_rule != "No applicable Sigma rule for this content.":
                        st.markdown("**Sigma Rule:**")
                        st.code(entry.security_analysis.sigma_rule, language="yaml")
            
            with security_col2:
                button_key = f"sec_{entry.id}"
                if entry.security_analysis:
                    if st.button("🔄 Refresh", key=f"refresh_{button_key}"):
                        with st.spinner("Refreshing security analysis..."):
                            feed_service.analyze_security(entry.id)
                        st.rerun()
                else:
                    if st.button("🛡️ Analyze", key=button_key):
                        with st.spinner("Analyzing..."):
                            feed_service.analyze_security(entry.id)
                        st.rerun()

            # Detailed Content Analysis Button
            if st.button("🔍 Analyze Content", key=f"analyze_{entry.id}"):
                with st.spinner("Analyzing content..."):
                    result = feed_service.analyze_detailed_content(entry.id)
                st.rerun()
            
            # Show Detailed Analysis if available
            if entry.detailed_analysis:
                st.markdown("#### 🔍 Content Analysis")
                st.markdown(entry.detailed_analysis.key_points)
            
            # Mark as read button
            if not entry.is_read:
                if st.button("📖 Mark as Read", key=f"read_{entry.id}"):
                    feed_service.mark_as_read(entry.id)
                    st.rerun()

def main():
    logger.debug("Starting RSS Feed Reader")
    # Create a new session for this request
    db_session = SessionFactory()
    
    # Initialize services
    llm_service = LLMService(st.session_state.ollama_url, st.session_state.ollama_model)
    feed_service = FeedService(db_session, llm_service)
    
    try:
        # Initialize scheduler if not already running
        if st.session_state.scheduler is None:
            logger.debug("Initializing background scheduler")
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                lambda: FeedService(SessionFactory(), LLMService(st.session_state.ollama_url, st.session_state.ollama_model)).update_feeds(),
                'interval', 
                minutes=30
            )
            scheduler.start()
            st.session_state.scheduler = scheduler

        # Render header with controls
        render_header_and_controls(llm_service, feed_service)
        
        # Render settings if open
        if st.session_state.settings_open:
            render_settings_modal(llm_service, feed_service)

        # Render main content and sidebars
        render_sidebar(feed_service)
        
        # View selector
        current_view = st.radio("View", options=["Entries", "IOCs"], horizontal=True)
        
        # Render selected view
        if current_view == "Entries":
            render_entries(feed_service, db_session)
        else:
            render_ioc_view(feed_service)
            
        render_console()
            
    finally:
        # Close the session when we're done
        db_session.close()

if __name__ == "__main__":
    main()

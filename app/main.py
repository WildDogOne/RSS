import os
import logging
import time
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import Config
from app.database import Database
from app.logging_config import LoggingManager
from app.ui_components import (
    render_header_and_controls,
    render_settings_modal,
    render_sidebar,
    render_console,
    render_entries,
    render_ioc_view,
)
from app.feed_service import FeedService
from app.llm_service import LLMService

# Get base path for configuration
base_path = os.path.join(os.path.dirname(__file__), "..")

# Initialize core components
config = Config(base_path)
database = Database(base_path)
logging_manager = LoggingManager()

# Get logger for this module
logger = logging.getLogger(__name__)

# Initialize session state
if "ollama_url" not in st.session_state:
    st.session_state.ollama_url = config.get("ollama_url")
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = config.get("ollama_model")
if "settings_open" not in st.session_state:
    st.session_state.settings_open = False
if "console_open" not in st.session_state:
    st.session_state.console_open = False
if "debug_enabled" not in st.session_state:
    st.session_state.debug_enabled = config.get("debug_enabled", False)
if "log_level" not in st.session_state:
    st.session_state.log_level = config.get("log_level", "INFO")
if "selected_feed" not in st.session_state:
    st.session_state.selected_feed = None
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "scheduler" not in st.session_state:
    st.session_state.scheduler = None
if "current_view" not in st.session_state:
    st.session_state.current_view = "entries"
if "config" not in st.session_state:
    st.session_state.config = config
if "logging_manager" not in st.session_state:
    st.session_state.logging_manager = logging_manager
if "logger" not in st.session_state:
    st.session_state.logger = logger

# Set initial log level
logging_manager.update_settings(st.session_state.debug_enabled, st.session_state.log_level)

def main():
    logger.debug("Starting RSS Feed Reader")
    
    # Create a new session for this request
    db_session = database.get_session()

    # Initialize services
    llm_service = LLMService(st.session_state.ollama_url, st.session_state.ollama_model)
    feed_service = FeedService(db_session, llm_service)

    try:
        # Initialize scheduler if not already running
        if st.session_state.scheduler is None:
            logger.debug("Initializing background scheduler")
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                lambda: FeedService(
                    database.get_session(),
                    LLMService(
                        st.session_state.ollama_url,
                        st.session_state.ollama_model
                    ),
                ).update_feeds(),
                "interval",
                minutes=30,
            )
            scheduler.start()
            st.session_state.scheduler = scheduler

        # Render UI components
        render_header_and_controls(llm_service, feed_service)

        if st.session_state.settings_open:
            render_settings_modal(llm_service, feed_service)

        render_sidebar(feed_service)

        # View selector
        current_view = st.radio("View", options=["Entries", "IOCs"], horizontal=True)

        # Render selected view
        if current_view == "Entries":
            render_entries(feed_service, db_session)
        else:
            render_ioc_view(feed_service)

        # Render debug console if enabled
        render_console(logging_manager.get_memory_stream())

    finally:
        # Close the session when we're done
        db_session.close()

if __name__ == "__main__":
    main()

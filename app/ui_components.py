import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Feed
from app.feed_service import FeedService
from app.llm_service import LLMService
from app.logging_config import StreamToList

def render_header_and_controls(llm_service: LLMService, feed_service: FeedService) -> None:
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
                    st.session_state.logger.debug("Manual feed update triggered")
                    feed_service.update_feeds()
                    st.success("Feeds updated successfully")
                except Exception as e:
                    st.session_state.logger.error(f"Error updating feeds: {str(e)}", exc_info=True)
                    st.error(f"Error updating feeds: {str(e)}")
                st.rerun()
    with col4:
        if st.button("🖥️", help="Toggle Console"):
            st.session_state.console_open = not st.session_state.console_open

def render_settings_modal(llm_service: LLMService, feed_service: FeedService) -> None:
    """Render settings modal with Ollama config and feed management."""
    if not st.session_state.settings_open:
        return

    st.markdown(
        """
        <style>
            div[data-testid="stMarkdownContainer"] div.settings-section {
                background-color: #f8f9fa;
                padding: 1.5rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
                border: 1px solid #dee2e6;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="settings-section">
        <h2 style="margin-top: 0;">⚙️ Settings</h2>
        </div>
    """,
        unsafe_allow_html=True,
    )

    with st.container():
        # Debug Settings
        st.subheader("Debug Settings")
        col1, col2 = st.columns([3, 1])
        with col1:
            debug_enabled = st.checkbox(
                "Enable Debug Mode", value=st.session_state.debug_enabled
            )
            log_level = st.selectbox(
                "Log Level",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                index=["DEBUG", "INFO", "WARNING", "ERROR"].index(
                    st.session_state.log_level
                ),
            )
            if (
                debug_enabled != st.session_state.debug_enabled
                or log_level != st.session_state.log_level
            ):
                st.session_state.logging_manager.update_settings(debug_enabled, log_level)
                st.session_state.debug_enabled = debug_enabled
                st.session_state.log_level = log_level
                st.session_state.config.update({
                    "debug_enabled": debug_enabled,
                    "log_level": log_level
                })
                st.rerun()
        with col2:
            if st.button("🧪 Test Feed"):
                try:
                    st.session_state.logger.debug("Adding test feed")
                    feed = feed_service.add_test_feed()
                    if feed:
                        st.success(f"Test feed added: {feed.title}")
                        st.session_state.logger.debug(f"Test feed added successfully: {feed.id}")
                    st.rerun()
                except Exception as e:
                    st.session_state.logger.error(f"Error adding test feed: {str(e)}", exc_info=True)
                    st.error(f"Error adding test feed: {str(e)}")

        st.markdown("---")

        # Ollama Configuration
        st.subheader("Ollama Configuration")
        new_url = st.text_input(
            "Ollama URL", value=st.session_state.ollama_url, key="new_url"
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            available_models = llm_service.get_available_models()
            selected_model = st.selectbox(
                "Model",
                options=available_models,
                index=(
                    available_models.index(st.session_state.ollama_model)
                    if st.session_state.ollama_model in available_models
                    else 0
                ),
            )
        with col2:
            if st.button("🔄 Refresh Models"):
                st.rerun()

        if (
            selected_model != st.session_state.ollama_model
            or new_url != st.session_state.ollama_url
        ):
            st.session_state.ollama_url = new_url
            st.session_state.ollama_model = selected_model
            llm_service.update_config(new_url, selected_model)
            st.session_state.config.update({
                "ollama_url": new_url,
                "ollama_model": selected_model
            })

        # Feed Management
        st.subheader("Add New Feed")
        new_feed_url = st.text_input("Feed URL")
        new_feed_title = st.text_input("Feed Title (optional)")
        new_feed_category = st.text_input("Category (optional)")
        if st.button("Add Feed"):
            if new_feed_url:
                try:
                    st.session_state.logger.debug(f"Adding new feed: {new_feed_url}")
                    feed = feed_service.add_feed(
                        url=new_feed_url,
                        title=new_feed_title if new_feed_title else None,
                        category=new_feed_category if new_feed_category else None,
                    )
                    st.success(f"Feed added successfully{' and entries loaded' if feed else ''}")
                    st.rerun()
                except Exception as e:
                    st.session_state.logger.error(f"Error adding feed: {str(e)}", exc_info=True)
                    st.error(f"Error adding feed: {str(e)}")
            else:
                st.error("Please enter a feed URL")

        # OPML Import
        st.subheader("Import from OPML")
        uploaded_file = st.file_uploader("Choose an OPML file", type="opml")
        if uploaded_file is not None:
            try:
                st.session_state.logger.debug("Processing OPML file")
                tree = ET.parse(uploaded_file)
                root = tree.getroot()
                imported_count = 0

                for category_outline in root.findall("./body/outline"):
                    category = category_outline.get("text") or category_outline.get("title")
                    st.session_state.logger.debug(f"Processing category: {category}")

                    for feed_outline in category_outline.findall("outline"):
                        feed_url = feed_outline.get("xmlUrl")
                        if feed_url:
                            title = feed_outline.get("text") or feed_outline.get("title")
                            st.session_state.logger.debug(f"Adding feed: {title} ({feed_url})")
                            feed_service.add_feed(
                                url=feed_url, title=title, category=category
                            )
                            imported_count += 1
                st.success(f"Successfully imported {imported_count} feeds from OPML file!")
            except ET.ParseError:
                st.session_state.logger.error("Invalid OPML file")
                st.error("Invalid OPML file")
            except Exception as e:
                st.session_state.logger.error(f"Error importing OPML: {str(e)}", exc_info=True)
                st.error(f"Error importing OPML: {str(e)}")

def render_sidebar(feed_service: FeedService) -> None:
    """Render sidebar with feed categories."""
    st.sidebar.title("Feeds")

    if st.sidebar.button("🏠 Show All"):
        st.session_state.logger.debug("Reset feed selection")
        st.session_state.selected_feed = None
        st.session_state.selected_category = None
        st.rerun()

    feeds_by_category = feed_service.get_feeds_by_category()

    for category, feeds in feeds_by_category.items():
        st.sidebar.markdown(f"### {category}")

        if st.sidebar.button(f"📁 All in {category}", key=f"cat_{category}"):
            st.session_state.logger.debug(f"Selected category: {category}")
            st.session_state.selected_category = category
            st.session_state.selected_feed = None
            st.rerun()

        for feed in feeds:
            if st.sidebar.button(f"📰 {feed.title or feed.url}", key=f"feed_{feed.id}"):
                st.session_state.logger.debug(f"Selected feed: {feed.id} ({feed.title})")
                st.session_state.selected_feed = feed.id
                st.session_state.selected_category = None
                st.rerun()

def render_console(memory_stream: StreamToList) -> None:
    """Render debug console in right sidebar."""
    if not st.session_state.console_open:
        return

    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"][aria-label="Console"] {
                right: 0;
                width: 400px !important;
                background-color: #f8f9fa;
                border-left: 1px solid #dee2e6;
            }
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
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### 🖥️ Debug Console")
        if st.session_state.debug_enabled:
            col1, col2 = st.columns([4, 1])
            with col1:
                filter_text = st.text_input(
                    "🔍", placeholder="Filter logs...", label_visibility="collapsed"
                )
            with col2:
                if st.button("🗑️", help="Clear logs"):
                    memory_stream.clear()
                    st.rerun()

            logs = memory_stream.get_logs(limit=1000)
            for log in logs:
                log_text = f"{log['timestamp'].strftime('%H:%M:%S')} - {log['message']}"
                if not filter_text or filter_text.lower() in log_text.lower():
                    st.markdown(
                        f'<div class="console-log">{log_text}</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.warning("Debug logging is disabled. Enable it in Settings to view logs.")

def render_ioc_view(feed_service: FeedService) -> None:
    """Render IOC view with flat layout."""
    st.header("🛡️ Indicators of Compromise")

    iocs = feed_service.get_all_iocs()
    if not iocs:
        st.info("No IOCs found")
        return

    ioc_types = list(set(ioc["type"] for ioc in iocs))
    selected_type = st.selectbox("Filter by type", ["All"] + ioc_types)

    filtered_iocs = iocs if selected_type == "All" else [ioc for ioc in iocs if ioc["type"] == selected_type]

    for ioc in filtered_iocs:
        st.markdown(
            f"""
            <div style="border: 1px solid #e2e8f0; padding: 1rem; margin-bottom: 1rem; border-radius: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <strong style="color: #e53e3e;">🔍 {ioc['type']}: {ioc['value']}</strong>
                    <span style="color: #718096; font-size: 0.875rem;">{ioc['discovered_date']}</span>
                </div>
                <p style="margin: 0.5rem 0; color: #4a5568;">Found in: {ioc['article_title']}</p>
                <div style="margin-top: 0.5rem;">
                    <div style="font-weight: 500; color: #2d3748;">Context:</div>
                    <div style="background: #f7fafc; padding: 0.75rem; border-radius: 0.25rem; margin-top: 0.25rem;">
                        {ioc['context'] if ioc['context'] else 'No context available'}
                    </div>
                </div>
                <div style="margin-top: 0.5rem;">
                    <div style="background: #ebf8ff; padding: 0.5rem; border-radius: 0.25rem;">
                        Confidence: {ioc['confidence_score']}%
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def render_entries(feed_service: FeedService, db_session: Session) -> None:
    """Render feed entries based on selection."""
    control_cols = st.columns([2, 2, 2])
    with control_cols[0]:
        show_read = st.checkbox(
            "Show read entries", help="Include entries that have been marked as read"
        )
    with control_cols[1]:
        limit = st.selectbox(
            "Entries per feed",
            [10, 20, 50, 100],
            1,
            help="Maximum number of entries to show",
        )
    with control_cols[2]:
        last_update = getattr(feed_service, "last_update", None)
        if last_update:
            st.caption(f"Last updated: {last_update.strftime('%H:%M:%S')}")

    if st.session_state.debug_enabled:
        st.markdown(
            """
            <style>
                div[data-testid="stMarkdownContainer"] > div.debug-info {
                    background-color: #f0f2f6;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin: 1rem 0;
                }
            </style>
        """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="debug-info">', unsafe_allow_html=True)
        st.markdown("#### 🐛 Debug Info")
        st.json(
            {
                "selected_feed": st.session_state.selected_feed,
                "selected_category": st.session_state.selected_category,
                "settings_open": st.session_state.settings_open,
                "debug_enabled": st.session_state.debug_enabled,
                "log_level": st.session_state.log_level,
                "show_read": show_read,
                "limit": limit,
                "last_update": last_update.isoformat() if last_update else None,
            }
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Get entries based on selection
    if st.session_state.selected_feed:
        entries = feed_service.get_latest_entries(
            feed_id=st.session_state.selected_feed,
            only_unread=not show_read,
            limit=limit,
        )
        feed = db_session.query(Feed).get(st.session_state.selected_feed)
        st.header(f"Latest from {feed.title or feed.url}")
    elif st.session_state.selected_category:
        entries = feed_service.get_latest_entries(
            category=st.session_state.selected_category,
            only_unread=not show_read,
            limit=limit,
        )
        st.header(f"Latest from {st.session_state.selected_category}")
    else:
        entries = feed_service.get_latest_entries(
            feed_id=None, category=None, only_unread=not show_read, limit=limit
        )
        st.header("Latest Entries")

    st.session_state.logger.debug(f"Displaying {len(entries) if entries else 0} entries")

    if not entries:
        st.info("No entries to display.")
        return

    for entry in entries:
        with st.expander(f"{entry.title}", expanded=True):
            st.markdown(
                f"*{entry.feed.category} / {entry.feed.title}* - {entry.published_date.strftime('%Y-%m-%d %H:%M')}"
            )

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

            # Security Analysis
            security_col1, security_col2 = st.columns([6, 1])
            with security_col1:
                if entry.security_analysis:
                    st.markdown("#### 🛡️ Security Analysis")
                    try:
                        iocs = eval(entry.security_analysis.iocs)
                        if iocs:
                            st.markdown("**IOCs Found:**")
                            ioc_data = [
                                {
                                    "Type": ioc["type"],
                                    "Value": ioc["value"],
                                    "Confidence": f"{ioc.get('confidence', 100)}%",
                                }
                                for ioc in iocs
                            ]
                            df = pd.DataFrame(ioc_data)
                            st.table(df)

                            st.markdown("**IOC Context:**")
                            for ioc in iocs:
                                with st.expander(
                                    f"{ioc['type']}: {ioc['value']}", expanded=False
                                ):
                                    if ioc.get("context"):
                                        st.write(ioc["context"])
                    except Exception as e:
                        st.error(f"Error displaying IOCs: {str(e)}")

                    if (
                        entry.security_analysis.sigma_rule
                        and entry.security_analysis.sigma_rule
                        != "No applicable Sigma rule for this content."
                    ):
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

            # Content Analysis
            content_col1, content_col2 = st.columns([6, 1])
            with content_col1:
                if entry.detailed_analysis:
                    st.markdown("#### 🔍 Content Analysis")
                    st.markdown(entry.detailed_analysis.key_points)

            with content_col2:
                button_key = f"analyze_{entry.id}"
                if entry.detailed_analysis:
                    if st.button("🔄 Refresh", key=f"refresh_{button_key}"):
                        with st.spinner("Refreshing content analysis..."):
                            feed_service.analyze_detailed_content(entry.id)
                        st.rerun()
                else:
                    if st.button("🔍 Analyze", key=button_key):
                        with st.spinner("Analyzing content..."):
                            feed_service.analyze_detailed_content(entry.id)
                        st.rerun()

            # Mark as read
            if not entry.is_read:
                if st.button("📖 Mark as Read", key=f"read_{entry.id}"):
                    feed_service.mark_as_read(entry.id)
                    st.rerun()

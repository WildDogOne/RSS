import os
import json
import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from app.models import Base, Feed, FeedEntry, SecurityAnalysis
from app.feed_service import FeedService
from app.llm_service import LLMService

# Database setup
database_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'rss.db')
os.makedirs(os.path.dirname(database_path), exist_ok=True)
engine = create_engine(f'sqlite:///{database_path}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Load or create config file
CONFIG_FILE = os.path.join(os.path.dirname(database_path), 'config.json')
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"ollama_url": "http://localhost:11434", "ollama_model": "mistral"}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Initialize configuration
config = load_config()
if 'ollama_url' not in st.session_state:
    st.session_state.ollama_url = config["ollama_url"]
if 'ollama_model' not in st.session_state:
    st.session_state.ollama_model = config["ollama_model"]

# Services setup
llm_service = LLMService(st.session_state.ollama_url, st.session_state.ollama_model)
feed_service = FeedService(Session(), llm_service)

# Schedule feed updates
scheduler = BackgroundScheduler()
scheduler.add_job(feed_service.update_feeds, 'interval', minutes=30)
scheduler.start()

def main():
    st.title("RSS Feed Reader with LLM Analysis")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        st.session_state.ollama_url = st.text_input("Ollama URL", st.session_state.ollama_url)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            # Get available models from Ollama
            available_models = llm_service.get_available_models()
            selected_model = st.selectbox("Ollama Model", options=available_models, 
                                        index=available_models.index(st.session_state.ollama_model) if st.session_state.ollama_model in available_models else 0)
        with col2:
            if st.button("🔄", help="Refresh model list"):
                st.rerun()
        
        if selected_model != st.session_state.ollama_model:
            st.session_state.ollama_model = selected_model
            llm_service.update_config(st.session_state.ollama_url, selected_model)
            save_config({"ollama_url": st.session_state.ollama_url, "ollama_model": selected_model})
        
        st.header("Add New Feed")
        st.write("Add individual feed:")
        new_feed_url = st.text_input("Feed URL")
        new_feed_title = st.text_input("Feed Title (optional)")
        new_feed_category = st.text_input("Category (optional)")
        is_security_feed = st.checkbox("Security Feed")
        
        if st.button("Add Feed"):
            if new_feed_url:
                feed_service.add_feed(
                    url=new_feed_url,
                    is_security_feed=is_security_feed,
                    title=new_feed_title if new_feed_title else None,
                    category=new_feed_category if new_feed_category else None
                )
                st.success("Feed added successfully!")
            else:
                st.error("Please enter a feed URL")
        
        st.write("Or import feeds from OPML:")
        uploaded_file = st.file_uploader("Choose an OPML file", type="opml")
        if uploaded_file is not None:
            try:
                tree = ET.parse(uploaded_file)
                root = tree.getroot()
                imported_count = 0

                # Process categories (top-level outlines)
                for category_outline in root.findall("./body/outline"):
                    category = category_outline.get('text') or category_outline.get('title')
                    
                    # Process feeds within this category
                    for feed_outline in category_outline.findall("outline"):
                        feed_url = feed_outline.get('xmlUrl')
                        if feed_url:
                            title = feed_outline.get('text') or feed_outline.get('title')
                            
                            # Check if feed is security related based on categories/text
                            is_security = any(security_term in ((category or '') + (title or '')).lower() 
                                            for security_term in ['security', 'vulnerability', 'threat', 'cve'])
                            
                            feed_service.add_feed(
                                url=feed_url,
                                is_security_feed=is_security,
                                title=title,
                                category=category
                            )
                            imported_count += 1
                st.success(f"Successfully imported {imported_count} feeds from OPML file!")
            except ET.ParseError:
                st.error("Invalid OPML file")
            except Exception as e:
                st.error(f"Error importing OPML: {str(e)}")
    
    # Main content area
    overview_tab, feeds_tab = st.tabs(["Overview", "Feed Entries"])
    
    with overview_tab:
        db = Session()

        # Manage Feeds section
        st.header("Manage Feeds")
        feeds = db.query(Feed).order_by(Feed.category, Feed.title).all()

        # Group feeds by category
        feeds_by_category = {}
        for feed in feeds:
            category = feed.category or "Uncategorized"
            if category not in feeds_by_category:
                feeds_by_category[category] = []
            feeds_by_category[category].append(feed)
        
        for category, category_feeds in feeds_by_category.items():
            with st.expander(f"📁 {category} ({len(category_feeds)} feeds)", expanded=True):
                for feed in category_feeds:
                    # Initialize session state for edit mode
                    edit_key = f"edit_mode_{feed.id}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        if st.session_state[edit_key]:
                            new_title = st.text_input("Title", feed.title or feed.url, key=f"title_{feed.id}")
                            new_category = st.text_input("Category", feed.category or "", key=f"category_{feed.id}")
                            if st.button("Save", key=f"save_{feed.id}"):
                                feed_service.update_feed(feed.id, new_category, new_title)
                                st.session_state[edit_key] = False
                                st.rerun()
                        else:
                            st.write(f"**{feed.title or feed.url}**")
                    
                    with col2:
                        if st.button("✏️", key=f"edit_{feed.id}", help="Edit feed"):
                            st.session_state[edit_key] = True
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️", key=f"delete_{feed.id}", help="Delete feed"):
                            feed_service.remove_feed(feed.id)
                            st.rerun()

        st.markdown("---")

        # Get all entries ordered by published date
        entries = db.query(FeedEntry).join(Feed).order_by(FeedEntry.published_date.desc()).all()
        
        if not entries:
            st.info("No entries yet. Add some feeds or wait for the next update.")
        else:
            for entry in entries:
                with st.container():
                    st.markdown("""
                    <style>
                    .feed-card {
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 1rem;
                        margin-bottom: 1rem;
                        background-color: white;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"#### {entry.title}")
                        category = entry.feed.category or "Uncategorized"
                        st.markdown(f"*{category} / {entry.feed.title}* - {entry.published_date.strftime('%Y-%m-%d %H:%M')}")
                        st.markdown("---")
                        
                        # Show either existing LLM summary or original summary
                        if entry.llm_summary:
                            st.write(entry.llm_summary)
                        else:
                            st.write(entry.summary or entry.content[:300] + "...")
                        
                        st.markdown(f"[Read More]({entry.link})")
                    
                    with col2:
                        # Action buttons
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if not entry.is_read:
                                if st.button("📖 Read", key=f"read_{entry.id}"):
                                    feed_service.mark_as_read(entry.id)
                                    st.rerun()
                                    
                            if not entry.llm_summary:
                                if st.button("🤖 LLM", key=f"llm_{entry.id}"):
                                    with st.spinner("Generating summary..."):
                                        feed_service.generate_llm_summary(entry.id)
                                    st.rerun()
                        
                        with btn_col2:
                            if not entry.security_analysis:
                                if st.button("🛡️ Sec", key=f"sec_{entry.id}"):
                                    with st.spinner("Analyzing..."):
                                        feed_service.analyze_security(entry.id)
                                    st.rerun()
    
    with feeds_tab:
        db = Session()
        feeds = db.query(Feed).all()
        
        if not feeds:
            st.info("No feeds added yet. Add your first feed using the sidebar!")
        else:
            selected_feed = st.selectbox(
                "Select Feed",
                options=feeds,
                format_func=lambda x: x.title or x.url
            )
            
            if selected_feed:
                entries = feed_service.get_unread_entries(selected_feed.id)
                st.write(f"### Latest Unread Entries ({len(entries)})")
                for entry in entries:
                    with st.expander(entry.title):
                        st.write(f"Published: {entry.published_date}")
                        st.write(f"Link: {entry.link}")
                        st.markdown("### Summary")
                        if entry.llm_summary:
                            st.write(entry.llm_summary)
                        else:
                            if st.button("🤖 Generate LLM Summary", key=f"llm_{entry.id}"):
                                with st.spinner("Generating summary..."):
                                    feed_service.generate_llm_summary(entry.id)
                                st.rerun()
                            st.write(entry.summary)

                        # Always show security analysis
                        st.markdown("### Security Analysis")
                        if entry.security_analysis:
                            iocs = eval(entry.security_analysis.iocs)
                            if iocs:
                                st.markdown("#### IOCs Found:")
                                df = pd.DataFrame(iocs)
                                st.dataframe(df)
                            
                            if entry.security_analysis.sigma_rule and entry.security_analysis.sigma_rule != "No applicable Sigma rule for this content.":
                                st.markdown("#### Sigma Rule:")
                                st.code(entry.security_analysis.sigma_rule)
                        else:
                            if st.button("🛡️ Analyze Security", key=f"sec_{entry.id}"):
                                with st.spinner("Analyzing security aspects..."):
                                    feed_service.analyze_security(entry.id)
                                st.rerun()
                        
                        st.markdown("### Original Content")
                        st.write(entry.content)

                        if not entry.is_read:
                            if st.button("📖 Mark as Read", key=f"read_{entry.id}"):
                                feed_service.mark_as_read(entry.id)
                                st.rerun()
    

if __name__ == "__main__":
    main()

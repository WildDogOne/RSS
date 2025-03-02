import os
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

import json
import os

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
        is_security_feed = st.checkbox("Security Feed")
        if st.button("Add Feed"):
            if new_feed_url:
                feed_service.add_feed(new_feed_url, is_security_feed)
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
                for outline in root.findall(".//outline"):
                    feed_url = outline.get('xmlUrl')
                    if feed_url:
                        # Check if feed is security related based on categories/tags
                        is_security = any(security_term in (outline.get('category', '') + outline.get('text', '')).lower() 
                                        for security_term in ['security', 'vulnerability', 'threat', 'cve'])
                        feed_service.add_feed(feed_url, is_security)
                        imported_count += 1
                st.success(f"Successfully imported {imported_count} feeds from OPML file!")
            except ET.ParseError:
                st.error("Invalid OPML file")
            except Exception as e:
                st.error(f"Error importing OPML: {str(e)}")
    
    # Main content area
    tab1, tab2 = st.tabs(["Feed Entries", "Security Analysis"])
    
    with tab1:
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
                entries = db.query(FeedEntry).filter(FeedEntry.feed_id == selected_feed.id).all()
                for entry in entries:
                    with st.expander(entry.title):
                        st.write(f"Published: {entry.published_date}")
                        st.write(f"Link: {entry.link}")
                        st.markdown("### Summary")
                        st.write(entry.summary)
                        st.markdown("### Original Content")
                        st.write(entry.content)
    
    with tab2:
        security_feeds = db.query(Feed).filter(Feed.is_security_feed == True).all()
        if not security_feeds:
            st.info("No security feeds added yet!")
        else:
            selected_security_feed = st.selectbox(
                "Select Security Feed",
                options=security_feeds,
                format_func=lambda x: x.title or x.url,
                key="security_feed"
            )
            
            if selected_security_feed:
                entries = db.query(FeedEntry).join(SecurityAnalysis).filter(
                    FeedEntry.feed_id == selected_security_feed.id
                ).all()
                
                for entry in entries:
                    with st.expander(entry.title):
                        analysis = db.query(SecurityAnalysis).filter(
                            SecurityAnalysis.entry_id == entry.id
                        ).first()
                        
                        if analysis:
                            st.markdown("### IOCs")
                            iocs = eval(analysis.iocs)
                            if iocs:
                                df = pd.DataFrame(iocs)
                                st.dataframe(df)
                            else:
                                st.info("No IOCs found")
                            
                            st.markdown("### Sigma Rule")
                            st.code(analysis.sigma_rule)
                        else:
                            st.info("Analysis pending...")

if __name__ == "__main__":
    main()

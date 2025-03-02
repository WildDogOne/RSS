import os
from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from .models import Base, Feed, FeedEntry, SecurityAnalysis
from .feed_service import FeedService
from .llm_service import LLMService

app = Flask(__name__)

# Database setup
database_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'rss.db')
os.makedirs(os.path.dirname(database_path), exist_ok=True)
engine = create_engine(f'sqlite:///{database_path}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Services setup
llm_service = LLMService()
feed_service = FeedService(Session(), llm_service)

# Schedule feed updates every 30 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(feed_service.update_feeds, 'interval', minutes=30)
scheduler.start()

@app.route('/')
def index():
    db = Session()
    feeds = db.query(Feed).all()
    return render_template('index.html', feeds=feeds)

@app.route('/api/feeds', methods=['GET', 'POST'])
def handle_feeds():
    if request.method == 'POST':
        data = request.json
        url = data.get('url')
        is_security_feed = data.get('is_security_feed', False)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        feed = feed_service.add_feed(url, is_security_feed)
        return jsonify({
            'id': feed.id,
            'url': feed.url,
            'is_security_feed': feed.is_security_feed
        })
    
    # GET request
    db = Session()
    feeds = db.query(Feed).all()
    return jsonify([{
        'id': feed.id,
        'url': feed.url,
        'title': feed.title,
        'is_security_feed': feed.is_security_feed,
        'last_fetched': feed.last_fetched.isoformat() if feed.last_fetched else None
    } for feed in feeds])

@app.route('/api/feeds/<int:feed_id>/entries')
def get_feed_entries(feed_id):
    db = Session()
    entries = db.query(FeedEntry).filter(FeedEntry.feed_id == feed_id).all()
    return jsonify([{
        'id': entry.id,
        'title': entry.title,
        'link': entry.link,
        'published_date': entry.published_date.isoformat() if entry.published_date else None,
        'summary': entry.summary
    } for entry in entries])

@app.route('/api/entries/<int:entry_id>/security')
def get_security_analysis(entry_id):
    db = Session()
    analysis = db.query(SecurityAnalysis).filter(SecurityAnalysis.entry_id == entry_id).first()
    if not analysis:
        return jsonify({'error': 'No security analysis found'}), 404
    
    return jsonify({
        'iocs': eval(analysis.iocs),  # Convert string representation back to list
        'sigma_rule': analysis.sigma_rule,
        'analysis_date': analysis.analysis_date.isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

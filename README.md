# RSS Feed Reader with LLM Analysis

A web application that combines RSS feed reading with local LLM-powered analysis using Ollama. It automatically summarizes feed entries and performs security analysis on security-related feeds.

## Features

- RSS feed aggregation and management
- Automatic feed updates every 30 minutes
- LLM-powered article summarization using Ollama
- Security feed analysis:
  - Automatic IOC extraction
  - Sigma rule generation
- Web interface for feed management and content viewing
- Docker-based deployment

## Prerequisites

- Docker and Docker Compose
- Ollama installed and running locally (automatically installed in container)

## Setup and Running

1. Clone the repository:
```bash
git clone https://github.com/yourusername/RSS.git
cd RSS
```

2. Build and start the containers:
```bash
docker-compose up --build
```

3. Access the web interface:
   - Open http://localhost:5000 in your browser
   - Add RSS feeds through the web interface
   - Mark security-related feeds for additional analysis

## API Endpoints

- `GET /api/feeds` - List all feeds
- `POST /api/feeds` - Add a new feed
- `GET /api/feeds/{feed_id}/entries` - Get entries for a specific feed
- `GET /api/entries/{entry_id}/security` - Get security analysis for an entry

## Usage

1. Add feeds through the web interface:
   - Enter the RSS feed URL
   - Check "This is a security-related feed" for security feeds
   - Submit to add the feed

2. View feed entries:
   - Click "View Entries" on any feed to see its content
   - Each entry includes:
     - Original title and link
     - LLM-generated summary
     - Security analysis (for security feeds)

3. Security Analysis:
   - Security feeds receive additional analysis:
     - Automatic IOC extraction
     - Sigma rule generation for threat detection
   - Access security analysis through the API endpoint

## Docker Volume Persistence

The application uses two Docker volumes:
- `./data:/app/data` - Stores the SQLite database
- `ollama:/root/.ollama` - Persists Ollama models and data

## Development

To run in development mode:
```bash
# Start with hot reloading
docker-compose up
```

## Note on LLM Usage

The application uses Ollama with the Mistral model for:
- Article summarization
- IOC extraction
- Sigma rule generation

Make sure your system has adequate resources to run the LLM efficiently.

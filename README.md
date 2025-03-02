# RSS Feed Reader with LLM Analysis

A Streamlit web application that combines RSS feed reading with local LLM-powered analysis using Ollama. It automatically summarizes feed entries and performs security analysis on security-related feeds.

## Features

- RSS feed aggregation and management
- Automatic feed updates every 30 minutes
- LLM-powered article summarization using Ollama
- Security feed analysis:
  - Automatic IOC extraction
  - Sigma rule generation
- Streamlit-based user interface
- Configurable Ollama settings (URL and model)
- Docker-based deployment

## Prerequisites

- Docker and Docker Compose
- Ollama installed and running with your preferred model (not included in container)

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
   - Open http://localhost:8501 in your browser
   - Configure Ollama settings in the sidebar (defaults to http://ollama:11434 and mistral model)
   - Add RSS feeds through the sidebar interface
   - Mark security-related feeds for additional analysis

## Usage

1. Configure Ollama:
   - In the sidebar, set your Ollama URL (default: http://ollama:11434)
   - Select your preferred model (default: mistral)
   - Make sure the model is available in your Ollama installation

2. Add feeds through the sidebar:
   - Enter the RSS feed URL
   - Check "Security Feed" for security-related feeds
   - Click "Add Feed" to submit

3. View feed entries:
   - Select a feed from the dropdown in the "Feed Entries" tab
   - Each entry shows:
     - Title and publication date
     - Original link
     - LLM-generated summary
     - Original content

4. Security Analysis:
   - Switch to the "Security Analysis" tab
   - Select a security feed from the dropdown
   - View for each entry:
     - Extracted IOCs in table format
     - Generated Sigma rules

## Docker Volume Persistence

The application uses two Docker volumes:
- `./data:/app/data` - Stores the SQLite database
- `ollama_data:/root/.ollama` - Persists Ollama models and data

## Development

To run in development mode:
```bash
# Start with hot reloading
docker-compose up
```

## Note on LLM Usage

The application uses Ollama for:
- Article summarization
- IOC extraction (for security feeds)
- Sigma rule generation (for security feeds)

Make sure:
- Your Ollama installation is properly configured
- The selected model is installed in Ollama
- Your system has adequate resources to run the LLM efficiently

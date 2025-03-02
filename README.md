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
- Configurable Ollama connection
- Docker-based deployment

## Prerequisites

- Docker and Docker Compose
- Ollama installed and running on your system or network with your preferred model

## Setup and Running

1. Clone the repository:
```bash
git clone https://github.com/yourusername/RSS.git
cd RSS
```

2. Build and start the container:
```bash
docker-compose up --build
```

3. Configure Ollama connection:
   - Open http://localhost:8501 in your browser
   - In the sidebar, set your Ollama URL:
     - Use `http://localhost:11434` if Ollama is running on the same machine
     - Use `http://<ollama-host>:11434` if Ollama is running on a different machine
   - Set your preferred model name (must be already installed in your Ollama instance)

4. Start using the application:
   - Add RSS feeds through the sidebar interface
   - Mark security-related feeds for additional analysis

## Usage

1. Configure Ollama Connection:
   - Set Ollama URL in the sidebar:
     - Local Ollama: `http://localhost:11434`
     - Remote Ollama: `http://<ollama-host>:11434`
   - Enter the name of an installed model
   - The connection status will be shown when adding feeds or viewing content

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

The application uses a Docker volume:
- `./data:/app/data` - Stores the SQLite database

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
- Your Ollama installation is properly configured and accessible
- The selected model is installed in your Ollama instance
- Your system has adequate resources to run the LLM efficiently

## Troubleshooting

If you cannot connect to Ollama:
1. Verify Ollama is running (`ollama ps`)
2. Check the Ollama URL in the sidebar configuration
3. Ensure network connectivity between the container and Ollama host
4. Verify the model specified is installed (`ollama list`)

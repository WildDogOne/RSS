# RSS Feed Reader with LLM Analysis

A modern web application that combines RSS feed reading with advanced LLM-powered analysis using Ollama. It automatically processes and analyzes feed entries, providing summaries, detailed content analysis, and specialized security analysis features.

## Core Features

### Feed Management
- RSS/Atom feed aggregation and management
- Category-based feed organization
- OPML import support for bulk feed addition
- Automatic feed updates every 30 minutes
- Read/unread entry tracking
- Feed categorization and organization

### LLM-Powered Analysis
- Automatic article summarization
- Detailed content analysis including:
  - Key points and findings
  - Technical details extraction
  - Impact assessment
  - Related technologies/concepts
  - Recommendations and conclusions
- Security feed analysis:
  - Automated IOC (Indicators of Compromise) extraction
  - Sigma rule generation for threat detection
  - Structured security insights

### User Interface
- Clean, modern Streamlit-based interface
- Category-based feed organization
- Configurable view settings:
  - Show/hide read entries
  - Adjustable entries per feed
  - Last update timestamp display
- Expandable entry cards with:
  - Original content link
  - Publication date
  - Category information
  - LLM-generated summaries
  - Security analysis (for security feeds)

### Advanced Features
- Debug console with real-time logging
- Configurable logging levels
- Test feed functionality for debugging
- Detailed entry analysis on demand
- Filter and search capabilities
- Customizable LLM model selection

## Technical Setup

### Prerequisites
- Docker and Docker Compose
- Ollama installed and running with your preferred model

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/RSS.git
cd RSS
```

2. Build and start the containers:
```bash
docker-compose up --build
```

3. Configure Ollama connection:
   - Access http://localhost:8501
   - In Settings (⚙️):
     - Set Ollama URL (`http://localhost:11434` for local, or `http://<ollama-host>:11434` for remote)
     - Select your preferred model from available models
     - Configure logging and debug settings if needed

### Data Persistence
The application uses Docker volumes for data persistence:
- `./data:/app/data` - Stores the SQLite database and configuration

## Usage Guide

### Main Interface Components

1. **Header Controls**
   - ⚙️ Settings - Configure application settings
   - 🔄 Update All - Manual feed refresh
   - 🖥️ Console - Toggle debug console

2. **Feed Management**
   - Add new feeds with optional titles and categories
   - Import feeds from OPML files
   - Organize feeds into categories
   - Mark entries as read/unread

3. **Entry Analysis**
   - 🤖 Generate Summary - Create LLM summary
   - 🔍 Analyze Content - Perform detailed content analysis
   - 🛡️ Security Analysis - For security-related feeds

4. **View Controls**
   - Show/hide read entries
   - Select number of entries per feed
   - Filter by category or individual feed

### Advanced Configuration

1. **Debug Settings**
   - Enable/disable debug mode
   - Set logging level (DEBUG, INFO, WARNING, ERROR)
   - Access real-time logs in debug console

2. **LLM Configuration**
   - Configure Ollama connection URL
   - Select from available models
   - Test connection and refresh model list

## Security Feed Features

Security-focused feeds receive additional analysis:

1. **IOC Extraction**
   - Identifies and categorizes potential indicators
   - Supports multiple IOC types (IPs, domains, hashes, URLs)
   - Presents findings in structured format

2. **Sigma Rule Generation**
   - Creates detection rules based on article content
   - Includes title, description, status, and level
   - Provides YAML-formatted rules for security tools

## Troubleshooting

1. **Ollama Connection Issues**
   - Verify Ollama is running (`ollama ps`)
   - Check URL configuration in settings
   - Ensure network connectivity
   - Verify model availability (`ollama list`)

2. **Feed Issues**
   - Check feed URL validity
   - Verify feed format (RSS/Atom)
   - Review debug console for detailed errors
   - Check feed update timestamp

3. **Performance Optimization**
   - Adjust entries per feed limit
   - Use categories for better organization
   - Mark read entries to reduce clutter
   - Configure appropriate logging level

## Development

For development mode:
```bash
# Start with hot reloading
docker-compose up
```

Debug features:
- Real-time logging in debug console
- Test feed functionality
- Configurable log levels
- SQL query logging in debug mode

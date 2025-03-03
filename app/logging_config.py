import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

class StreamToList:
    """Custom stream handler that stores logs in memory."""
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def write(self, text: str) -> int:
        log_entry = {"timestamp": datetime.now(), "message": text.strip()}
        if log_entry["message"]:  # Only add non-empty messages
            self.logs.append(log_entry)
        return len(text)

    def flush(self) -> None:
        pass

    def get_logs(self, limit: Optional[int] = None) -> List[Dict]:
        logs = sorted(self.logs, key=lambda x: x["timestamp"], reverse=True)
        return logs[:limit] if limit else logs

    def clear(self) -> None:
        self.logs = []

class LoggingManager:
    def __init__(self):
        self.memory_stream = StreamToList()
        self.memory_handler = logging.StreamHandler(self.memory_stream)
        self.memory_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        # Setup root logger
        self.root_logger = logging.getLogger()
        self.root_logger.handlers = []  # Remove default handlers
        
        # Add console handler
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.root_logger.addHandler(self.console_handler)
        self.root_logger.addHandler(self.memory_handler)

    def update_settings(self, debug_enabled: bool, log_level: str) -> None:
        """Update logging configuration."""
        # Update root logger level
        self.root_logger.setLevel(getattr(logging, log_level))

        # Configure SQLAlchemy logging based on debug mode
        if debug_enabled:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)
        else:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    def get_memory_stream(self) -> StreamToList:
        """Get the memory stream for accessing stored logs."""
        return self.memory_stream

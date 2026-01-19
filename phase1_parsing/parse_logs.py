"""
Phase 1: Log Parser
Converts raw execution logs into structured LogEntry objects.
Automatically detects temporal strategy (timestamp vs sequence).
"""

import json
import csv
from pathlib import Path
from typing import Any
from .schemas import LogEntry, ParsedLogs, TemporalStrategy


class LogParser:
    """
    Parses execution logs from various formats.
    
    Supports JSON and CSV formats.
    Automatically detects whether to use timestamps or sequence ordering.
    Domain-independent: extracts structure without interpreting semantics.
    """
    
    # Flexible field name mappings
    FIELD_MAPPINGS = {
        'entry_id': ['entry_id', 'id', 'event_id', 'log_id', 'eventId'],
        'agent_id': ['agent_id', 'agent', 'agentId', 'actor', 'agent_name'],
        'action': ['action', 'event', 'activity', 'what', 'behavior'],
        'timestamp': ['timestamp', 'time', 'datetime', 'when', 'created_at'],
        'sequence_number': ['sequence_number', 'sequence', 'order', 'index', 'seq'],
    }
    
    def __init__(self, log_file_path: str | Path):
        """Initialize parser with path to log file."""
        self.log_file_path = Path(log_file_path)
        
        if not self.log_file_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file_path}")
    
    def _normalize_field_name(self, raw_data: dict, field_name: str) -> Any:
        """Extract field value using flexible field name matching."""
        possible_names = self.FIELD_MAPPINGS.get(field_name, [field_name])
        
        for name in possible_names:
            if name in raw_data:
                return raw_data[name]
        
        return None
    
    def _detect_temporal_strategy(self, raw_logs: list[dict]) -> TemporalStrategy:
        """
        Automatically detect whether to use timestamps or sequence numbers.
        
        Strategy:
        1. If all entries have valid timestamps -> use TIMESTAMP
        2. Otherwise -> use SEQUENCE
        
        Args:
            raw_logs: List of raw log dictionaries
            
        Returns:
            Detected temporal strategy
        """
        if not raw_logs:
            return TemporalStrategy.SEQUENCE
        
        # Check if all entries have timestamps
        timestamp_count = 0
        for log in raw_logs:
            ts = self._normalize_field_name(log, 'timestamp')
            if ts is not None and ts != '':
                timestamp_count += 1
        
        # If majority have timestamps, use timestamp strategy
        if timestamp_count >= len(raw_logs) * 0.8:  # 80% threshold
            return TemporalStrategy.TIMESTAMP
        else:
            return TemporalStrategy.SEQUENCE
    
    def _parse_single_log(self, raw_log: dict, index: int, temporal_strategy: TemporalStrategy) -> LogEntry:
        """
        Parse a single log entry from raw dictionary.
        
        Args:
            raw_log: Raw log data
            index: Position in file (for auto-generating IDs and sequence numbers)
            temporal_strategy: Which temporal approach to use
            
        Returns:
            Validated LogEntry object
        """
        # Extract fields using flexible matching
        entry_id = self._normalize_field_name(raw_log, 'entry_id') or f"entry_{index}"
        agent_id = self._normalize_field_name(raw_log, 'agent_id')
        action = self._normalize_field_name(raw_log, 'action')
        timestamp = self._normalize_field_name(raw_log, 'timestamp')
        sequence_number = self._normalize_field_name(raw_log, 'sequence_number')
        
        # Auto-assign sequence number if using SEQUENCE strategy and not provided
        if temporal_strategy == TemporalStrategy.SEQUENCE and sequence_number is None:
            sequence_number = index
        
        # Collect extra fields as metadata
        metadata = {
            k: v for k, v in raw_log.items()
            if k not in ['entry_id', 'id', 'event_id', 'agent_id', 'agent', 
                        'action', 'event', 'timestamp', 'time', 'sequence_number']
        }
        
        return LogEntry(
            entry_id=entry_id,
            agent_id=agent_id,
            action=action,
            timestamp=timestamp,
            sequence_number=sequence_number,
            metadata=metadata
        )
    
    def _parse_json(self) -> tuple[list[dict], TemporalStrategy]:
        """Parse JSON format log file."""
        with open(self.log_file_path, 'r') as f:
            raw_data = json.load(f)
        
        # Handle both single-dict and list formats
        if isinstance(raw_data, dict):
            # Check if it's a wrapper with a 'logs' or 'entries' key
            if 'logs' in raw_data:
                raw_logs = raw_data['logs']
            elif 'entries' in raw_data:
                raw_logs = raw_data['entries']
            else:
                # Treat entire dict as single log entry
                raw_logs = [raw_data]
        elif isinstance(raw_data, list):
            raw_logs = raw_data
        else:
            raise ValueError("Log file must contain a dict or list")
        
        temporal_strategy = self._detect_temporal_strategy(raw_logs)
        return raw_logs, temporal_strategy
    
    def _parse_csv(self) -> tuple[list[dict], TemporalStrategy]:
        """Parse CSV format log file."""
        raw_logs = []
        
        with open(self.log_file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_logs.append(dict(row))
        
        temporal_strategy = self._detect_temporal_strategy(raw_logs)
        return raw_logs, temporal_strategy
    
    def parse(self) -> ParsedLogs:
        """
        Parse the log file and return structured logs.
        
        Returns:
            ParsedLogs object containing all log entries
        """
        # Determine file format
        suffix = self.log_file_path.suffix.lower()
        
        if suffix == '.json':
            raw_logs, temporal_strategy = self._parse_json()
        elif suffix == '.csv':
            raw_logs, temporal_strategy = self._parse_csv()
        else:
            raise ValueError(f"Unsupported log file format: {suffix}")
        
        # Parse each log entry
        entries = []
        for idx, raw_log in enumerate(raw_logs):
            try:
                entry = self._parse_single_log(raw_log, idx, temporal_strategy)
                entries.append(entry)
            except Exception as e:
                print(f"Warning: Failed to parse log entry at index {idx}: {e}")
                continue
        
        return ParsedLogs(
            entries=entries,
            temporal_strategy=temporal_strategy
        )


def parse_logs(log_file_path: str | Path) -> ParsedLogs:
    """
    Convenience function to parse logs with auto-format detection.
    
    Args:
        log_file_path: Path to log file
        
    Returns:
        ParsedLogs object
    """
    from pathlib import Path
    
    path = Path(log_file_path)
    suffix = path.suffix.lower()
    
    # Auto-detect format
    if suffix in ['.log', '.txt']:
        from .parse_logs_text import parse_logs_text
        return parse_logs_text(log_file_path)
    elif suffix in ['.json', '.csv']:
        parser = LogParser(log_file_path)
        return parser.parse()
    else:
        raise ValueError(f"Unsupported log file format: {suffix}. Supported: .log, .txt, .json, .csv")
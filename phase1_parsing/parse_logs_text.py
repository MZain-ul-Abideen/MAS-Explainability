"""
Phase 1: Text Log Parser
Converts text-based execution logs into structured LogEntry objects.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from .schemas import LogEntry, ParsedLogs, TemporalStrategy


class TextLogParser:
    """
    Parses execution logs from text format.
    
    Automatically detects log patterns and extracts:
    - Agent IDs
    - Actions
    - Timestamps (if present)
    - Additional metadata
    
    Domain-independent: uses pattern matching without hard-coded values.
    """
    
    # Common log patterns
    PATTERNS = [
        # Pattern 1: [agent] [context] action (JaCaMo/Moise style)
        r'^\[(?P<agent_id>[^\]]+)\]\s+\[(?P<context>[^\]]+)\]\s+(?P<action>.+)$',
        
        # Pattern 2: [agent] action description
        r'^\[(?P<agent_id>[^\]]+)\]\s+(?P<action>.+)$',
        
        # Pattern 3: timestamp | agent | action | metadata
        r'^(?P<timestamp>[^|]+)\s*\|\s*(?P<agent_id>[^|]+)\s*\|\s*(?P<action>[^|]+)(?:\s*\|\s*(?P<metadata>.*))?$',
        
        # Pattern 4: [timestamp] agent: action (metadata)
        r'^\[(?P<timestamp>[^\]]+)\]\s*(?P<agent_id>\S+):\s*(?P<action>\S+)(?:\s+(?P<metadata>.*))?$',
        
        # Pattern 5: timestamp agent action metadata
        r'^(?P<timestamp>\S+\s+\S+)\s+(?P<agent_id>\S+)\s+(?P<action>.+)$',
        
        # Pattern 6: agent action description
        r'^(?P<agent_id>\S+)\s+(?P<action>.+)$',
    ]
    
    def __init__(self, log_file_path: str | Path):
        """Initialize parser with path to text log file."""
        self.log_file_path = Path(log_file_path)
        
        if not self.log_file_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file_path}")
        
        self.detected_pattern = None
    
    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Try to parse timestamp from string."""
        if not ts_str:
            return None
        
        ts_str = ts_str.strip()
        
        # Common timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%Y%m%d %H:%M:%S",
            "%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _extract_metadata_from_action(self, action: str) -> tuple[str, dict]:
        """
        Extract metadata embedded in action string.
        
        For example:
        - "Registered wa_wheels1 for operation: assemble_wheels (energy=7, time=3)"
        - "artifact ws_trunks2: tools.WorkstationArt(...)"
        
        Returns:
            (cleaned_action, metadata_dict)
        """
        metadata = {}
        
        # Extract key=value pairs in parentheses
        paren_pattern = r'\(([^)]+)\)'
        paren_matches = re.findall(paren_pattern, action)
        
        for match in paren_matches:
            # Try to extract key=value pairs
            kv_pattern = r'(\w+)=([^\s,)]+)'
            kv_matches = re.findall(kv_pattern, match)
            if kv_matches:
                metadata.update(dict(kv_matches))
        
        # Extract operation names (for workstation operations)
        op_pattern = r'for operation:\s*(\w+)'
        op_match = re.search(op_pattern, action)
        if op_match:
            metadata['operation'] = op_match.group(1)
        
        # Extract "for op=X" pattern
        op_pattern2 = r'for op=(\w+)'
        op_match2 = re.search(op_pattern2, action)
        if op_match2:
            metadata['operation'] = op_match2.group(1)
        
        return action, metadata
    
    def _normalize_agent_id(self, agent_id: str) -> str:
        """Clean up agent ID (remove extra brackets, whitespace)."""
        if not agent_id:
            return "unknown"
        
        # Remove surrounding brackets if present
        agent_id = agent_id.strip()
        if agent_id.startswith('[') and agent_id.endswith(']'):
            agent_id = agent_id[1:-1]
        
        return agent_id.strip()
    
    def _clean_action(self, action: str) -> str:
        """Clean and normalize action string."""
        if not action:
            return "unknown"
        
        action = action.strip()
        
        # Remove trailing periods
        if action.endswith('.'):
            action = action[:-1]
        
        return action
    
    def _match_line(self, line: str) -> Optional[dict]:
        """Try to match line against known patterns."""
        line = line.strip()
        
        if not line or line.startswith('#'):
            return None
        
        # Try each pattern
        for pattern in self.PATTERNS:
            match = re.match(pattern, line)
            if match:
                result = match.groupdict()
                
                # Clean up agent_id
                if 'agent_id' in result:
                    result['agent_id'] = self._normalize_agent_id(result['agent_id'])
                
                # Clean up action
                if 'action' in result:
                    result['action'] = self._clean_action(result['action'])
                
                return result
        
        return None
    
    def _detect_temporal_strategy(self, entries: list[dict]) -> TemporalStrategy:
        """Determine if logs have timestamps or should use sequence."""
        timestamp_count = sum(1 for e in entries if e.get('timestamp'))
        
        if timestamp_count >= len(entries) * 0.8:
            return TemporalStrategy.TIMESTAMP
        else:
            return TemporalStrategy.SEQUENCE
    
    def parse(self) -> ParsedLogs:
        """
        Parse the text log file and return structured logs.
        
        Returns:
            ParsedLogs object containing all log entries
        """
        raw_entries = []
        
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                matched = self._match_line(line)
                if matched:
                    raw_entries.append({
                        'line_num': line_num,
                        **matched
                    })
        
        if not raw_entries:
            raise ValueError("No log entries could be parsed from file")
        
        # Detect temporal strategy
        temporal_strategy = self._detect_temporal_strategy(raw_entries)
        
        # Convert to LogEntry objects
        entries = []
        for idx, raw_entry in enumerate(raw_entries):
            try:
                # Parse timestamp if present
                timestamp = None
                if raw_entry.get('timestamp'):
                    timestamp = self._parse_timestamp(raw_entry['timestamp'])
                
                # Extract metadata from action string
                action = raw_entry.get('action', 'unknown')
                action_clean, embedded_metadata = self._extract_metadata_from_action(action)
                
                # Combine metadata
                metadata = embedded_metadata.copy()
                if raw_entry.get('metadata'):
                    metadata['raw_metadata'] = raw_entry['metadata']
                if raw_entry.get('context'):
                    metadata['context'] = raw_entry['context']
                metadata['line_num'] = raw_entry['line_num']
                
                # Determine sequence number
                sequence_number = idx if temporal_strategy == TemporalStrategy.SEQUENCE else None
                
                entry = LogEntry(
                    entry_id=f"entry_{idx}",
                    agent_id=raw_entry.get('agent_id', 'unknown'),
                    action=action_clean,
                    timestamp=timestamp,
                    sequence_number=sequence_number,
                    metadata=metadata
                )
                
                entries.append(entry)
                
            except Exception as e:
                print(f"Warning: Failed to parse log entry at line {raw_entry['line_num']}: {e}")
                continue
        
        return ParsedLogs(
            entries=entries,
            temporal_strategy=temporal_strategy
        )


def parse_logs_text(log_file_path: str | Path) -> ParsedLogs:
    """
    Convenience function to parse text logs.
    
    Args:
        log_file_path: Path to text log file
        
    Returns:
        ParsedLogs object
    """
    parser = TextLogParser(log_file_path)
    return parser.parse()
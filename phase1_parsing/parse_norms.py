"""
Phase 1: Norm Parser
Converts raw norm specifications into structured Norm objects.
"""

import json
import yaml
from pathlib import Path
from typing import Any
from .schemas import Norm, ParsedNorms, NormType


class NormParser:
    """
    Parses normative specifications from various formats.
    
    Supports JSON and YAML formats with flexible field naming.
    Domain-independent: extracts structure without interpreting semantics.
    """
    
    # Flexible field name mappings (to handle variations in input)
    FIELD_MAPPINGS = {
        'norm_id': ['norm_id', 'id', 'norm_identifier', 'normId'],
        'norm_type': ['norm_type', 'type', 'normType', 'kind'],
        'role': ['role', 'agent_role', 'agentRole'],
        'mission': ['mission', 'goal', 'objective'],
        'condition': ['condition', 'when', 'if', 'precondition'],
        'action': ['action', 'what', 'behavior', 'prescribed_action'],
    }
    
    def __init__(self, norm_file_path: str | Path):
        """Initialize parser with path to norm specification file."""
        self.norm_file_path = Path(norm_file_path)
        
        if not self.norm_file_path.exists():
            raise FileNotFoundError(f"Norm file not found: {self.norm_file_path}")
    
    def _normalize_field_name(self, raw_data: dict, field_name: str) -> Any:
        """
        Extract field value using flexible field name matching.
        
        Args:
            raw_data: Dictionary from input file
            field_name: Canonical field name we're looking for
            
        Returns:
            Field value if found, None otherwise
        """
        possible_names = self.FIELD_MAPPINGS.get(field_name, [field_name])
        
        for name in possible_names:
            if name in raw_data:
                return raw_data[name]
        
        return None
    
    def _parse_single_norm(self, raw_norm: dict, index: int) -> Norm:
        """
        Parse a single norm from raw dictionary.
        
        Args:
            raw_norm: Raw norm data
            index: Position in file (for auto-generating IDs)
            
        Returns:
            Validated Norm object
        """
        # Extract fields using flexible matching
        norm_id = self._normalize_field_name(raw_norm, 'norm_id') or f"norm_{index}"
        norm_type = self._normalize_field_name(raw_norm, 'norm_type')
        role = self._normalize_field_name(raw_norm, 'role')
        mission = self._normalize_field_name(raw_norm, 'mission')
        condition = self._normalize_field_name(raw_norm, 'condition')
        action = self._normalize_field_name(raw_norm, 'action')
        
        # Normalize norm_type to enum
        if norm_type:
            norm_type = norm_type.lower()
            if norm_type not in [t.value for t in NormType]:
                raise ValueError(f"Invalid norm_type '{norm_type}' in norm {norm_id}")
        
        # Collect extra fields as metadata
        metadata = {
            k: v for k, v in raw_norm.items()
            if k not in ['norm_id', 'id', 'norm_type', 'type', 'role', 
                        'mission', 'condition', 'action', 'when', 'if', 'what']
        }
        
        return Norm(
            norm_id=norm_id,
            norm_type=norm_type,
            role=role,
            mission=mission,
            condition=condition,
            action=action,
            metadata=metadata
        )
    
    def parse(self) -> ParsedNorms:
        """
        Parse the norm file and return structured norms.
        
        Returns:
            ParsedNorms object containing all norms
        """
        # Determine file format
        suffix = self.norm_file_path.suffix.lower()
        
        if suffix == '.json':
            with open(self.norm_file_path, 'r') as f:
                raw_data = json.load(f)
        elif suffix in ['.yaml', '.yml']:
            with open(self.norm_file_path, 'r') as f:
                raw_data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported norm file format: {suffix}")
        
        # Handle both single-dict and list formats
        if isinstance(raw_data, dict):
            # Check if it's a wrapper with a 'norms' key
            if 'norms' in raw_data:
                raw_norms = raw_data['norms']
            else:
                # Treat entire dict as single norm
                raw_norms = [raw_data]
        elif isinstance(raw_data, list):
            raw_norms = raw_data
        else:
            raise ValueError("Norm file must contain a dict or list")
        
        # Parse each norm
        norms = []
        for idx, raw_norm in enumerate(raw_norms):
            try:
                norm = self._parse_single_norm(raw_norm, idx)
                norms.append(norm)
            except Exception as e:
                print(f"Warning: Failed to parse norm at index {idx}: {e}")
                continue
        
        return ParsedNorms(norms=norms)


def parse_norms(norm_file_path: str | Path) -> ParsedNorms:
    """
    Convenience function to parse norms with auto-format detection.
    
    Args:
        norm_file_path: Path to norm specification file
        
    Returns:
        ParsedNorms object
    """
    from pathlib import Path
    
    path = Path(norm_file_path)
    suffix = path.suffix.lower()
    
    # Auto-detect format
    if suffix == '.xml':
        from .parse_norms_xml import parse_norms_xml
        return parse_norms_xml(norm_file_path)
    elif suffix in ['.json', '.yaml', '.yml']:
        parser = NormParser(norm_file_path)
        return parser.parse()
    else:
        raise ValueError(f"Unsupported norm file format: {suffix}. Supported: .xml, .json, .yaml")
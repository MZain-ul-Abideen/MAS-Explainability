"""
Phase 1: XML Norm Parser
Converts XML normative specifications into structured Norm objects.
"""

from pathlib import Path
from lxml import etree
from typing import Optional
from .schemas import Norm, ParsedNorms, NormType


class XMLNormParser:
    """
    Parses normative specifications from XML format.
    
    Domain-independent: extracts structure based on XML tags and attributes.
    Handles various XML schemas flexibly.
    """
    
    def __init__(self, norm_file_path: str | Path):
        """Initialize parser with path to XML norm specification file."""
        self.norm_file_path = Path(norm_file_path)
        
        if not self.norm_file_path.exists():
            raise FileNotFoundError(f"Norm file not found: {self.norm_file_path}")
    
    def _get_text(self, element) -> Optional[str]:
        """Safely extract text from element."""
        if element is None:
            return None
        if hasattr(element, 'text') and element.text:
            text = element.text.strip()
            return text if text else None
        return None
    
    def _get_attr(self, element, *attr_names) -> Optional[str]:
        """Try multiple attribute names, return first found."""
        for attr in attr_names:
            if attr in element.attrib:
                val = element.attrib[attr]
                if isinstance(val, str):
                    val_stripped = val.strip()
                    return val_stripped if val_stripped else None
        return None
    
    def _find_child_text(self, element, *tag_names) -> Optional[str]:
        """Find first child with any of the given tag names and return its text."""
        for tag in tag_names:
            child = element.find(tag)
            if child is not None:
                return self._get_text(child)
        return None
    
    def _infer_norm_type_from_element(self, element) -> str:
        """
        Infer norm type from XML element.
        """
        # Get tag name safely
        tag = str(element.tag) if element.tag else ""
        tag_lower = tag.lower()
        
        # Check attributes first
        type_attr = self._get_attr(element, 'type', 'norm_type', 'kind')
        if type_attr:
            type_lower = type_attr.lower()
            if type_lower in [t.value for t in NormType]:
                return type_lower
        
        # Check tag name
        for nt in NormType:
            if nt.value in tag_lower:
                return nt.value
        
        # Default to obligation
        return NormType.OBLIGATION.value
    
    def _parse_single_norm(self, element, index: int) -> Norm:
        """
        Parse a single norm from XML element.
        
        Args:
            element: XML element representing a norm
            index: Position in file (for auto-generating IDs)
            
        Returns:
            Validated Norm object
        """
        # Extract norm_id
        norm_id = (
            self._get_attr(element, 'id', 'norm_id', 'name') or
            self._find_child_text(element, 'id', 'norm_id', 'name') or
            f"norm_{index}"
        )
        
        # Infer norm type
        norm_type = self._infer_norm_type_from_element(element)
        
        # Extract role (from attributes first, then children)
        role = (
            self._get_attr(element, 'role', 'agent_role', 'agent') or
            self._find_child_text(element, 'role', 'agent_role', 'agent', 'actor')
        )
        
        # Extract mission (from attributes first, then children)
        mission = (
            self._get_attr(element, 'mission', 'goal', 'objective') or
            self._find_child_text(element, 'mission', 'goal', 'objective', 'purpose')
        )
        
        # Extract condition (from attributes first, then children)
        condition = (
            self._get_attr(element, 'condition', 'when', 'if', 'precondition') or
            self._find_child_text(element, 'condition', 'when', 'if', 'precondition', 'trigger')
        )
        
        # Extract action (from attributes first, then children)
        action = (
            self._get_attr(element, 'action', 'what', 'behavior', 'activity') or
            self._find_child_text(element, 'action', 'what', 'behavior', 'activity', 'task')
        )
        
        # Collect all attributes as metadata
        metadata = {}
        for key, val in element.attrib.items():
            val_str = str(val) if val is not None else None
            if val_str and key not in ['id', 'norm_id', 'name', 'type', 'norm_type', 'role', 'mission', 'goal', 'condition', 'when', 'action']:
                metadata[key] = val_str
        
        # Add child elements as metadata (excluding already extracted ones)
        for child in element:
            child_tag = str(child.tag) if child.tag else None
            if child_tag and child_tag not in ['id', 'norm_id', 'role', 'mission', 'goal', 'condition', 'action', 'when', 'if']:
                child_text = self._get_text(child)
                if child_text:
                    metadata[child_tag] = child_text
        
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
        Parse the XML norm file and return structured norms.
        
        Returns:
            ParsedNorms object containing all norms
        """
        try:
            # Parse XML, removing comments
            parser = etree.XMLParser(remove_comments=True, remove_blank_text=True)
            tree = etree.parse(str(self.norm_file_path), parser)
            root = tree.getroot()
        except Exception as e:
            raise ValueError(f"Failed to parse XML file: {e}")
        
        # Extract namespace if present
        nsmap = root.nsmap if hasattr(root, 'nsmap') else {}
        default_ns = nsmap.get(None, '')
        
        # Try to find norm elements using various strategies
        norm_elements = []
        
        # Strategy 1: Look for 'norm' tags with namespace handling
        if default_ns:
            # Try with namespace
            norm_elements = root.findall('.//{%s}norm' % default_ns)
        
        if not norm_elements:
            # Try without namespace (local name only)
            norm_elements = root.xpath('.//norm | .//*[local-name()="norm"]')
        
        # Strategy 2: Look inside normative-specification container
        if not norm_elements:
            # Try to find normative-specification with and without namespace
            containers = (
                root.xpath('.//*[local-name()="normative-specification"]') +
                root.xpath('.//*[local-name()="norms"]') +
                root.xpath('.//*[local-name()="rules"]')
            )
            
            if containers:
                container = containers[0]
                # Get all direct children that look like norms
                for child in container:
                    tag_local = etree.QName(child.tag).localname if isinstance(child.tag, str) else str(child.tag)
                    if tag_local in ['norm', 'rule', 'constraint', 'obligation', 'prohibition', 'permission']:
                        norm_elements.append(child)
        
        # Strategy 3: Look for other common norm-related tags
        if not norm_elements:
            for tag in ['rule', 'constraint', 'obligation', 'prohibition', 'permission']:
                elements = root.xpath(f'.//*[local-name()="{tag}"]')
                if elements:
                    norm_elements.extend(elements)
                    break
        
        # Strategy 4: Use direct children of root
        if not norm_elements:
            norm_elements = list(root)
        
        if not norm_elements:
            print(f"Warning: No norm elements found.")
            print(f"Root tag: {root.tag}")
            print(f"Available tags: {set(etree.QName(e.tag).localname if isinstance(e.tag, str) else str(e.tag) for e in root.iter())}")
        
        # Parse each norm element
        norms = []
        for idx, element in enumerate(norm_elements):
            try:
                norm = self._parse_single_norm(element, idx)
                # Only add if we extracted meaningful normative content
                # At minimum, we need either (role + mission) or action
                if (norm.role and norm.mission) or norm.action:
                    norms.append(norm)
                else:
                    tag_local = etree.QName(element.tag).localname if isinstance(element.tag, str) else str(element.tag)
                    print(f"Info: Skipping element at index {idx} (tag: {tag_local}) - insufficient normative content")
            except Exception as e:
                print(f"Warning: Failed to parse norm element at index {idx}: {e}")
                continue
        
        print(f"Info: Successfully parsed {len(norms)} norms from {len(norm_elements)} elements")
        
        return ParsedNorms(norms=norms)


def parse_norms_xml(norm_file_path: str | Path) -> ParsedNorms:
    """
    Convenience function to parse XML norms.
    
    Args:
        norm_file_path: Path to XML norm specification file
        
    Returns:
        ParsedNorms object
    """
    parser = XMLNormParser(norm_file_path)
    return parser.parse()
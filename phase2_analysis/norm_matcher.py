"""
Phase 2: Norm Matcher
Determines which norms apply to which agents based on roles and missions.
"""

from typing import Optional
from pathlib import Path
import json
import re
from pydantic import BaseModel, Field


class AgentRoleMapping(BaseModel):
    """Maps an agent to its inferred role."""
    agent_id: str
    inferred_role: Optional[str] = None
    confidence: str = Field(default="exact")  # exact, fuzzy, unknown
    evidence: str = Field(default="")


class NormApplicability(BaseModel):
    """Determines if a norm applies to an agent."""
    norm_id: str
    agent_id: str
    applies: bool
    reason: str


class NormMatcher:
    """
    Matches agents to norms based on roles.
    
    Uses domain-independent role inference from agent IDs and metadata.
    No hard-coded role mappings.
    """
    
    def __init__(self, parsed_norms_path: Path, parsed_logs_path: Path):
        """Initialize with paths to parsed artifacts."""
        self.norms_path = parsed_norms_path
        self.logs_path = parsed_logs_path
        
        # Load parsed data
        with open(parsed_norms_path, 'r') as f:
            self.norms_data = json.load(f)
        
        with open(parsed_logs_path, 'r') as f:
            self.logs_data = json.load(f)
        
        self.norms = self.norms_data['norms']
        self.log_entries = self.logs_data['entries']
        
        # Extract unique agents
        self.agents = list(set(entry['agent_id'] for entry in self.log_entries))
    
    def _normalize_string(self, s: str) -> str:
        """Normalize string for comparison (lowercase, no special chars)."""
        if not s:
            return ""
        # Remove brackets, underscores, convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', s.lower())
        return normalized.strip()
    
    def _fuzzy_role_match(self, agent_id: str, role: str) -> tuple[bool, str]:
        """
        Check if agent_id fuzzy-matches a role.
        
        Strategies:
        1. Exact match (case-insensitive)
        2. Agent ID contains role name
        3. Role name appears in agent ID after normalization
        
        Returns:
            (matches: bool, confidence: str)
        """
        if not role:
            return False, "no_role"
        
        agent_norm = self._normalize_string(agent_id)
        role_norm = self._normalize_string(role)
        
        # Strategy 1: Exact match
        if agent_norm == role_norm:
            return True, "exact"
        
        # Strategy 2: Agent ID contains role
        if role_norm in agent_norm:
            return True, "substring"
        
        # Strategy 3: Role contains agent (e.g., agent="supplier1", role="supplier")
        if agent_norm in role_norm:
            return True, "substring_reverse"
        
        # Strategy 4: Check for role keywords in agent ID
        # Split role into parts (e.g., "ws_trunks" -> ["ws", "trunks"])
        role_parts = role_norm.split()
        agent_parts = agent_norm.split()
        
        # If any role part appears in agent parts
        for role_part in role_parts:
            if role_part in agent_norm:
                return True, "partial"
        
        return False, "no_match"
    
    def infer_agent_role(self, agent_id: str) -> AgentRoleMapping:
        """
        Infer the role of an agent based on its ID.
        
        Uses heuristics:
        - Direct name matching (e.g., "customer" agent -> "customer" role)
        - Pattern matching (e.g., "wa_trunks1" -> "ws_trunks")
        - Metadata from logs
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            AgentRoleMapping with inferred role and confidence
        """
        agent_norm = self._normalize_string(agent_id)
        
        # Check against all known roles from norms
        best_match = None
        best_confidence = None
        
        for norm in self.norms:
            role = norm.get('role')
            if not role:
                continue
            
            matches, confidence = self._fuzzy_role_match(agent_id, role)
            
            if matches:
                # Prioritize exact matches
                if confidence == "exact" or not best_match:
                    best_match = role
                    best_confidence = confidence
                elif confidence in ["substring", "substring_reverse"] and best_confidence == "partial":
                    best_match = role
                    best_confidence = confidence
        
        if best_match:
            return AgentRoleMapping(
                agent_id=agent_id,
                inferred_role=best_match,
                confidence=best_confidence,
                evidence=f"Matched '{agent_id}' to role '{best_match}' via {best_confidence}"
            )
        else:
            return AgentRoleMapping(
                agent_id=agent_id,
                inferred_role=None,
                confidence="unknown",
                evidence=f"No role match found for '{agent_id}'"
            )
    
    def check_norm_applicability(self, norm_id: str, agent_id: str) -> NormApplicability:
        """
        Check if a specific norm applies to a specific agent.
        
        Args:
            norm_id: The norm identifier
            agent_id: The agent identifier
            
        Returns:
            NormApplicability result
        """
        # Find the norm
        norm = next((n for n in self.norms if n['norm_id'] == norm_id), None)
        
        if not norm:
            return NormApplicability(
                norm_id=norm_id,
                agent_id=agent_id,
                applies=False,
                reason=f"Norm {norm_id} not found"
            )
        
        # Get required role
        required_role = norm.get('role')
        
        if not required_role:
            # If norm has no role requirement, it applies to all agents
            return NormApplicability(
                norm_id=norm_id,
                agent_id=agent_id,
                applies=True,
                reason="Norm has no role requirement (applies to all)"
            )
        
        # Infer agent's role
        role_mapping = self.infer_agent_role(agent_id)
        
        if role_mapping.inferred_role == required_role:
            return NormApplicability(
                norm_id=norm_id,
                agent_id=agent_id,
                applies=True,
                reason=f"Agent role '{role_mapping.inferred_role}' matches norm requirement '{required_role}' ({role_mapping.confidence})"
            )
        else:
            return NormApplicability(
                norm_id=norm_id,
                agent_id=agent_id,
                applies=False,
                reason=f"Agent role '{role_mapping.inferred_role}' does not match norm requirement '{required_role}'"
            )
    
    def get_applicable_norms_for_agent(self, agent_id: str) -> list[dict]:
        """
        Get all norms that apply to a specific agent.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            List of applicable norms with applicability info
        """
        applicable = []
        
        for norm in self.norms:
            applicability = self.check_norm_applicability(norm['norm_id'], agent_id)
            
            if applicability.applies:
                applicable.append({
                    'norm': norm,
                    'applicability': applicability.model_dump()
                })
        
        return applicable
    
    def build_role_mapping(self) -> dict:
        """
        Build complete mapping of all agents to their inferred roles.
        
        Returns:
            Dictionary mapping agent_id -> AgentRoleMapping
        """
        role_map = {}
        
        for agent_id in self.agents:
            role_map[agent_id] = self.infer_agent_role(agent_id).model_dump()
        
        return role_map
    
    def build_applicability_matrix(self) -> list[dict]:
        """
        Build complete matrix of norm applicability for all agents.
        
        Returns:
            List of applicability records
        """
        matrix = []
        
        for norm in self.norms:
            for agent_id in self.agents:
                applicability = self.check_norm_applicability(norm['norm_id'], agent_id)
                matrix.append(applicability.model_dump())
        
        return matrix
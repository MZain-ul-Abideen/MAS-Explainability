"""
Phase 2: Compliance Checker
Verifies whether agents fulfilled, violated, or were not subject to norms.
"""

from typing import Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field
from enum import Enum


class ComplianceStatus(str, Enum):
    """Possible compliance states."""
    FULFILLED = "fulfilled"
    VIOLATED = "violated"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ComplianceResult(BaseModel):
    """Result of compliance checking for a norm-agent pair."""
    norm_id: str
    agent_id: str
    status: ComplianceStatus
    evidence: list[dict] = Field(default_factory=list)
    reasoning: str = ""


class ComplianceChecker:
    """
    Checks compliance of agents against norms based on logged behavior.
    
    Purely evidence-based: only uses what's recorded in logs.
    """
    
    def __init__(
        self,
        parsed_norms_path: Path,
        parsed_logs_path: Path,
        role_mapping: dict,
        applicability_matrix: list[dict]
    ):
        """
        Initialize compliance checker.
        
        Args:
            parsed_norms_path: Path to parsed norms
            parsed_logs_path: Path to parsed logs
            role_mapping: Agent-to-role mapping from NormMatcher
            applicability_matrix: Norm applicability matrix from NormMatcher
        """
        # Load parsed data
        with open(parsed_norms_path, 'r') as f:
            self.norms_data = json.load(f)
        
        with open(parsed_logs_path, 'r') as f:
            self.logs_data = json.load(f)
        
        self.norms = self.norms_data['norms']
        self.log_entries = self.logs_data['entries']
        self.temporal_strategy = self.logs_data.get('temporal_strategy')
        
        self.role_mapping = role_mapping
        self.applicability_matrix = applicability_matrix
        
        # Build index of logs by agent
        self._build_agent_action_index()
    
    def _build_agent_action_index(self):
        """Build index: agent_id -> list of actions with metadata."""
        self.agent_actions = {}
        
        for entry in self.log_entries:
            agent_id = entry['agent_id']
            
            if agent_id not in self.agent_actions:
                self.agent_actions[agent_id] = []
            
            self.agent_actions[agent_id].append({
                'entry_id': entry['entry_id'],
                'action': entry['action'],
                'timestamp': entry.get('timestamp'),
                'sequence_number': entry.get('sequence_number'),
                'metadata': entry.get('metadata', {})
            })
    
    def _normalize_action_or_mission(self, s: str) -> str:
        """Normalize action/mission string for comparison."""
        if not s:
            return ""
        # Convert to lowercase, replace underscores/hyphens with spaces
        normalized = s.lower().replace('_', ' ').replace('-', ' ')
        return normalized.strip()
    
    def _mission_action_match(self, action: str, mission: str) -> tuple[bool, str]:
        """
        Check if an action fulfills a mission.
        
        Strategies:
        1. Direct match (action == mission)
        2. Action contains mission keywords
        3. Semantic similarity (future enhancement)
        
        Returns:
            (matches: bool, match_type: str)
        """
        if not mission:
            return False, "no_mission"
        
        action_norm = self._normalize_action_or_mission(action)
        mission_norm = self._normalize_action_or_mission(mission)
        
        # Strategy 1: Exact match
        if action_norm == mission_norm:
            return True, "exact"
        
        # Strategy 2: Action contains mission
        if mission_norm in action_norm:
            return True, "contains_mission"
        
        # Strategy 3: Mission contains action
        if action_norm in mission_norm:
            return True, "mission_contains_action"
        
        # Strategy 4: Keyword overlap
        mission_words = set(mission_norm.split())
        action_words = set(action_norm.split())
        
        overlap = mission_words & action_words
        if len(overlap) >= len(mission_words) * 0.5:  # 50% keyword overlap
            return True, "keyword_overlap"
        
        return False, "no_match"
    
    def _is_norm_applicable(self, norm_id: str, agent_id: str) -> bool:
        """Check if norm applies to agent using applicability matrix."""
        for record in self.applicability_matrix:
            if record['norm_id'] == norm_id and record['agent_id'] == agent_id:
                return record['applies']
        return False
    
    def check_compliance(self, norm_id: str, agent_id: str) -> ComplianceResult:
        """
        Check if an agent complied with a specific norm.
        
        Args:
            norm_id: The norm identifier
            agent_id: The agent identifier
            
        Returns:
            ComplianceResult with status and evidence
        """
        # Find the norm
        norm = next((n for n in self.norms if n['norm_id'] == norm_id), None)
        
        if not norm:
            return ComplianceResult(
                norm_id=norm_id,
                agent_id=agent_id,
                status=ComplianceStatus.UNKNOWN,
                reasoning=f"Norm {norm_id} not found"
            )
        
        # Check if norm applies to this agent
        if not self._is_norm_applicable(norm_id, agent_id):
            return ComplianceResult(
                norm_id=norm_id,
                agent_id=agent_id,
                status=ComplianceStatus.NOT_APPLICABLE,
                reasoning=f"Norm does not apply to agent {agent_id}"
            )
        
        # Get agent's actions
        actions = self.agent_actions.get(agent_id, [])
        
        if not actions:
            # Agent exists but performed no actions
            return ComplianceResult(
                norm_id=norm_id,
                agent_id=agent_id,
                status=ComplianceStatus.VIOLATED,
                reasoning="Agent performed no actions (norm requires action)"
            )
        
        # Check compliance based on norm type
        norm_type = norm['norm_type']
        mission = norm.get('mission')
        required_action = norm.get('action')
        
        evidence = []
        
        # For obligations: must find evidence of fulfillment
        if norm_type == 'obligation':
            # Check if any action fulfills the mission
            fulfilled = False
            
            for action_entry in actions:
                action = action_entry['action']
                
                # Try to match action to mission
                if mission:
                    matches, match_type = self._mission_action_match(action, mission)
                    if matches:
                        fulfilled = True
                        evidence.append({
                            'entry_id': action_entry['entry_id'],
                            'action': action,
                            'match_type': match_type,
                            'matched_to': mission,
                            'timestamp': action_entry.get('timestamp'),
                            'sequence_number': action_entry.get('sequence_number')
                        })
                
                # Also check against required action if specified
                if required_action:
                    matches, match_type = self._mission_action_match(action, required_action)
                    if matches:
                        fulfilled = True
                        evidence.append({
                            'entry_id': action_entry['entry_id'],
                            'action': action,
                            'match_type': match_type,
                            'matched_to': required_action,
                            'timestamp': action_entry.get('timestamp'),
                            'sequence_number': action_entry.get('sequence_number')
                        })
            
            if fulfilled:
                return ComplianceResult(
                    norm_id=norm_id,
                    agent_id=agent_id,
                    status=ComplianceStatus.FULFILLED,
                    evidence=evidence,
                    reasoning=f"Found {len(evidence)} action(s) fulfilling obligation '{mission or required_action}'"
                )
            else:
                return ComplianceResult(
                    norm_id=norm_id,
                    agent_id=agent_id,
                    status=ComplianceStatus.VIOLATED,
                    reasoning=f"No actions found fulfilling obligation '{mission or required_action}'"
                )
        
        # For prohibitions: must NOT find forbidden action
        elif norm_type == 'prohibition':
            violated = False
            
            for action_entry in actions:
                action = action_entry['action']
                
                if required_action:
                    matches, match_type = self._mission_action_match(action, required_action)
                    if matches:
                        violated = True
                        evidence.append({
                            'entry_id': action_entry['entry_id'],
                            'action': action,
                            'match_type': match_type,
                            'violated_prohibition': required_action,
                            'timestamp': action_entry.get('timestamp'),
                            'sequence_number': action_entry.get('sequence_number')
                        })
            
            if violated:
                return ComplianceResult(
                    norm_id=norm_id,
                    agent_id=agent_id,
                    status=ComplianceStatus.VIOLATED,
                    evidence=evidence,
                    reasoning=f"Agent performed prohibited action '{required_action}' {len(evidence)} time(s)"
                )
            else:
                return ComplianceResult(
                    norm_id=norm_id,
                    agent_id=agent_id,
                    status=ComplianceStatus.FULFILLED,
                    reasoning=f"Agent did not perform prohibited action '{required_action}'"
                )
        
        # For permissions: just log if used
        elif norm_type == 'permission':
            used = False
            
            for action_entry in actions:
                action = action_entry['action']
                
                if required_action or mission:
                    target = required_action or mission
                    matches, match_type = self._mission_action_match(action, target)
                    if matches:
                        used = True
                        evidence.append({
                            'entry_id': action_entry['entry_id'],
                            'action': action,
                            'match_type': match_type,
                            'used_permission': target,
                            'timestamp': action_entry.get('timestamp'),
                            'sequence_number': action_entry.get('sequence_number')
                        })
            
            return ComplianceResult(
                norm_id=norm_id,
                agent_id=agent_id,
                status=ComplianceStatus.FULFILLED,
                evidence=evidence,
                reasoning=f"Permission {'used' if used else 'not used'} ({len(evidence)} occurrences)"
            )
        
        return ComplianceResult(
            norm_id=norm_id,
            agent_id=agent_id,
            status=ComplianceStatus.UNKNOWN,
            reasoning=f"Unknown norm type: {norm_type}"
        )
    
    def check_all_compliance(self) -> list[ComplianceResult]:
        """
        Check compliance for all norm-agent pairs where norm applies.
        
        Returns:
            List of all compliance results
        """
        results = []
        
        # Get unique agents
        agents = list(self.agent_actions.keys())
        
        for norm in self.norms:
            for agent_id in agents:
                result = self.check_compliance(norm['norm_id'], agent_id)
                results.append(result.model_dump())
        
        return results
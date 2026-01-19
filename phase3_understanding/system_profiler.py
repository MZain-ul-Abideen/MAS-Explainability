"""
Phase 3: System Profiler
Builds a comprehensive understanding of the MAS from norms, logs, and compliance results.
"""

from typing import Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field
from collections import defaultdict, Counter


class AgentProfile(BaseModel):
    """Profile of a single agent."""
    agent_id: str
    inferred_role: Optional[str] = None
    role_confidence: str = "unknown"
    total_actions: int = 0
    unique_actions: int = 0
    action_summary: dict[str, int] = Field(default_factory=dict)
    applicable_norms: list[str] = Field(default_factory=list)
    compliance_status: dict[str, str] = Field(default_factory=dict)  # norm_id -> status
    first_appearance: Optional[int] = None
    last_appearance: Optional[int] = None


class MissionProfile(BaseModel):
    """Profile of a mission from norms."""
    mission_name: str
    required_roles: list[str] = Field(default_factory=list)
    associated_norms: list[str] = Field(default_factory=list)
    agents_assigned: list[str] = Field(default_factory=list)
    fulfillment_status: dict[str, str] = Field(default_factory=dict)  # agent_id -> status


class InteractionProfile(BaseModel):
    """Profile of agent interactions (inferred from logs)."""
    source_agent: str
    target_agent: Optional[str] = None
    interaction_type: str  # e.g., "registration", "communication", "coordination"
    frequency: int = 0
    evidence: list[str] = Field(default_factory=list)  # entry_ids


class SystemProfile(BaseModel):
    """Complete profile of the MAS."""
    # Agents
    total_agents: int = 0
    agents: dict[str, AgentProfile] = Field(default_factory=dict)
    
    # Roles
    total_roles: int = 0
    roles: dict[str, list[str]] = Field(default_factory=dict)  # role -> [agent_ids]
    
    # Norms
    total_norms: int = 0
    norms_by_type: dict[str, int] = Field(default_factory=dict)
    norms_by_role: dict[str, list[str]] = Field(default_factory=dict)  # role -> [norm_ids]
    
    # Missions
    total_missions: int = 0
    missions: dict[str, MissionProfile] = Field(default_factory=dict)
    
    # Execution
    total_events: int = 0
    temporal_strategy: str = "sequence"
    execution_timeline: list[dict] = Field(default_factory=list)
    
    # Compliance
    compliance_summary: dict[str, int] = Field(default_factory=dict)  # status -> count
    
    # Interactions (optional, derived from logs)
    interactions: list[InteractionProfile] = Field(default_factory=list)


class SystemProfiler:
    """
    Builds a comprehensive understanding of the MAS.
    
    Extracts and organizes facts from all available artifacts.
    """
    
    def __init__(
        self,
        parsed_norms_path: Path,
        parsed_logs_path: Path,
        compliance_results_path: Path
    ):
        """Initialize with paths to all artifacts."""
        # Load all artifacts
        with open(parsed_norms_path, 'r') as f:
            self.norms_data = json.load(f)
        
        with open(parsed_logs_path, 'r') as f:
            self.logs_data = json.load(f)
        
        with open(compliance_results_path, 'r') as f:
            self.compliance_data = json.load(f)
        
        self.norms = self.norms_data['norms']
        self.log_entries = self.logs_data['entries']
        self.temporal_strategy = self.logs_data.get('temporal_strategy', 'sequence')
        
        self.role_mapping = self.compliance_data['role_mapping']
        self.compliance_results = self.compliance_data['compliance_results']
    
    def _extract_target_agent(self, action: str, metadata: dict) -> Optional[str]:
        """Try to extract target agent from action/metadata."""
        # Look for common patterns indicating agent-to-agent interaction
        # e.g., "Registered wa_wheels1 for operation"
        import re
        
        # Pattern 1: "Registered <agent>"
        match = re.search(r'Registered\s+(\w+)', action)
        if match:
            return match.group(1)
        
        # Pattern 2: Check metadata for agent references
        for key in ['target', 'to', 'agent', 'assigned_to']:
            if key in metadata:
                return metadata[key]
        
        return None
    
    def build_agent_profiles(self) -> dict[str, AgentProfile]:
        """Build profiles for all agents."""
        profiles = {}
        
        # Get unique agents
        agents = set(entry['agent_id'] for entry in self.log_entries)
        
        for agent_id in agents:
            # Get agent's actions
            agent_entries = [e for e in self.log_entries if e['agent_id'] == agent_id]
            
            # Count actions
            actions = [e['action'] for e in agent_entries]
            action_counts = Counter(actions)
            
            # Get temporal bounds
            if agent_entries:
                sequences = [e.get('sequence_number') for e in agent_entries if e.get('sequence_number') is not None]
                first_seq = min(sequences) if sequences else None
                last_seq = max(sequences) if sequences else None
            else:
                first_seq = last_seq = None
            
            # Get role info
            role_info = self.role_mapping.get(agent_id, {})
            
            # Get applicable norms
            applicable_norms = []
            compliance_status = {}
            
            for result in self.compliance_results:
                if result['agent_id'] == agent_id and result['status'] != 'not_applicable':
                    norm_id = result['norm_id']
                    applicable_norms.append(norm_id)
                    compliance_status[norm_id] = result['status']
            
            profile = AgentProfile(
                agent_id=agent_id,
                inferred_role=role_info.get('inferred_role'),
                role_confidence=role_info.get('confidence', 'unknown'),
                total_actions=len(actions),
                unique_actions=len(set(actions)),
                action_summary=dict(action_counts.most_common(10)),  # Top 10 actions
                applicable_norms=applicable_norms,
                compliance_status=compliance_status,
                first_appearance=first_seq,
                last_appearance=last_seq
            )
            
            profiles[agent_id] = profile
        
        return profiles
    
    def build_mission_profiles(self) -> dict[str, MissionProfile]:
        """Build profiles for all missions."""
        missions = {}
        
        # Extract unique missions from norms
        for norm in self.norms:
            mission = norm.get('mission')
            if not mission:
                continue
            
            if mission not in missions:
                missions[mission] = MissionProfile(
                    mission_name=mission,
                    required_roles=[],
                    associated_norms=[],
                    agents_assigned=[],
                    fulfillment_status={}
                )
            
            # Add role requirement
            role = norm.get('role')
            if role and role not in missions[mission].required_roles:
                missions[mission].required_roles.append(role)
            
            # Add norm
            missions[mission].associated_norms.append(norm['norm_id'])
        
        # Add agent assignments and fulfillment status
        for result in self.compliance_results:
            if result['status'] == 'not_applicable':
                continue
            
            # Find mission for this norm
            norm = next((n for n in self.norms if n['norm_id'] == result['norm_id']), None)
            if not norm or not norm.get('mission'):
                continue
            
            mission = norm['mission']
            agent_id = result['agent_id']
            
            if agent_id not in missions[mission].agents_assigned:
                missions[mission].agents_assigned.append(agent_id)
            
            missions[mission].fulfillment_status[agent_id] = result['status']
        
        return missions
    
    def build_execution_timeline(self) -> list[dict]:
        """Build chronological timeline of events."""
        timeline = []
        
        # Sort entries by temporal marker
        sorted_entries = sorted(
            self.log_entries,
            key=lambda e: e.get('sequence_number', 0) if self.temporal_strategy == 'sequence' else e.get('timestamp', '')
        )
        
        for entry in sorted_entries:
            timeline.append({
                'entry_id': entry['entry_id'],
                'agent_id': entry['agent_id'],
                'action': entry['action'],
                'temporal_marker': entry.get('sequence_number') or entry.get('timestamp'),
                'metadata': entry.get('metadata', {})
            })
        
        return timeline
    
    def detect_interactions(self) -> list[InteractionProfile]:
        """Detect agent-to-agent interactions from logs."""
        interactions = defaultdict(lambda: {'count': 0, 'evidence': []})
        
        for entry in self.log_entries:
            source = entry['agent_id']
            action = entry['action']
            metadata = entry.get('metadata', {})
            
            # Try to find target agent
            target = self._extract_target_agent(action, metadata)
            
            if target:
                # Classify interaction type
                action_lower = action.lower()
                if 'register' in action_lower:
                    int_type = 'registration'
                elif 'send' in action_lower or 'deliver' in action_lower:
                    int_type = 'delivery'
                elif 'request' in action_lower or 'ask' in action_lower:
                    int_type = 'request'
                else:
                    int_type = 'coordination'
                
                key = (source, target, int_type)
                interactions[key]['count'] += 1
                interactions[key]['evidence'].append(entry['entry_id'])
        
        # Convert to InteractionProfile objects
        interaction_profiles = []
        for (source, target, int_type), data in interactions.items():
            interaction_profiles.append(InteractionProfile(
                source_agent=source,
                target_agent=target,
                interaction_type=int_type,
                frequency=data['count'],
                evidence=data['evidence'][:5]  # Keep top 5 evidence entries
            ))
        
        return interaction_profiles
    
    def build_profile(self) -> SystemProfile:
        """Build complete system profile."""
        print("Building system profile...")
        
        # Build agent profiles
        print("  [1/6] Profiling agents...")
        agents = self.build_agent_profiles()
        
        # Build role mapping
        print("  [2/6] Mapping roles...")
        roles = defaultdict(list)
        for agent_id, profile in agents.items():
            if profile.inferred_role:
                roles[profile.inferred_role].append(agent_id)
        
        # Build norm organization
        print("  [3/6] Organizing norms...")
        norms_by_type = Counter(n['norm_type'] for n in self.norms)
        norms_by_role = defaultdict(list)
        for norm in self.norms:
            role = norm.get('role')
            if role:
                norms_by_role[role].append(norm['norm_id'])
        
        # Build mission profiles
        print("  [4/6] Profiling missions...")
        missions = self.build_mission_profiles()
        
        # Build execution timeline
        print("  [5/6] Building execution timeline...")
        timeline = self.build_execution_timeline()
        
        # Detect interactions
        print("  [6/6] Detecting interactions...")
        interactions = self.detect_interactions()
        
        # Build compliance summary
        compliance_summary = Counter(r['status'] for r in self.compliance_results)
        
        profile = SystemProfile(
            total_agents=len(agents),
            agents=agents,
            total_roles=len(roles),
            roles=dict(roles),
            total_norms=len(self.norms),
            norms_by_type=dict(norms_by_type),
            norms_by_role=dict(norms_by_role),
            total_missions=len(missions),
            missions=missions,
            total_events=len(self.log_entries),
            temporal_strategy=self.temporal_strategy,
            execution_timeline=timeline,
            compliance_summary=dict(compliance_summary),
            interactions=interactions
        )
        
        return profile


def build_system_profile(
    parsed_norms_path: Path,
    parsed_logs_path: Path,
    compliance_results_path: Path
) -> SystemProfile:
    """
    Convenience function to build system profile.
    
    Args:
        parsed_norms_path: Path to parsed norms
        parsed_logs_path: Path to parsed logs
        compliance_results_path: Path to compliance results
        
    Returns:
        SystemProfile object
    """
    profiler = SystemProfiler(parsed_norms_path, parsed_logs_path, compliance_results_path)
    return profiler.build_profile()
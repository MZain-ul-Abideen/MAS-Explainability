"""
Phase 4: Evidence Retriever
Retrieves relevant facts from artifacts based on user queries.
"""

from typing import Optional
from pathlib import Path
import json
import re
from pydantic import BaseModel, Field


class EvidencePacket(BaseModel):
    """Structured evidence retrieved for a query."""
    query: str
    query_type: str  # agent, norm, mission, compliance, timeline, overview
    
    # Relevant data
    relevant_agents: list[dict] = Field(default_factory=list)
    relevant_norms: list[dict] = Field(default_factory=list)
    relevant_missions: list[dict] = Field(default_factory=list)
    relevant_log_entries: list[dict] = Field(default_factory=list)
    relevant_compliance: list[dict] = Field(default_factory=list)
    relevant_interactions: list[dict] = Field(default_factory=list)
    
    # Context
    system_overview: Optional[dict] = None
    
    # Metadata
    retrieval_strategy: str = ""
    total_items_retrieved: int = 0


class EvidenceRetriever:
    """
    Retrieves relevant evidence from artifacts based on queries.
    
    Uses keyword matching and entity extraction (no LLM at this stage).
    """
    
    def __init__(self, artifacts_dir: Path):
        """Initialize with path to artifacts directory."""
        self.artifacts_dir = Path(artifacts_dir)
        
        # Load all artifacts
        with open(self.artifacts_dir / "parsed_norms.json", 'r') as f:
            self.norms_data = json.load(f)
        
        with open(self.artifacts_dir / "parsed_logs.json", 'r') as f:
            self.logs_data = json.load(f)
        
        with open(self.artifacts_dir / "compliance_results.json", 'r') as f:
            self.compliance_data = json.load(f)
        
        with open(self.artifacts_dir / "system_profile.json", 'r') as f:
            self.profile_data = json.load(f)
        
        self.norms = self.norms_data['norms']
        self.log_entries = self.logs_data['entries']
        self.compliance_results = self.compliance_data['compliance_results']
        self.agents = self.profile_data['agents']
        self.missions = self.profile_data['missions']
        self.interactions = self.profile_data['interactions']
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        return re.sub(r'[^\w\s]', '', text.lower()).strip()
    
    def _extract_entities(self, query: str) -> dict:
        """
        Extract potential entities from query.
        
        Looks for:
        - Agent names/IDs
        - Role names
        - Mission names
        - Norm IDs
        - Action keywords
        """
        query_norm = self._normalize_text(query)
        entities = {
            'agents': [],
            'roles': [],
            'missions': [],
            'norms': [],
            'actions': [],
            'keywords': query_norm.split()
        }
        
        # Extract agent references
        for agent_id in self.agents.keys():
            if self._normalize_text(agent_id) in query_norm:
                entities['agents'].append(agent_id)
        
        # Extract role references
        for role in self.profile_data.get('roles', {}).keys():
            if self._normalize_text(role) in query_norm:
                entities['roles'].append(role)
        
        # Extract mission references
        for mission in self.missions.keys():
            if self._normalize_text(mission) in query_norm:
                entities['missions'].append(mission)
        
        # Extract norm IDs (e.g., "n1", "norm_1")
        norm_pattern = r'\b(n\d+|norm_?\d+)\b'
        norm_matches = re.findall(norm_pattern, query.lower())
        entities['norms'].extend(norm_matches)
        
        return entities
    
    def _classify_query(self, query: str, entities: dict) -> str:
        """
        Classify query type based on content and entities.
        
        Types:
        - agent: Questions about specific agents
        - norm: Questions about norms/rules
        - mission: Questions about missions/goals
        - compliance: Questions about violations/fulfillment
        - timeline: Questions about when/sequence
        - overview: General questions about the system
        """
        query_lower = query.lower()
        
        # Check for compliance keywords
        if any(kw in query_lower for kw in ['violat', 'fulfill', 'comply', 'complian', 'satisfy', 'follow']):
            return 'compliance'
        
        # Check for timeline keywords
        if any(kw in query_lower for kw in ['when', 'first', 'last', 'before', 'after', 'sequence', 'order', 'timeline']):
            return 'timeline'
        
        # Check for specific entities
        if entities['agents']:
            return 'agent'
        
        if entities['norms'] or 'norm' in query_lower or 'rule' in query_lower:
            return 'norm'
        
        if entities['missions'] or 'mission' in query_lower or 'goal' in query_lower:
            return 'mission'
        
        # Check for overview keywords
        if any(kw in query_lower for kw in ['overview', 'summary', 'all', 'list', 'what are', 'how many']):
            return 'overview'
        
        # Default to agent if specific agent mentioned
        if entities['agents']:
            return 'agent'
        
        return 'overview'
    
    def _retrieve_agent_evidence(self, entities: dict) -> dict:
        """Retrieve evidence related to specific agents."""
        evidence = {
            'agents': [],
            'log_entries': [],
            'compliance': [],
            'interactions': []
        }
        
        target_agents = entities['agents']
        
        # If no specific agents, use agents from roles
        if not target_agents and entities['roles']:
            for role in entities['roles']:
                target_agents.extend(self.profile_data['roles'].get(role, []))
        
        # Get agent profiles
        for agent_id in target_agents:
            if agent_id in self.agents:
                evidence['agents'].append(self.agents[agent_id])
        
        # Get relevant log entries
        for entry in self.log_entries:
            if entry['agent_id'] in target_agents:
                evidence['log_entries'].append(entry)
        
        # Get compliance results
        for result in self.compliance_results:
            if result['agent_id'] in target_agents and result['status'] != 'not_applicable':
                evidence['compliance'].append(result)
        
        # Get interactions
        for interaction in self.interactions:
            if interaction['source_agent'] in target_agents or interaction.get('target_agent') in target_agents:
                evidence['interactions'].append(interaction)
        
        return evidence
    
    def _retrieve_norm_evidence(self, entities: dict) -> dict:
        """Retrieve evidence related to norms."""
        evidence = {
            'norms': [],
            'compliance': [],
            'agents': []
        }
        
        # Get specific norms
        target_norm_ids = entities['norms']
        
        # If no specific norms, get all from mentioned roles/missions
        if not target_norm_ids:
            if entities['roles']:
                for norm in self.norms:
                    if norm.get('role') in entities['roles']:
                        target_norm_ids.append(norm['norm_id'])
            
            if entities['missions']:
                for norm in self.norms:
                    if norm.get('mission') in entities['missions']:
                        target_norm_ids.append(norm['norm_id'])
        
        # Get norm details
        for norm in self.norms:
            if norm['norm_id'] in target_norm_ids or not target_norm_ids:
                evidence['norms'].append(norm)
        
        # Get compliance for these norms
        for result in self.compliance_results:
            if result['norm_id'] in target_norm_ids or not target_norm_ids:
                if result['status'] != 'not_applicable':
                    evidence['compliance'].append(result)
                    
                    # Also get agent profiles
                    if result['agent_id'] in self.agents:
                        if result['agent_id'] not in [a['agent_id'] for a in evidence['agents']]:
                            evidence['agents'].append(self.agents[result['agent_id']])
        
        return evidence
    
    def _retrieve_mission_evidence(self, entities: dict) -> dict:
        """Retrieve evidence related to missions."""
        evidence = {
            'missions': [],
            'norms': [],
            'agents': [],
            'compliance': []
        }
        
        target_missions = entities['missions'] or list(self.missions.keys())
        
        # Get mission profiles
        for mission_name in target_missions:
            if mission_name in self.missions:
                evidence['missions'].append(self.missions[mission_name])
        
        # Get related norms
        for norm in self.norms:
            if norm.get('mission') in target_missions:
                evidence['norms'].append(norm)
        
        # Get agents assigned to these missions
        for mission_name in target_missions:
            if mission_name in self.missions:
                mission = self.missions[mission_name]
                for agent_id in mission.get('agents_assigned', []):
                    if agent_id in self.agents:
                        if agent_id not in [a['agent_id'] for a in evidence['agents']]:
                            evidence['agents'].append(self.agents[agent_id])
        
        # Get compliance for mission-related norms
        mission_norm_ids = [n['norm_id'] for n in evidence['norms']]
        for result in self.compliance_results:
            if result['norm_id'] in mission_norm_ids and result['status'] != 'not_applicable':
                evidence['compliance'].append(result)
        
        return evidence
    
    def _retrieve_compliance_evidence(self, entities: dict, query: str) -> dict:
        """Retrieve evidence related to compliance questions."""
        evidence = {
            'compliance': [],
            'norms': [],
            'agents': [],
            'log_entries': []
        }
        
        query_lower = query.lower()
        
        # Filter compliance by status if specified
        target_status = None
        if 'violat' in query_lower:
            target_status = 'violated'
        elif 'fulfill' in query_lower or 'satisfy' in query_lower or 'comply' in query_lower:
            target_status = 'fulfilled'
        
        # Get compliance results
        for result in self.compliance_results:
            if result['status'] == 'not_applicable':
                continue
            
            # Filter by status if specified
            if target_status and result['status'] != target_status:
                continue
            
            # Filter by entities if present
            if entities['agents'] and result['agent_id'] not in entities['agents']:
                continue
            
            if entities['norms'] and result['norm_id'] not in entities['norms']:
                continue
            
            evidence['compliance'].append(result)
            
            # Add related norm
            norm = next((n for n in self.norms if n['norm_id'] == result['norm_id']), None)
            if norm and norm not in evidence['norms']:
                evidence['norms'].append(norm)
            
            # Add related agent
            if result['agent_id'] in self.agents:
                if result['agent_id'] not in [a['agent_id'] for a in evidence['agents']]:
                    evidence['agents'].append(self.agents[result['agent_id']])
            
            # Add evidence log entries
            for ev in result.get('evidence', []):
                entry_id = ev.get('entry_id')
                log_entry = next((e for e in self.log_entries if e['entry_id'] == entry_id), None)
                if log_entry and log_entry not in evidence['log_entries']:
                    evidence['log_entries'].append(log_entry)
        
        return evidence
    
    def _retrieve_timeline_evidence(self, entities: dict, query: str) -> dict:
        """Retrieve evidence related to timeline questions."""
        evidence = {
            'log_entries': [],
            'agents': []
        }
        
        query_lower = query.lower()
        
        # Get relevant logs
        if entities['agents']:
            # Specific agent timeline
            for entry in self.log_entries:
                if entry['agent_id'] in entities['agents']:
                    evidence['log_entries'].append(entry)
        else:
            # Full timeline (limit to reasonable size)
            evidence['log_entries'] = self.log_entries[:100]
        
        # Add agent profiles
        agent_ids = set(e['agent_id'] for e in evidence['log_entries'])
        for agent_id in agent_ids:
            if agent_id in self.agents:
                evidence['agents'].append(self.agents[agent_id])
        
        return evidence
    
    def _retrieve_overview_evidence(self, query: str) -> dict:
        """Retrieve evidence for overview questions."""
        evidence = {
            'system_overview': {
                'total_agents': self.profile_data['total_agents'],
                'total_norms': self.profile_data['total_norms'],
                'total_missions': self.profile_data['total_missions'],
                'total_events': self.profile_data['total_events'],
                'roles': self.profile_data['roles'],
                'norms_by_type': self.profile_data['norms_by_type'],
                'compliance_summary': self.profile_data['compliance_summary']
            },
            'agents': list(self.agents.values())[:10],  # Top 10 agents
            'norms': self.norms,
            'missions': list(self.missions.values())
        }
        
        return evidence
    
    def retrieve(self, query: str) -> EvidencePacket:
        """
        Retrieve relevant evidence for a query.
        
        Args:
            query: User's natural language question
            
        Returns:
            EvidencePacket with relevant facts
        """
        # Extract entities
        entities = self._extract_entities(query)
        
        # Classify query
        query_type = self._classify_query(query, entities)
        
        # Retrieve based on type
        if query_type == 'agent':
            evidence = self._retrieve_agent_evidence(entities)
            strategy = f"Agent-focused retrieval for: {', '.join(entities['agents'])}"
        
        elif query_type == 'norm':
            evidence = self._retrieve_norm_evidence(entities)
            strategy = "Norm-focused retrieval"
        
        elif query_type == 'mission':
            evidence = self._retrieve_mission_evidence(entities)
            strategy = f"Mission-focused retrieval for: {', '.join(entities['missions'])}"
        
        elif query_type == 'compliance':
            evidence = self._retrieve_compliance_evidence(entities, query)
            strategy = "Compliance-focused retrieval"
        
        elif query_type == 'timeline':
            evidence = self._retrieve_timeline_evidence(entities, query)
            strategy = "Timeline-focused retrieval"
        
        else:  # overview
            evidence = self._retrieve_overview_evidence(query)
            strategy = "System overview retrieval"
        
        # Build packet
        packet = EvidencePacket(
            query=query,
            query_type=query_type,
            relevant_agents=evidence.get('agents', []),
            relevant_norms=evidence.get('norms', []),
            relevant_missions=evidence.get('missions', []),
            relevant_log_entries=evidence.get('log_entries', []),
            relevant_compliance=evidence.get('compliance', []),
            relevant_interactions=evidence.get('interactions', []),
            system_overview=evidence.get('system_overview'),
            retrieval_strategy=strategy
        )
        
        # Count total items
        packet.total_items_retrieved = (
            len(packet.relevant_agents) +
            len(packet.relevant_norms) +
            len(packet.relevant_missions) +
            len(packet.relevant_log_entries) +
            len(packet.relevant_compliance) +
            len(packet.relevant_interactions)
        )
        
        return packet


def retrieve_evidence(artifacts_dir: Path, query: str) -> EvidencePacket:
    """
    Convenience function to retrieve evidence.
    
    Args:
        artifacts_dir: Path to artifacts directory
        query: User's question
        
    Returns:
        EvidencePacket
    """
    retriever = EvidenceRetriever(artifacts_dir)
    return retriever.retrieve(query)
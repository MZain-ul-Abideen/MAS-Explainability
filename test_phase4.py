"""
Phase 4 Test Script
Test evidence retrieval for various query types.
"""

import json
from pathlib import Path
from phase4_retrieval.evidence_retriever import retrieve_evidence


def test_query(artifacts_dir: Path, query: str):
    """Test a single query and display results."""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    packet = retrieve_evidence(artifacts_dir, query)
    
    print(f"Query Type: {packet.query_type}")
    print(f"Strategy: {packet.retrieval_strategy}")
    print(f"Total Items Retrieved: {packet.total_items_retrieved}")
    
    print(f"\nEvidence Breakdown:")
    print(f"  Agents: {len(packet.relevant_agents)}")
    print(f"  Norms: {len(packet.relevant_norms)}")
    print(f"  Missions: {len(packet.relevant_missions)}")
    print(f"  Log Entries: {len(packet.relevant_log_entries)}")
    print(f"  Compliance Results: {len(packet.relevant_compliance)}")
    print(f"  Interactions: {len(packet.relevant_interactions)}")
    
    # Show samples
    if packet.relevant_agents:
        print(f"\n  Sample Agents:")
        for agent in packet.relevant_agents[:3]:
            print(f"    - {agent['agent_id']} (role: {agent.get('inferred_role', 'unknown')})")
    
    if packet.relevant_norms:
        print(f"\n  Sample Norms:")
        for norm in packet.relevant_norms[:3]:
            print(f"    - {norm['norm_id']}: {norm.get('role')} must {norm.get('mission')}")
    
    if packet.relevant_compliance:
        print(f"\n  Sample Compliance:")
        for comp in packet.relevant_compliance[:3]:
            print(f"    - {comp['agent_id']} {comp['status']} {comp['norm_id']}")
    
    return packet


def main():
    print("=" * 60)
    print("PHASE 4: EVIDENCE RETRIEVAL TEST")
    print("=" * 60)
    
    artifacts_dir = Path("artifacts")
    
    # Test different query types
    test_queries = [
        # Agent queries
        "What did the assembly agent do?",
        "Tell me about the customer agent",
        
        # Norm queries
        "What norms apply to suppliers?",
        "Show me all obligations",
        
        # Mission queries
        "What is the manage_assembly mission?",
        "Who is responsible for deliver_parts?",
        
        # Compliance queries
        "Which norms were violated?",
        "Did the assembly agent fulfill its obligations?",
        
        # Timeline queries
        "What happened first?",
        "Show me the timeline for the assembly agent",
        
        # Overview queries
        "Give me an overview of the system",
        "How many agents are there?",
    ]
    
    packets = []
    
    for query in test_queries:
        packet = test_query(artifacts_dir, query)
        packets.append(packet)
    
    # Save all evidence packets
    print(f"\n{'='*60}")
    print("Saving evidence packets...")
    
    evidence_dir = artifacts_dir / "evidence_cache"
    evidence_dir.mkdir(exist_ok=True)
    
    for i, packet in enumerate(packets):
        output_file = evidence_dir / f"evidence_{i}.json"
        with open(output_file, "w") as f:
            json.dump(packet.model_dump(), f, indent=2, default=str)
    
    print(f"  ✓ Saved {len(packets)} evidence packets to {evidence_dir}")
    
    print(f"\n{'='*60}")
    print("✓ PHASE 4 COMPLETE")
    print("=" * 60)
    print("\nNext: Run Phase 5 for LLM-based explanation generation")


if __name__ == "__main__":
    main()
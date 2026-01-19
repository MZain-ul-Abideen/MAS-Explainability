"""
Phase 3 Test Script
Run this to build system understanding.
"""

import json
from pathlib import Path
from phase3_understanding.system_profiler import build_system_profile


def main():
    print("=" * 60)
    print("PHASE 3: SYSTEM UNDERSTANDING TEST")
    print("=" * 60)
    
    artifacts_dir = Path("artifacts")
    norms_file = artifacts_dir / "parsed_norms.json"
    logs_file = artifacts_dir / "parsed_logs.json"
    compliance_file = artifacts_dir / "compliance_results.json"
    
    # Build system profile
    print("\nBuilding comprehensive system profile...")
    profile = build_system_profile(norms_file, logs_file, compliance_file)
    
    print("\n" + "=" * 60)
    print("SYSTEM OVERVIEW")
    print("=" * 60)
    
    # Agents
    print(f"\n📊 AGENTS ({profile.total_agents} total)")
    print(f"  Roles identified: {profile.total_roles}")
    for role, agents in list(profile.roles.items())[:5]:
        print(f"    {role}: {len(agents)} agent(s) - {', '.join(agents[:3])}")
    
    # Norms
    print(f"\n📜 NORMS ({profile.total_norms} total)")
    print(f"  By type:")
    for norm_type, count in profile.norms_by_type.items():
        print(f"    {norm_type}: {count}")
    
    # Missions
    print(f"\n🎯 MISSIONS ({profile.total_missions} total)")
    for mission_name, mission in list(profile.missions.items())[:5]:
        print(f"  {mission_name}:")
        print(f"    Required roles: {', '.join(mission.required_roles)}")
        print(f"    Agents assigned: {len(mission.agents_assigned)}")
        fulfilled = sum(1 for s in mission.fulfillment_status.values() if s == 'fulfilled')
        print(f"    Fulfillment: {fulfilled}/{len(mission.fulfillment_status)}")
    
    # Execution
    print(f"\n⏱️  EXECUTION")
    print(f"  Total events: {profile.total_events}")
    print(f"  Temporal strategy: {profile.temporal_strategy}")
    print(f"  Timeline span: entry {profile.execution_timeline[0]['temporal_marker']} to {profile.execution_timeline[-1]['temporal_marker']}")
    
    # Compliance
    print(f"\n✅ COMPLIANCE SUMMARY")
    for status, count in profile.compliance_summary.items():
        print(f"  {status}: {count}")
    
    # Interactions
    print(f"\n🔗 INTERACTIONS ({len(profile.interactions)} detected)")
    for interaction in profile.interactions[:5]:
        print(f"  {interaction.source_agent} -> {interaction.target_agent or 'system'}")
        print(f"    Type: {interaction.interaction_type}, Frequency: {interaction.frequency}")
    
    # Agent spotlight
    print(f"\n🔍 AGENT SPOTLIGHT")
    for agent_id, agent in list(profile.agents.items())[:3]:
        print(f"\n  Agent: {agent_id}")
        print(f"    Role: {agent.inferred_role or 'unknown'} ({agent.role_confidence})")
        print(f"    Actions: {agent.total_actions} total, {agent.unique_actions} unique")
        print(f"    Top actions: {', '.join(list(agent.action_summary.keys())[:3])}")
        print(f"    Norms: {len(agent.applicable_norms)} applicable")
        if agent.compliance_status:
            fulfilled = sum(1 for s in agent.compliance_status.values() if s == 'fulfilled')
            print(f"    Compliance: {fulfilled}/{len(agent.compliance_status)} fulfilled")
    
    # Save profile
    output_file = artifacts_dir / "system_profile.json"
    with open(output_file, "w") as f:
        json.dump(profile.model_dump(), f, indent=2, default=str)
    
    print(f"\n💾 Saved to {output_file}")
    
    print("\n" + "=" * 60)
    print("✓ PHASE 3 COMPLETE")
    print("=" * 60)
    print("\nNext: Run Phase 4 to enable evidence retrieval")


if __name__ == "__main__":
    main()
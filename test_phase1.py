"""
Phase 1 Test Script
Run this to verify parsing works correctly.
"""

import json
from pathlib import Path
from phase1_parsing.parse_norms import parse_norms
from phase1_parsing.parse_logs import parse_logs


def main():
    print("=" * 60)
    print("PHASE 1: PARSING TEST")
    print("=" * 60)
    
    # Parse norms
    print("\n[1/2] Parsing norms...")
    norms_file = Path("data/sample_norms/skateboard_assembly.xml")
    parsed_norms = parse_norms(norms_file)
    
    print(f"  ✓ Parsed {parsed_norms.total_count} norms")
    print(f"  ✓ Norm types: {set(n.norm_type for n in parsed_norms.norms)}")
    
    # Save to artifacts
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    
    with open(artifacts_dir / "parsed_norms.json", "w") as f:
        json.dump(parsed_norms.model_dump(), f, indent=2, default=str)
    print(f"  ✓ Saved to artifacts/parsed_norms.json")
    
    # Parse logs
    print("\n[2/2] Parsing logs...")
    logs_file = Path("data/sample_logs/skateboard_run.log")
    parsed_logs = parse_logs(logs_file)
    
    print(f"  ✓ Parsed {parsed_logs.total_count} log entries")
    print(f"  ✓ Temporal strategy: {parsed_logs.temporal_strategy}")
    print(f"  ✓ Agents: {set(e.agent_id for e in parsed_logs.entries)}")
    print(f"  ✓ Actions: {set(e.action for e in parsed_logs.entries)}")
    
    # Save to artifacts
    with open(artifacts_dir / "parsed_logs.json", "w") as f:
        json.dump(parsed_logs.model_dump(), f, indent=2, default=str)
    print(f"  ✓ Saved to artifacts/parsed_logs.json")
    
    print("\n" + "=" * 60)
    print("✓ PHASE 1 COMPLETE")
    print("=" * 60)
    print("\nNext: Run Phase 2 to analyze compliance")


if __name__ == "__main__":
    main()
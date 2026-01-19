"""
Phase 2 Test Script
Run this to verify compliance analysis works correctly.
"""

import json
from pathlib import Path
from phase2_analysis.norm_matcher import NormMatcher
from phase2_analysis.compliance_checker import ComplianceChecker


def main():
    print("=" * 60)
    print("PHASE 2: COMPLIANCE ANALYSIS TEST")
    print("=" * 60)
    
    artifacts_dir = Path("artifacts")
    norms_file = artifacts_dir / "parsed_norms.json"
    logs_file = artifacts_dir / "parsed_logs.json"
    
    # Step 1: Build role mapping
    print("\n[1/3] Building agent-role mappings...")
    matcher = NormMatcher(norms_file, logs_file)
    role_mapping = matcher.build_role_mapping()
    
    print(f"  ✓ Mapped {len(role_mapping)} agents to roles")
    
    # Show sample mappings
    print("\n  Sample role mappings:")
    for agent_id, mapping in list(role_mapping.items())[:5]:
        role = mapping.get('inferred_role', 'unknown')
        confidence = mapping.get('confidence', 'unknown')
        print(f"    {agent_id} -> {role} ({confidence})")
    
    # Step 2: Build applicability matrix
    print("\n[2/3] Building norm applicability matrix...")
    applicability_matrix = matcher.build_applicability_matrix()
    
    applicable_count = sum(1 for a in applicability_matrix if a['applies'])
    print(f"  ✓ {applicable_count} norm-agent pairs where norm applies")
    print(f"  ✓ Total matrix size: {len(applicability_matrix)} entries")
    
    # Step 3: Check compliance
    print("\n[3/3] Checking compliance...")
    checker = ComplianceChecker(
        norms_file,
        logs_file,
        role_mapping,
        applicability_matrix
    )
    
    compliance_results = checker.check_all_compliance()
    
    # Count by status
    from collections import Counter
    status_counts = Counter(r['status'] for r in compliance_results)
    
    print(f"  ✓ Analyzed {len(compliance_results)} compliance cases")
    print(f"\n  Compliance Status Breakdown:")
    for status, count in status_counts.items():
        print(f"    {status}: {count}")
    
    # Save results
    output = {
        'role_mapping': role_mapping,
        'applicability_matrix': applicability_matrix,
        'compliance_results': compliance_results,
        'summary': {
            'total_agents': len(role_mapping),
            'total_norms': len(matcher.norms),
            'applicable_pairs': applicable_count,
            'status_counts': dict(status_counts)
        }
    }
    
    output_file = artifacts_dir / "compliance_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n  ✓ Saved to {output_file}")
    
    # Show sample results
    print("\n  Sample compliance results:")
    fulfilled = [r for r in compliance_results if r['status'] == 'fulfilled'][:3]
    violated = [r for r in compliance_results if r['status'] == 'violated'][:3]
    
    if fulfilled:
        print("\n  Fulfilled:")
        for r in fulfilled:
            print(f"    {r['agent_id']} fulfilled {r['norm_id']}: {r['reasoning']}")
    
    if violated:
        print("\n  Violated:")
        for r in violated:
            print(f"    {r['agent_id']} violated {r['norm_id']}: {r['reasoning']}")
    
    print("\n" + "=" * 60)
    print("✓ PHASE 2 COMPLETE")
    print("=" * 60)
    print("\nNext: Run Phase 3 to build system understanding")


if __name__ == "__main__":
    main()
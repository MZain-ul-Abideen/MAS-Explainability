"""
MAS Explainability System - Main Orchestrator

Complete pipeline from raw logs/norms to natural language explanations.
"""

import argparse
import json
from pathlib import Path
from phase1_parsing.parse_norms import parse_norms
from phase1_parsing.parse_logs import parse_logs
from phase2_analysis.norm_matcher import NormMatcher
from phase2_analysis.compliance_checker import ComplianceChecker
from phase3_understanding.system_profiler import build_system_profile
from phase4_retrieval.evidence_retriever import retrieve_evidence
from phase5_explanation.explainer import generate_explanation


def run_full_pipeline(
    norms_file: Path,
    logs_file: Path,
    artifacts_dir: Path,
    api_token: str = None
):
    """
    Run the complete explainability pipeline.
    
    Args:
        norms_file: Path to norm specification file
        logs_file: Path to execution log file
        artifacts_dir: Directory to store intermediate artifacts
        api_token: HuggingFace API token (optional)
    """
    artifacts_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("MAS EXPLAINABILITY SYSTEM - FULL PIPELINE")
    print("=" * 80)
    
    # =========================================================================
    # PHASE 1: PARSING
    # =========================================================================
    print("\n[PHASE 1] Parsing norms and logs...")
    
    parsed_norms = parse_norms(norms_file)
    print(f"  ✓ Parsed {parsed_norms.total_count} norms")
    
    parsed_logs = parse_logs(logs_file)
    print(f"  ✓ Parsed {parsed_logs.total_count} log entries")
    print(f"  ✓ Temporal strategy: {parsed_logs.temporal_strategy}")
    
    # Save artifacts
    with open(artifacts_dir / "parsed_norms.json", "w") as f:
        json.dump(parsed_norms.model_dump(), f, indent=2, default=str)
    
    with open(artifacts_dir / "parsed_logs.json", "w") as f:
        json.dump(parsed_logs.model_dump(), f, indent=2, default=str)
    
    # =========================================================================
    # PHASE 2: COMPLIANCE ANALYSIS
    # =========================================================================
    print("\n[PHASE 2] Analyzing compliance...")
    
    matcher = NormMatcher(
        artifacts_dir / "parsed_norms.json",
        artifacts_dir / "parsed_logs.json"
    )
    
    role_mapping = matcher.build_role_mapping()
    print(f"  ✓ Mapped {len(role_mapping)} agents to roles")
    
    applicability_matrix = matcher.build_applicability_matrix()
    
    checker = ComplianceChecker(
        artifacts_dir / "parsed_norms.json",
        artifacts_dir / "parsed_logs.json",
        role_mapping,
        applicability_matrix
    )
    
    compliance_results = checker.check_all_compliance()
    
    from collections import Counter
    status_counts = Counter(r['status'] for r in compliance_results)
    print(f"  ✓ Compliance: {dict(status_counts)}")
    
    # Save artifacts
    with open(artifacts_dir / "compliance_results.json", "w") as f:
        json.dump({
            'role_mapping': role_mapping,
            'applicability_matrix': applicability_matrix,
            'compliance_results': compliance_results
        }, f, indent=2, default=str)
    
    # =========================================================================
    # PHASE 3: SYSTEM UNDERSTANDING
    # =========================================================================
    print("\n[PHASE 3] Building system understanding...")
    
    profile = build_system_profile(
        artifacts_dir / "parsed_norms.json",
        artifacts_dir / "parsed_logs.json",
        artifacts_dir / "compliance_results.json"
    )
    
    print(f"  ✓ Profiled {profile.total_agents} agents")
    print(f"  ✓ Identified {profile.total_roles} roles")
    print(f"  ✓ Analyzed {profile.total_missions} missions")
    
    # Save artifacts
    with open(artifacts_dir / "system_profile.json", "w") as f:
        json.dump(profile.model_dump(), f, indent=2, default=str)
    
    # =========================================================================
    # PHASE 4 & 5: READY FOR QUERIES
    # =========================================================================
    print("\n[PHASE 4 & 5] System ready for queries!")
    print("\nThe system can now answer questions about:")
    print("  - Agent behavior and actions")
    print("  - Norm compliance and violations")
    print("  - Mission fulfillment")
    print("  - System timeline and interactions")
    print("  - Overall system overview")
    
    return {
        'artifacts_dir': artifacts_dir,
        'parsed_norms': parsed_norms,
        'parsed_logs': parsed_logs,
        'compliance_results': compliance_results,
        'system_profile': profile
    }


def answer_query(query: str, artifacts_dir: Path, api_token: str = None) -> dict:
    """
    Answer a natural language query about the MAS.
    
    Args:
        query: User's question
        artifacts_dir: Directory containing artifacts
        api_token: HuggingFace API token
        
    Returns:
        Dictionary with answer and metadata
    """
    print(f"\nQuery: {query}")
    print("─" * 80)
    
    # Retrieve evidence
    evidence_packet = retrieve_evidence(artifacts_dir, query)
    print(f"Retrieved: {evidence_packet.total_items_retrieved} relevant items")
    
    # Generate explanation
    explanation = generate_explanation(
        query,
        evidence_packet.model_dump(),
        api_token=api_token
    )
    
    print("\nAnswer:")
    print(explanation.answer)
    print("─" * 80)
    
    if explanation.token_usage and explanation.token_usage.get('total_tokens'):
        print(f"Tokens used: {explanation.token_usage['total_tokens']}")
    
    return {
        'query': query,
        'answer': explanation.answer,
        'evidence_used': explanation.evidence_used,
        'token_usage': explanation.token_usage
    }


def main():
    parser = argparse.ArgumentParser(
        description='MAS Explainability System'
    )
    
    parser.add_argument(
        '--norms',
        type=Path,
        default=Path('data/sample_norms/skateboard_assembly.xml'),
        help='Path to norm specification file'
    )
    
    parser.add_argument(
        '--logs',
        type=Path,
        default=Path('data/sample_logs/skateboard_run.log'),
        help='Path to execution log file'
    )
    
    parser.add_argument(
        '--artifacts',
        type=Path,
        default=Path('artifacts'),
        help='Directory to store artifacts'
    )
    
    parser.add_argument(
        '--query',
        type=str,
        help='Query to answer (runs full pipeline first if needed)'
    )
    
    parser.add_argument(
        '--api-token',
        type=str,
        help='HuggingFace API token (or set HF_API_TOKEN env var)'
    )
    
    args = parser.parse_args()
    
    # Run full pipeline
    result = run_full_pipeline(
        args.norms,
        args.logs,
        args.artifacts,
        args.api_token
    )
    
    # Answer query if provided
    if args.query:
        print("\n" + "=" * 80)
        answer_query(args.query, args.artifacts, args.api_token)
    else:
        print("\n💡 TIP: Run with --query 'Your question here' to get explanations")
        print("Example: python main.py --query 'What did the assembly agent do?'")


if __name__ == "__main__":
    main()
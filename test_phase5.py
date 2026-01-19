"""
Phase 5 Test Script (HuggingFace Version)
Test LLM-based explanation generation.
"""

import json
from pathlib import Path
from phase4_retrieval.evidence_retriever import retrieve_evidence
from phase5_explanation.explainer import generate_explanation


def test_explanation(artifacts_dir: Path, query: str, api_token: str = None):
    """Test explanation generation for a query."""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    # Step 1: Retrieve evidence
    print("\n[1/2] Retrieving evidence...")
    evidence_packet = retrieve_evidence(artifacts_dir, query)
    
    print(f"  Retrieved: {evidence_packet.total_items_retrieved} items")
    print(f"  Query type: {evidence_packet.query_type}")
    print(f"  Strategy: {evidence_packet.retrieval_strategy}")
    
    # Step 2: Generate explanation
    print("\n[2/2] Generating explanation with HuggingFace LLM...")
    explanation = generate_explanation(
        query,
        evidence_packet.model_dump(),
        api_token=api_token
    )
    
    print(f"\n{'─'*80}")
    print("EXPLANATION:")
    print(f"{'─'*80}")
    print(explanation.answer)
    print(f"{'─'*80}")
    
    if explanation.token_usage:
        print(f"\nModel: {explanation.token_usage.get('model', 'N/A')}")
        if explanation.token_usage.get('total_tokens'):
            print(f"Token Usage: {explanation.token_usage['total_tokens']} tokens")
            print(f"  Prompt: {explanation.token_usage.get('prompt_tokens', 'N/A')}")
            print(f"  Completion: {explanation.token_usage.get('completion_tokens', 'N/A')}")
    
    print(f"\nEvidence Used:")
    for key, count in explanation.evidence_used.items():
        if count > 0:
            print(f"  {key}: {count}")
    
    return explanation


def main():
    print("=" * 80)
    print("PHASE 5: LLM-BASED EXPLANATION GENERATION TEST (HuggingFace)")
    print("=" * 80)
    
    artifacts_dir = Path("artifacts")
    
    # Check for API token
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_token = os.getenv("HF_API_TOKEN")
    
    if not api_token:
        print("\n⚠️  WARNING: HF_API_TOKEN not set!")
        print("Please set your HuggingFace API token:")
        print("  1. Create a .env file in the project root")
        print("  2. Add: HF_API_TOKEN=your-token-here")
        print("  Or export HF_API_TOKEN='your-token-here'")
        print("\nGet your token at: https://huggingface.co/settings/tokens")
        return
    
    print(f"✓ HuggingFace API token found")
    print(f"✓ Using model: meta-llama/Llama-3.3-70B-Instruct")
    
    # Test queries (diverse set)
    test_queries = [
        "What did the assembly agent do?",
        "Which norms were violated and why?",
        "Did all suppliers fulfill their obligations?",
        "Give me an overview of the system",
        "What is the manage_assembly mission about?",
    ]
    
    explanations = []
    
    for query in test_queries:
        try:
            explanation = test_explanation(artifacts_dir, query, api_token)
            explanations.append(explanation)
        except Exception as e:
            print(f"\n❌ Error processing query: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save all explanations
    print(f"\n{'='*80}")
    print("Saving explanations...")
    
    explanations_dir = artifacts_dir / "explanations"
    explanations_dir.mkdir(exist_ok=True)
    
    for i, explanation in enumerate(explanations):
        output_file = explanations_dir / f"explanation_{i}.json"
        with open(output_file, "w") as f:
            json.dump(explanation.model_dump(), f, indent=2, default=str)
    
    print(f"  ✓ Saved {len(explanations)} explanations to {explanations_dir}")
    
    print(f"\n{'='*80}")
    print("✓ PHASE 5 COMPLETE")
    print("=" * 80)
    print("\n🎉 ALL PHASES COMPLETE!")
    print("\nYour MAS Explainability System is ready!")
    print("\nNext steps:")
    print("  1. Review generated explanations in artifacts/explanations/")
    print("  2. Try your own queries with the system")
    print("  3. Document findings in your research paper")


if __name__ == "__main__":
    main()
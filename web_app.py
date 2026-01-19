"""
Web Interface for MAS Explainability System
Flask-based web application for querying the system.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import json
import os
from dotenv import load_dotenv
from phase4_retrieval.evidence_retriever import retrieve_evidence
from phase5_explanation.explainer import generate_explanation

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['ARTIFACTS_DIR'] = Path('artifacts')
app.config['HF_API_TOKEN'] = os.getenv('HF_API_TOKEN')

# Check if artifacts exist
ARTIFACTS_EXIST = (
    (app.config['ARTIFACTS_DIR'] / 'parsed_norms.json').exists() and
    (app.config['ARTIFACTS_DIR'] / 'parsed_logs.json').exists() and
    (app.config['ARTIFACTS_DIR'] / 'compliance_results.json').exists() and
    (app.config['ARTIFACTS_DIR'] / 'system_profile.json').exists()
)


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html', artifacts_exist=ARTIFACTS_EXIST)


@app.route('/api/query', methods=['POST'])
def query():
    """Handle user queries."""
    if not ARTIFACTS_EXIST:
        return jsonify({
            'error': 'System not initialized. Please run the pipeline first.',
            'details': 'Run: python main.py'
        }), 400
    
    data = request.get_json()
    user_query = data.get('query', '').strip()
    
    if not user_query:
        return jsonify({'error': 'Query cannot be empty'}), 400
    
    try:
        # Retrieve evidence
        evidence_packet = retrieve_evidence(app.config['ARTIFACTS_DIR'], user_query)
        
        # Generate explanation
        explanation = generate_explanation(
            user_query,
            evidence_packet.model_dump(),
            api_token=app.config['HF_API_TOKEN']
        )
        
        response = {
            'query': user_query,
            'answer': explanation.answer,
            'evidence_used': explanation.evidence_used,
            'token_usage': explanation.token_usage,
            'query_type': evidence_packet.query_type,
            'retrieval_strategy': evidence_packet.retrieval_strategy,
            'total_items_retrieved': evidence_packet.total_items_retrieved
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to process query',
            'details': str(e)
        }), 500


@app.route('/api/system-info')
def system_info():
    """Get system overview information."""
    if not ARTIFACTS_EXIST:
        return jsonify({'error': 'System not initialized'}), 400
    
    try:
        # Load system profile
        with open(app.config['ARTIFACTS_DIR'] / 'system_profile.json', 'r') as f:
            profile = json.load(f)
        
        # Load norms
        with open(app.config['ARTIFACTS_DIR'] / 'parsed_norms.json', 'r') as f:
            norms = json.load(f)
        
        info = {
            'total_agents': profile['total_agents'],
            'total_norms': profile['total_norms'],
            'total_missions': profile['total_missions'],
            'total_events': profile['total_events'],
            'temporal_strategy': profile['temporal_strategy'],
            'roles': profile['roles'],
            'compliance_summary': profile['compliance_summary'],
            'norms_by_type': profile['norms_by_type'],
            'sample_agents': list(profile['agents'].keys())[:10],
            'sample_norms': [
                {
                    'id': n['norm_id'],
                    'type': n['norm_type'],
                    'role': n.get('role'),
                    'mission': n.get('mission')
                } for n in norms['norms'][:5]
            ]
        }
        
        return jsonify(info)
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to load system information',
            'details': str(e)
        }), 500


@app.route('/api/examples')
def examples():
    """Get example queries."""
    example_queries = [
        {
            'category': 'Agent Behavior',
            'queries': [
                'What did the assembly agent do?',
                'Tell me about the customer agent',
                'Show me all actions by supplier1'
            ]
        },
        {
            'category': 'Norms & Compliance',
            'queries': [
                'Which norms were violated?',
                'Did the assembly agent fulfill its obligations?',
                'What norms apply to suppliers?'
            ]
        },
        {
            'category': 'Missions',
            'queries': [
                'What is the manage_assembly mission?',
                'Who is responsible for deliver_parts?',
                'Which missions were completed?'
            ]
        },
        {
            'category': 'Timeline',
            'queries': [
                'What happened first?',
                'Show me the timeline for the assembly agent',
                'What was the sequence of events?'
            ]
        },
        {
            'category': 'Overview',
            'queries': [
                'Give me an overview of the system',
                'How many agents are there?',
                'What roles exist in the system?'
            ]
        }
    ]
    
    return jsonify(example_queries)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
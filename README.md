# MAS Explainability

A comprehensive system for parsing, analyzing, and explaining compliance in multi-agent systems (MAS) through a structured 5-phase pipeline.

## Overview

This project implements an end-to-end framework for understanding and explaining compliance behavior in multi-agent systems by:
1. **Parsing** system logs and normative rules
2. **Analyzing** compliance with detected norms
3. **Profiling** system characteristics and behaviors
4. **Retrieving** relevant evidence from system logs
5. **Generating** human-understandable explanations

## Features

- 📋 Log and norm XML parsing with schema validation
- ✅ Compliance checking against system norms
- 📊 System profiling and behavior analysis
- 🔍 Evidence retrieval for compliance violations
- 📝 Automated explanation generation
- 🌐 Web-based interface for result visualization

## Project Structure

```
mas-explainability/
├── phase1_parsing/          # Data parsing module
│   ├── parse_logs.py        # Log parsing logic
│   ├── parse_norms.py       # Norm parsing logic
│   └── schemas.py           # Data validation schemas
├── phase2_analysis/         # Compliance analysis module
│   ├── compliance_checker.py # Compliance verification
│   └── norm_matcher.py      # Norm matching logic
├── phase3_understanding/    # System understanding module
│   └── system_profiler.py   # System profile generation
├── phase4_retrieval/        # Evidence retrieval module
│   └── evidence_retriever.py # Evidence gathering
├── phase5_explanation/      # Explanation generation module
│   └── explainer.py         # Explanation logic
├── templates/               # Web interface templates
│   └── index.html          # Main dashboard
├── data/                    # Sample data
├── artifacts/               # Generated outputs
└── main.py                  # Main execution script
```

## Requirements

- Python 3.8+
- Flask (for web interface)
- Pydantic (for data validation)
- XML parsing libraries

Install dependencies:

```bash
pip install -r requirements.txt
```

## Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd mas-explainability
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

### Run the complete pipeline:

```bash
python main.py
```

### Run individual phases:

```bash
python test_phase1.py  # Parsing
python test_phase2.py  # Analysis
python test_phase3.py  # Understanding
python test_phase4.py  # Retrieval
python test_phase5.py  # Explanation
```

### Launch the web interface:

```bash
python web_app.py
```

Then navigate to `http://localhost:5000` in your browser.

## Pipeline Phases

### Phase 1: Parsing
Parses raw system logs and normative rules (XML format) into structured data for further analysis.

**Output:** `artifacts/parsed_logs.json`, `artifacts/parsed_norms.json`

### Phase 2: Analysis
Checks compliance of the system against detected norms and identifies violations.

**Output:** `artifacts/compliance_results.json`

### Phase 3: Understanding
Profiles the system to understand its characteristics and behavior patterns.

**Output:** `artifacts/system_profile.json`

### Phase 4: Retrieval
Retrieves relevant evidence from system logs to support explanations.

**Output:** `artifacts/evidence_cache/`

### Phase 5: Explanation
Generates human-readable explanations for compliance violations and system behavior.

**Output:** `artifacts/explanations/`

## Example Data

Sample data files are located in the `data/` directory:
- `data/sample_logs/skateboard_run.log` - Sample system log
- `data/sample_norms/skateboard_assembly.xml` - Sample normative rules

## Configuration

Modify input/output paths and parameters in `main.py` as needed for your specific use case.

## Output

All generated artifacts are stored in the `artifacts/` directory:
- `compliance_results.json` - Compliance check results
- `parsed_logs.json` - Parsed system logs
- `parsed_norms.json` - Parsed normative rules
- `system_profile.json` - System profiling data
- `evidence_cache/` - Retrieved evidence files
- `explanations/` - Generated explanations

## Contributing

For contributions, please:
1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly using the test_phaseX.py scripts
4. Submit a pull request

## Contact

muhammadzainulabideen02@gmail.com

## Acknowledgments

This project is part of research in explainability for multi-agent systems.

# AI Fraud Investigation Agent

An AI-powered multi-agent system for suspicious transaction detection and investigation, designed for financial compliance teams.

## Problem

Financial institutions spend thousands of analyst-hours manually reviewing flagged transactions. Current rule-based systems generate high false-positive rates (>95%), and analysts lack tools to quickly contextualize and investigate alerts.

## Solution

A multi-agent investigation system that:
1. **Detects** anomalous transaction patterns using known fraud typologies
2. **Enriches** context by linking entities, networks, and external signals
3. **Assesses** risk with explainable scoring (regulatory requirement)
4. **Generates** SAR-ready investigation reports with evidence chains

## Architecture

```
User Input: Transaction record(s) or alert
                    ↓
┌─────────────────────────────────────────────┐
│           Orchestrator Agent                │
│   (Plan → Execute → Verify loop)            │
└──────┬──────┬──────┬──────┬────────────────┘
       ↓      ↓      ↓      ↓
   ┌───────┐┌───────┐┌───────┐┌───────────┐
   │Pattern││Context││ Risk  ││  Report    │
   │Detect ││Enrich ││Assess ││ Generator  │
   │Agent  ││Agent  ││Agent  ││  Agent     │
   └───────┘└───────┘└───────┘└───────────┘
       ↓      ↓      ↓           ↓
   Anomaly  Entity  Risk      SAR Report
   Flags    Graph   Score     (with citations)
                    ↓
            ┌──────────────┐
            │ Human Review │ ← Analyst feedback loop
            │   Interface  │ → Improves future detection
            └──────────────┘
```

## Key Design Decisions

### Why Multi-Agent (not single LLM call)?
- **Separation of concerns**: Each agent has a clear responsibility and can be evaluated independently
- **Explainability**: Regulators require clear reasoning chains — each agent produces auditable output
- **Adversarial robustness**: Risk Assessor challenges Pattern Detector's findings (reduces false positives)

### Why Explainable AI matters here
- FinCEN/PBOC regulations require institutions to explain why a transaction was flagged
- Black-box ML models are insufficient for compliance — every flag needs a human-readable rationale
- Our system generates structured evidence chains, not just scores

### Human-in-the-Loop Design
- AI handles initial screening (high volume, low judgment)
- Analysts review AI-generated reports (low volume, high judgment)
- Analyst feedback flows back to improve detection patterns

## Tech Stack

- **LLM**: Claude API (via Anthropic SDK)
- **Agent Framework**: Custom orchestrator with Plan-Execute-Verify pattern
- **Data**: PaySim synthetic dataset + custom fraud scenario generator
- **Frontend**: Streamlit (MVP) → React (production)
- **Language**: Python 3.11+

## Project Structure

```
ai-fraud-investigator/
├── src/
│   ├── agents/              # Multi-agent system
│   │   ├── orchestrator.py  # Main coordinator (Plan-Execute-Verify)
│   │   ├── pattern_detector.py    # Stage 1: Anomaly detection
│   │   ├── context_enricher.py    # Stage 2: Entity & network analysis
│   │   ├── risk_assessor.py       # Stage 3: Explainable risk scoring
│   │   └── report_generator.py    # Stage 4: SAR report generation
│   ├── models/              # Data models & schemas
│   │   ├── transaction.py   # Transaction data model
│   │   ├── investigation.py # Investigation state & results
│   │   └── sar_report.py    # SAR report schema
│   ├── utils/               # Shared utilities
│   │   ├── llm_client.py    # Claude API wrapper
│   │   ├── data_loader.py   # Dataset loading & preprocessing
│   │   └── visualization.py # Network graph & chart generation
│   └── data/                # Data directory
│       └── fraud_patterns.json  # Known fraud typology library
├── tests/                   # Test suite
├── frontend/                # Streamlit UI
│   └── app.py
├── config/                  # Configuration
│   └── settings.yaml
├── scripts/                 # Utility scripts
│   └── generate_synthetic_data.py
├── docs/                    # Documentation
│   └── fraud_typologies.md
├── requirements.txt
└── README.md
```

## Getting Started

```bash
# Clone and setup
cd projects/ai-fraud-investigator
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run with sample data
python -m src.agents.orchestrator --input data/sample_transactions.csv

# Launch UI
streamlit run frontend/app.py
```

## Development Roadmap

- [x] Project skeleton & architecture design
- [ ] **Week 1**: MVP — Single-agent pattern detection on PaySim data
- [ ] **Week 2**: Multi-agent pipeline + explainable risk scoring
- [ ] **Week 3**: Web UI + SAR report generation
- [ ] **Week 4**: Adversarial scenarios + demo polish

## License

MIT

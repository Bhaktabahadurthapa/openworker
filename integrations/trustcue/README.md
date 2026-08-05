# TrustCue Integration

TrustCue is Bhakta Thapa's applied AI customer-retention prototype for DBA research and startup validation.

This integration combines:

- OpenWorker as the local-first desktop agent shell and approval interface.
- ChurnCue as the deterministic customer-retention intelligence engine.
- TrustCue as the product workflow, research framing, and business use case.

## Product boundary

TrustCue is not a rebrand of OpenWorker. OpenWorker remains an upstream open-source dependency. ChurnCue provides the original domain-specific risk-scoring and rescue-report workflow.

## End-to-end flow

1. Start ChurnCue on port 8000.
2. Start OpenWorker on port 8765.
3. Register the ChurnCue Streamable HTTP MCP endpoint: `http://localhost:8000/mcp`.
4. Load the TrustCue operating prompt from `SYSTEM_PROMPT.md`.
5. Ask for a weekly customer-retention brief.
6. Review deterministic ChurnCue scores and evidence.
7. Approve, edit, reject, or postpone any proposed external action.

## Local prerequisites

- Python 3.12 for ChurnCue
- Python 3.10+ for OpenWorker
- Node.js 20+
- Docker Desktop, optional but recommended

## Start ChurnCue

```bash
git clone https://github.com/Bhaktabahadurthapa/ChurnCue.git
cd ChurnCue
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python scripts/generate_demo_data.py
churncue
```

Verify:

```bash
curl http://localhost:8000/health
```

## Start OpenWorker

```bash
git clone https://github.com/Bhaktabahadurthapa/openworker.git
cd openworker
bash packaging/setup_dev_env.sh
.venv/bin/openworker-server --cwd ~/trustcue-workspace --port 8765
```

In a second terminal:

```bash
cd surfaces/gui
npm install
npm run dev
```

## MVP definition

The first live vertical slice is complete when a manager can:

1. Ask which customers are at risk.
2. Receive a prioritized rescue report from ChurnCue.
3. Open the evidence for one customer.
4. Review a recommended action.
5. Approve, edit, reject, or postpone it.
6. Produce a draft Slack or email message without sending automatically.
7. Record the final business outcome.

## Commercial direction

Do not sell the OpenWorker fork as an original standalone product. The commercial product should use a separate TrustCue brand and may later add its own web dashboard, tenancy, billing, reporting, and outcome tracking.

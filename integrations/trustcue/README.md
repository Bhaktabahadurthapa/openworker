# TrustCue Integration

TrustCue is Bhakta Thapa's applied AI customer-retention prototype for DBA research and startup validation.

This integration combines:

- **OpenWorker** as the local-first desktop agent shell, MCP client, and approval interface.
- **ChurnCue** as the deterministic customer-retention intelligence engine.
- **TrustCue** as the governed product workflow, research framing, and business use case.

## Product boundary

TrustCue is not a rebrand of OpenWorker. OpenWorker remains an attributed upstream open-source dependency. ChurnCue supplies the domain-specific risk-scoring, evidence, revenue prioritization, and rescue-report workflow.

## End-to-end flow

```text
Manager request
      ↓
TrustCue persona in OpenWorker
      ↓
ChurnCue MCP health and dataset validation
      ↓
Deterministic training, scoring, and weekly comparison
      ↓
Evidence-backed rescue report
      ↓
Unsent internal action draft
      ↓
Approval-gated local artifact write
      ↓
Manager approves, redirects, or rejects the exact content and path
```

Risk calculations come from ChurnCue, not the language model. The local demonstration never sends an external message. It uses OpenWorker's approval system to save the accepted draft under `approved-actions/`.

## Local prerequisites

- macOS or Linux
- Python 3.12 for ChurnCue
- Python 3.10+ for OpenWorker
- Node.js 20+ for the browser UI
- `curl`

Place the repositories next to each other by default:

```text
projects/
├── ChurnCue/
└── openworker/
```

Set `CHURNCUE_DIR` when using a different layout.

## One-command local runtime

From the OpenWorker repository:

```bash
bash integrations/trustcue/start_local.sh --with-ui
```

The launcher:

1. Verifies both repositories.
2. Creates missing Python environments and installs dependencies.
3. Generates the ChurnCue demo dataset when needed.
4. Configures `~/trustcue-workspace/.coworker/mcp.json`.
5. Enables TrustCue as the default OpenWorker persona.
6. Creates `~/trustcue-workspace/approved-actions/`.
7. Starts ChurnCue on port `8000`.
8. Starts OpenWorker on port `8765`.
9. Optionally starts the browser UI.

Stop all local services:

```bash
bash integrations/trustcue/stop_local.sh
```

Logs and PID files are stored under:

```text
~/trustcue-workspace/.trustcue/
```

## Configure without starting services

```bash
python integrations/trustcue/bootstrap.py \
  --workspace ~/trustcue-workspace \
  --churncue-url http://localhost:8000/mcp
```

The generated workspace MCP configuration is equivalent to `mcp.json.example`. It exposes only these ChurnCue tools:

- `health_check`
- `load_demo_dataset`
- `profile_dataset`
- `train_models`
- `score_customers`
- `compare_weekly_risk`
- `explain_risk`
- `generate_rescue_report`

The ChurnCue tools do not send external messages, so they can run without per-call approval. Slack, email, CRM, shell, and other external changes remain governed by OpenWorker. The demonstration uses the approval-gated `write_file` tool only to save the accepted local draft.

## Manual startup

### ChurnCue

```bash
git clone https://github.com/Bhaktabahadurthapa/ChurnCue.git
cd ChurnCue
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
.venv/bin/python scripts/generate_demo_data.py
.venv/bin/churncue
```

Verify:

```bash
curl http://localhost:8000/health
```

### OpenWorker

```bash
git clone https://github.com/Bhaktabahadurthapa/openworker.git
cd openworker
bash packaging/setup_dev_env.sh
python integrations/trustcue/bootstrap.py --workspace ~/trustcue-workspace
.venv/bin/openworker-server --cwd ~/trustcue-workspace --port 8765
```

In another terminal:

```bash
cd surfaces/gui
npm install
npm run dev
```

## Run the first governed demonstration

TrustCue is enabled as the default persona by the bootstrap script. Open:

```text
~/trustcue-workspace/TRUSTCUE_DEMO_PROMPT.md
```

Paste the request into OpenWorker. The expected workflow is:

```text
health_check
  → load_demo_dataset
  → profile_dataset
  → train_models
  → score_customers
  → compare_weekly_risk
  → explain_risk
  → generate_rescue_report
  → prepare an unsent internal Slack draft
  → propose approved-actions/<draft-name>.md
  → OpenWorker displays a write approval card
  → manager approves, redirects, or rejects
  → approved draft is saved locally without being sent
```

The final output must include:

- Executive summary.
- Monthly and annual revenue exposure.
- Top five accounts by revenue-weighted risk.
- ChurnCue evidence for every highlighted account.
- Proposed rescue action.
- Data-quality and model limitations.
- A clearly labeled draft that has not been sent.
- The saved artifact path after approval.

## Test the integration

```bash
.venv/bin/pytest tests/test_trustcue_integration.py
```

Run the full backend suite before release:

```bash
.venv/bin/pytest
```

## MVP definition

The first live vertical slice is complete when a manager can:

1. Ask which customers are at risk.
2. Receive a prioritized rescue report from ChurnCue.
3. Open the evidence for one customer.
4. Review a recommended action.
5. Approve, redirect, or reject the exact draft artifact.
6. Save an approved Slack or email draft without sending it automatically.
7. Record the final business outcome.

The current local integration completes steps 1 through 6 with synthetic data. Durable outcome storage and a standalone TrustCue web dashboard remain later product milestones.

## Commercial direction

Do not sell the OpenWorker fork as an original standalone product. The commercial product should live under a separate TrustCue brand and repository, while preserving OpenWorker's MIT notices. A later TrustCue SaaS can add its own web dashboard, tenant isolation, billing, reporting, integrations, and outcome tracking.

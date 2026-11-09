# Cozy — Autonomous Multi-Agent Workspace

Cozy is a free, GitHub-native workspace for dispatching tasks to a small agent team, running optional external connectors, and recording durable state and Markdown reports in the repository.

## What is included

- `index.html`: responsive GitHub Pages dashboard with task dispatch, connector toggles, pipeline modes, and live state feed.
- `orchestrator.py`: dependency-free Python orchestration loop with Architect, Executor, and Auditor stages.
- `connectors/app_connectors.py`: standard-library connectors for WhatsApp Cloud API, Google Apps Script webhooks, Discord webhooks, and repository file operations.
- `.github/workflows/agent_team.yml`: handles `repository_dispatch`, runs the orchestrator, and commits state/reports back to the default branch.
- `workspace_state.json`: durable task history consumed by the dashboard.
- `logs/`: human-readable execution reports.

## Quick start

1. Create the repository with this project and enable **Settings → Pages → GitHub Actions** as the source. The included `pages.yml` workflow publishes `index.html` automatically.
2. In **Settings → Secrets and variables → Actions**, add only the integrations you use:
   - `GEMINI_API_KEY` (recommended; optional, for Gemini task planning and summaries)
   - `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TO_NUMBER`
   - `GOOGLE_SHEETS_WEBHOOK_URL`
   - `DISCORD_WEBHOOK_URL`
3. Open the dashboard at `https://<owner>.github.io/Cozy/`.
4. Enter a fine-grained GitHub token in the dashboard. It is stored only in that browser's `localStorage`; use a token scoped to this repository with **Actions: Read and write** and **Contents: Read and write** permissions. The token is sent to GitHub only when you click **Dispatch task**.
5. Enter a task, choose a pipeline, select connectors, and dispatch it. GitHub Actions will process it and commit a report/state update.

## Google Apps Script webhook

Deploy a Google Apps Script as a web app with access set to the audience that should be allowed to call it. A minimal receiver is:

```js
function doPost(e) {
  const body = JSON.parse(e.postData.contents || '{}');
  const sheet = SpreadsheetApp.openById('YOUR_SHEET_ID').getSheetByName('Tasks');
  sheet.appendRow([new Date(), body.task_id || '', body.prompt || '', body.status || '', JSON.stringify(body)]);
  return ContentService.createTextOutput(JSON.stringify({ok: true})).setMimeType(ContentService.MimeType.JSON);
}
```

Use the deployed `/exec` URL as `GOOGLE_SHEETS_WEBHOOK_URL`.

## Local smoke test

```bash
python3 orchestrator.py --prompt "Create a project summary" --mode code_only
```

The orchestrator uses no third-party Python packages. External APIs are optional and fail safely with a recorded error so a missing connector does not lose the task report.

## Security notes

Never commit API keys, personal access tokens, or webhook URLs. Rotate a dashboard token if it is exposed. Repository state is intentionally committed by the Actions runner so the static dashboard can read it; do not put secrets in `workspace_state.json` or generated reports.

# Frontend

React and TypeScript client for CSV upload, dataset preview, the LangGraph
analysis workflow, charts, clarification, and follow-up conversation.

## Development

From the repository root:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5173 --strictPort
```

Start the backend separately with its model credentials:

```bash
uv run --project backend --env-file .env python -m backend.app.api.planner_server
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to
`http://127.0.0.1:8000`. Use Node.js 22.12 or newer. See the root
[running guide](../RUNNING.md) for credentials, a synthetic sales demo, and
troubleshooting.

The client validates a CSV up to 10 MB, previews its first four rows, and uploads
it to backend storage. It starts one workflow and polls persisted progress.
The backend owns planning, execution, review, retries, and clarification limits.
Final charts can be enlarged; suggested questions or the composer continue a
completed conversation.

The current conversation lives in browser memory and is cleared on page reload.
The **Recent** list is a placeholder. Backend checkpoint persistence does not
yet provide browser session restoration. Keep the tab open during a demo.

## Checks

```bash
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

`npm run build` creates `frontend/dist`. A deployed static build needs `/api`
routed to a persistent backend; the Vite development proxy does not run in the
static deployment. Never put model API keys in frontend environment variables.

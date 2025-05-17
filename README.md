# Codegen Deep Research

A code research tool that enables users to understand codebases through agentic AI analysis. The project combines a Modal-based FastAPI backend with a Next.js frontend to provide intelligent code exploration capabilities.

Users submit a GitHub repository and research query through the frontend. The Modal API processes the request using an AI agent equipped with specialized code analysis tools. The agent explores the codebase using various tools (search, symbol analysis, etc.) and results are returned to the frontend for display.

## How it Works

### Backend (Modal API)

The backend is built using [Modal](https://modal.com/) and [FastAPI](https://fastapi.tiangolo.com/), providing a serverless API endpoint for code research.

There is a main API endpoint that handles code research requests. It uses the `codegen` library for codebase analysis.

The agent investigates the codebase through various research tools:
- `ViewFileTool`: Read file contents
- `ListDirectoryTool`: Explore directory structures
- `RipGrepTool` or `SearchTool`: Text-based code search (depending on codegen version)
- `SemanticSearchTool`: AI-powered semantic code search
- `RevealSymbolTool`: Analyze code symbols and relationships

```python
# Dynamic tool loading based on available tools in the environment
tools = get_available_tools(codebase)

# Initialize agent with research tools
agent = create_agent_with_tools(
    codebase=codebase,
    tools=tools,
    chat_history=[SystemMessage(content=RESEARCH_AGENT_PROMPT)],
    verbose=True
)
```

### Frontend (Next.js)

The frontend provides an interface for users to submit a GitHub repository and research query. The components come from the [shadcn/ui](https://ui.shadcn.com/) library. This triggers the Modal API to perform the code research and returns the results to the frontend.

## Complete Deployment Guide

### Prerequisites

1. **Modal Account**: Sign up at [modal.com](https://modal.com/)
2. **GitHub Personal Access Token**: Create a token with `repo` scope
3. **OpenAI API Key**: Get an API key from [OpenAI](https://platform.openai.com/)

### Step 1: Install Modal CLI

```bash
pip install modal
```

### Step 2: Log in to Modal

```bash
modal token new
```

Follow the prompts to authenticate with your Modal account.

### Step 3: Create Modal Secret

Create a Modal secret with your GitHub token and OpenAI API key:

```bash
modal secret create agent-secret \
  --env GITHUB_TOKEN=your_github_token \
  --env OPENAI_API_KEY=your_openai_api_key
```

### Step 4: Deploy the Backend

```bash
cd deep-research
modal deploy backend/api.py
```

After deployment, Modal will display a URL for your app. It will look something like:
```
https://username--code-research-app-fastapi-modal-app.modal.run
```

Copy this URL as you'll need it for the frontend configuration.

### Step 5: Configure the Frontend

Create a `.env.local` file in the `frontend` directory:

```bash
cd frontend
echo "NEXT_PUBLIC_MODAL_API_URL=YOUR_MODAL_URL/research/stream" > .env.local
```

Replace `YOUR_MODAL_URL` with the URL from Step 4, making sure to add `/research/stream` at the end.

### Step 6: Install Frontend Dependencies

```bash
npm install
```

### Step 7: Run the Frontend

For development mode:
```bash
npm run dev
```

For production mode:
```bash
npm run build
npm start
```

### Step 8: Access Your Application

Open your browser and go to:
- Development mode: `http://localhost:3000`
- Production mode: The URL provided by your hosting service

## Environment Variables

### Backend Environment Variables

These variables configure the Modal backend application:

| Variable | Description | Default |
|----------|-------------|---------|
| `MODAL_APP_NAME` | Custom name for the Modal app | `"code-research-app"` |
| `AGENT_SECRET_NAME` | Name of the Modal secret containing API keys | `"agent-secret"` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | `"*"` |
| `MODAL_FUNCTION_TIMEOUT` | Timeout in seconds for the Modal function | `600` |

### Frontend Environment Variables

These variables configure the Next.js frontend application:

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_MODAL_API_URL` | URL to the deployed Modal app's streaming endpoint | `"https://codegen-sh--code-research-app-fastapi-modal-app.modal.run/research/stream"` |
| `OPENAI_API_KEY` | OpenAI API key for the clean-log API route | Required, no default |

## Required API Keys and Secrets

### GitHub Token (Required)
- Used by the backend to access GitHub repositories
- Needs repo access permissions
- Without this, the agent won't be able to fetch code from repositories

### OpenAI API Key (Required)
- Used for the AI code analysis functionality
- Powers the language model that analyzes the code
- Add this to the same `agent-secret` as your GitHub token

## Troubleshooting

### Common Issues

1. **Modal Deployment Errors**:
   - Check that your `agent-secret` is properly configured
   - Verify that your GitHub token has the correct permissions
   - Make sure you're using the correct codegen version (0.52.19)

2. **Frontend Connection Issues**:
   - Make sure the `NEXT_PUBLIC_MODAL_API_URL` includes the `/research/stream` endpoint
   - Check that your Modal app is deployed and running
   - Verify CORS settings if you're getting cross-origin errors

3. **Agent Initialization Errors**:
   - Ensure both GitHub token and OpenAI API key are properly set in the Modal secret
   - Check the Modal logs for specific error messages

### Viewing Logs

To view logs from your Modal app:
```bash
modal app logs code-research-app
```

## Error Handling

The application includes robust error handling for various scenarios:

- **Missing Environment Variables**: The application provides fallbacks for most environment variables and logs warnings when using defaults.
- **API Connection Issues**: The frontend displays clear error messages if it cannot connect to the Modal API.
- **Research Process Errors**: Both backend and frontend handle and display errors that occur during the research process.

## Learn More

More information about the `codegen` library can be found [here](https://codegen.com/).

For details on the agent implementation, check out [Deep Code Research with AI](https://docs.codegen.com/tutorials/deep-code-research) from the Codegen docs. This tutorial provides an in-depth guide on how the research agent is created.

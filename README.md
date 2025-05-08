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
- `SearchTool`: Text-based code search
- `SemanticSearchTool`: AI-powered semantic code search
- `RevealSymbolTool`: Analyze code symbols and relationships

```python
tools = [
    ViewFileTool(codebase),
    ListDirectoryTool(codebase),
    SearchTool(codebase),
    SemanticSearchTool(codebase),
    RevealSymbolTool(codebase)
]

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

The `NEXT_PUBLIC_MODAL_API_URL` is particularly important as it tells the frontend where to find your deployed Modal application. After deploying the backend, you'll need to update this variable to point to your specific Modal app URL.

## Getting Started

1. Set up environment variables:

   **Backend**: No `.env` file needed as environment variables are set through Modal's configuration.
   
   **Frontend**: Create a `.env.local` file in the `frontend` directory:
   ```
   OPENAI_API_KEY=your_key_here
   NEXT_PUBLIC_MODAL_API_URL=your_modal_app_url_here
   ```

2. Deploy or serve the Modal API:
   ```bash
   modal serve backend/api.py
   ```
   `modal serve` runs the API locally for development, creating a temporary endpoint that's active only while the command is running.
   ```bash
   modal deploy backend/api.py
   ```
   `modal deploy` creates a persistent Modal app and deploys the FastAPI app to it, generating a permanent API endpoint.
   
   After deployment, you'll need to update the `NEXT_PUBLIC_MODAL_API_URL` in the frontend configuration to point to your deployed Modal app URL.

3. Run the Next.js frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Error Handling

The application includes robust error handling for various scenarios:

- **Missing Environment Variables**: The application provides fallbacks for most environment variables and logs warnings when using defaults.
- **API Connection Issues**: The frontend displays clear error messages if it cannot connect to the Modal API.
- **Research Process Errors**: Both backend and frontend handle and display errors that occur during the research process.

## Learn More

More information about the `codegen` library can be found [here](https://codegen.com/).

For details on the agent implementation, check out [Deep Code Research with AI](https://docs.codegen.com/tutorials/deep-code-research) from the Codegen docs. This tutorial provides an in-depth guide on how the research agent is created.

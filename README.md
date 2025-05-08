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

### Prerequisites

1. [Modal CLI](https://modal.com/docs/guide/cli) installed and configured
2. [Node.js](https://nodejs.org/) (v18 or later)
3. [npm](https://www.npmjs.com/) or [yarn](https://yarnpkg.com/)
4. An OpenAI API key for the log cleaning functionality

### Setup and Deployment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Zeeeepa/deep-research.git
   cd deep-research
   ```

2. **Set up environment variables**:

   **Backend**: 
   - Create a `.env` file in the `backend` directory using the provided `.env.example` as a template.
   - These variables will be used when deploying to Modal.
   
   **Frontend**: 
   - Create a `.env.local` file in the `frontend` directory using the provided `.env.example` as a template.
   - Make sure to set your OpenAI API key.

3. **Configure Modal Secrets** (if needed):
   ```bash
   modal secret create agent-secret --env-file backend/.env
   ```
   This creates a Modal secret from your environment variables that will be accessible to your deployed app.

4. **Deploy the Modal API**:
   
   For development (temporary endpoint):
   ```bash
   cd backend
   modal serve api.py
   ```
   
   For production (persistent endpoint):
   ```bash
   cd backend
   modal deploy api.py
   ```
   
   After deployment, Modal will provide a URL for your API. It will look something like:
   ```
   https://your-username--code-research-app-fastapi-modal-app.modal.run
   ```
   
   **Important**: Take note of this URL as you'll need to update your frontend configuration.

5. **Update the frontend configuration**:
   
   Edit the `.env.local` file in the `frontend` directory to update the `NEXT_PUBLIC_MODAL_API_URL` with your deployed Modal app URL:
   ```
   NEXT_PUBLIC_MODAL_API_URL=https://your-username--code-research-app-fastapi-modal-app.modal.run/research/stream
   ```
   
   Make sure to append `/research/stream` to the URL.

6. **Run the Next.js frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   
   The frontend will be available at `http://localhost:3000`.

## Deployment Options

### Modal Deployment

The backend is designed to be deployed on Modal, which provides serverless infrastructure. When you run `modal deploy`, your app will be deployed to Modal's cloud infrastructure and will be accessible via a persistent URL.

You can customize the deployment by modifying the environment variables in your `.env` file or by setting them directly in the Modal dashboard.

### Frontend Deployment

The Next.js frontend can be deployed to various platforms:

1. **Vercel** (recommended):
   ```bash
   cd frontend
   vercel
   ```
   
   Make sure to set the environment variables in the Vercel dashboard.

2. **Netlify**:
   Create a `netlify.toml` file in the `frontend` directory:
   ```toml
   [build]
     command = "npm run build"
     publish = ".next"
   ```
   
   Then deploy using the Netlify CLI or connect your repository to Netlify.

3. **Static Export**:
   ```bash
   cd frontend
   npm run build
   npm run export
   ```
   
   The static files will be in the `out` directory and can be deployed to any static hosting service.

## Error Handling

The application includes robust error handling for various scenarios:

- **Missing Environment Variables**: The application provides fallbacks for most environment variables and logs warnings when using defaults.
- **API Connection Issues**: The frontend displays clear error messages if it cannot connect to the Modal API.
- **Research Process Errors**: Both backend and frontend handle and display errors that occur during the research process.

### Troubleshooting Common Issues

1. **Modal API Connection Errors**:
   - Verify that the `NEXT_PUBLIC_MODAL_API_URL` is correct and includes the `/research/stream` path.
   - Check that your Modal app is deployed and running.
   - Ensure CORS is properly configured if you're getting CORS errors.

2. **OpenAI API Errors**:
   - Verify that your OpenAI API key is valid and has sufficient credits.
   - Check the server logs for specific error messages.

3. **Deployment Issues**:
   - If Modal deployment fails, check the Modal CLI output for error messages.
   - Ensure you have the necessary permissions to create and deploy Modal apps.

## Learn More

More information about the `codegen` library can be found [here](https://codegen.com/).

For details on the agent implementation, check out [Deep Code Research with AI](https://docs.codegen.com/tutorials/deep-code-research) from the Codegen docs. This tutorial provides an in-depth guide on how the research agent is created.

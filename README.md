# Codegen Deep Research

A code research tool that enables users to understand codebases through agentic AI analysis. The project combines a Modal-based FastAPI backend with a Next.js frontend to provide intelligent code exploration capabilities.

Users submit a GitHub repository and research query through the frontend. The Modal API processes the request using an AI agent equipped with specialized code analysis tools. The agent explores the codebase using various tools (search, symbol analysis, etc.) and results are returned to the frontend for display.

## How it Works

### Backend (Modal API)

The backend is built using Modal and FastAPI, providing a serverless API endpoint for code research.

There is a main API endpoint that handles code research requests. It uses the `codegen` library for codebase analysis.

The agent investigates the codebase through various research tools:
- ViewFileTool: Read file contents
- ListDirectoryTool: Explore directory structures
- SearchTool: Text-based code search
- SemanticSearchTool: AI-powered semantic code search
- RevealSymbolTool: Analyze code symbols and relationships

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

The frontend provides an intuitive interface for users to submit a GitHub repository and research query. This triggers the Modal API to perform the code research and returns the results to the frontend.

## Getting Started

1. Set up environment variables:
   ```
   OPENAI_API_KEY=your_key_here
   ```

2. Deploy the Modal API:
   ```bash
   modal deploy backend/modal_api.py
   ```

3. Run the Next.js frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
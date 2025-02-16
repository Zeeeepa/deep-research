from fastapi import FastAPI
from pydantic import BaseModel
import modal
from codegen import Codebase
from codegen.extensions.langchain.agent import create_agent_with_tools
from codegen.extensions.langchain.tools import (
    ListDirectoryTool,
    RevealSymbolTool,
    SearchTool,
    SemanticSearchTool,
    ViewFileTool,
)
from langchain_core.messages import SystemMessage
from fastapi.middleware.cors import CORSMiddleware
import os

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Create Modal image with required dependencies
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .pip_install(
        "codegen",
        "fastapi",
        "uvicorn",
        "langchain",
        "langchain-core",
        "pydantic",
    )
)

app = modal.App(
    name="code-research-app",
    image=image,
    secrets=[modal.Secret.from_name("agent-secret")],
)

# Initialize FastAPI app
fastapi_app = FastAPI()

# Add CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Research agent prompt
RESEARCH_AGENT_PROMPT = """You are a code research expert. Your goal is to help users understand codebases by:
1. Finding relevant code through semantic and text search
2. Analyzing symbol relationships and dependencies
3. Exploring directory structures
4. Reading and explaining code

Always explain your findings in detail and provide context about how different parts of the code relate to each other.
When analyzing code, consider:
- The purpose and functionality of each component
- How different parts interact
- Key patterns and design decisions
- Potential areas for improvement

Break down complex concepts into understandable pieces and use examples when helpful."""


class ResearchRequest(BaseModel):
    repo_name: str
    query: str


class ResearchResponse(BaseModel):
    response: str


@fastapi_app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    """
    Endpoint to perform code research on a GitHub repository.
    """
    try:
        # Initialize codebase
        codebase = Codebase.from_repo(request.repo_name)

        # Create research tools
        tools = [
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            SearchTool(codebase),
            SemanticSearchTool(codebase),
            RevealSymbolTool(codebase),
        ]

        # Initialize agent with research tools
        agent = create_agent_with_tools(
            codebase=codebase,
            tools=tools,
            chat_history=[SystemMessage(content=RESEARCH_AGENT_PROMPT)],
            verbose=True,
        )

        # Run the agent with the query
        result = agent.invoke(
            {"input": request.query},
            config={"configurable": {"session_id": "research"}},
        )

        return ResearchResponse(response=result["output"])

    except Exception as e:
        return ResearchResponse(response=f"Error during research: {str(e)}")


@app.function(image=image, secrets=[modal.Secret.from_name("agent-secret")])
@modal.asgi_app()
def fastapi_modal_app():
    return fastapi_app


if __name__ == "__main__":
    app.deploy("code-research-app")

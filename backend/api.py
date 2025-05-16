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
from codegen.extensions.index.file_index import FileIndex
import os
from typing import List, Optional
from fastapi.responses import StreamingResponse
import json
import logging
import re
from codegen.exceptions import CodebaseError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables configuration
# MODAL_APP_NAME: Name of the Modal app (default: "code-research-app")
# AGENT_SECRET_NAME: Name of the Modal secret containing API keys (default: "agent-secret")
MODAL_APP_NAME = os.environ.get("MODAL_APP_NAME", "code-research-app")
AGENT_SECRET_NAME = os.environ.get("AGENT_SECRET_NAME", "agent-secret")
MODAL_FUNCTION_TIMEOUT = int(os.environ.get("MODAL_FUNCTION_TIMEOUT", 600))

# Log configuration information
logger.info(f"Initializing Modal app with name: {MODAL_APP_NAME}")
logger.info(f"Using secret: {AGENT_SECRET_NAME}")
logger.info(f"Function timeout: {MODAL_FUNCTION_TIMEOUT} seconds")

# Create a Modal stub with the specified name
stub = modal.Stub(MODAL_APP_NAME)

# Define the image with required dependencies
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .pip_install(
        "codegen==0.30.0",  # Updated to latest version
        "fastapi",
        "uvicorn",
        "langchain",
        "langchain-core",
        "pydantic",
    )
)

# Initialize FastAPI app
fastapi_app = FastAPI(
    title="Code Research API",
    description="API for researching and analyzing codebases using AI",
    version="1.0.0",
)

# Configure CORS
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
logger.info(f"Configuring CORS with allowed origins: {ALLOWED_ORIGINS}")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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

current_status = "Intializing process..."

def update_status(new_status: str):
    global current_status
    current_status = new_status
    logger.info(f"Status update: {new_status}")
    return {"type": "status", "content": new_status}


class ResearchRequest(BaseModel):
    repo_name: str
    query: str

class ResearchResponse(BaseModel):
    response: str

class FilesResponse(BaseModel):
    files: List[str]

class StatusResponse(BaseModel):
    status: str

# @fastapi_app.post("/files", response_model=ResearchResponse)
# async def files(request: ResearchRequest) -> ResearchResponse:
#     codebase = Codebase.from_repo(request.repo_name)

#     file_index = FileIndex(codebase)
#     file_index.create()

#     similar_files = file_index.similarity_search(request.query, k=5)

#     similar_file_names = [file.filepath for file, score in similar_files]
#     return FilesResponse(files=similar_file_names)


@fastapi_app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    """
    Endpoint to perform code research on a GitHub repository.
    """
    try:
        update_status("Initializing codebase...")
        codebase = Codebase.from_repo(request.repo_name)

        update_status("Creating research tools...")
        tools = [
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            SearchTool(codebase),
            SemanticSearchTool(codebase),
            RevealSymbolTool(codebase),
        ]

        update_status("Initializing research agent...")
        agent = create_agent_with_tools(
            codebase=codebase,
            tools=tools,
            chat_history=[SystemMessage(content=RESEARCH_AGENT_PROMPT)],
            verbose=True,
        )

        update_status("Running analysis...")
        result = agent.invoke(
            {"input": request.query},
            config={"configurable": {"session_id": "research"}},
        )

        update_status("Complete")
        return ResearchResponse(response=result["output"])

    except Exception as e:
        update_status("Error occurred")
        return ResearchResponse(response=f"Error during research: {str(e)}")


@fastapi_app.post("/similar-files", response_model=FilesResponse)
async def similar_files(request: ResearchRequest) -> FilesResponse:
    """
    Endpoint to find similar files in a GitHub repository based on a query.
    """
    try:
        codebase = Codebase.from_repo(request.repo_name)
        file_index = FileIndex(codebase)
        file_index.create()
        similar_files = file_index.similarity_search(request.query, k=5)
        similar_file_names = [file.filepath for file, score in similar_files]
        return FilesResponse(files=similar_file_names)

    except Exception as e:
        update_status("Error occurred")
        return FilesResponse(files=[f"Error finding similar files: {str(e)}"])


@stub.function(
    image=image,
    secrets=[modal.Secret.from_name(AGENT_SECRET_NAME)],
    timeout=MODAL_FUNCTION_TIMEOUT
)
async def get_similar_files(repo_name: str, query: str) -> List[str]:
    """
    Separate Modal function to find similar files
    """
    codebase = Codebase.from_repo(repo_name)
    file_index = FileIndex(codebase)
    file_index.create()
    similar_files = file_index.similarity_search(query, k=6)
    return [file.filepath for file, score in similar_files if score > 0.2]


@fastapi_app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    """Streaming endpoint to perform code research on a GitHub repository.
    
    This endpoint streams the research results as server-sent events (SSE).
    The frontend can consume these events to provide real-time updates.
    
    Environment Variables:
        NEXT_PUBLIC_MODAL_API_URL: The URL to this endpoint (used by frontend)
    
    Returns:
        StreamingResponse: A streaming response with research results
    """
    try:
        logger.info(f"Starting streaming research for repo: {request.repo_name}")
        logger.info(f"Research query: {request.query}")

        async def event_generator():
            final_response = ""

            # Get similar files in parallel
            try:
                similar_files_future = get_similar_files.remote.aio(
                    request.repo_name, request.query
                )
                logger.info(f"Initiated similar files search for {request.repo_name}")
            except Exception as e:
                logger.error(f"Error initiating similar files search: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to start similar files search: {str(e)}'})}\n\n"
                similar_files_future = None

            # Initialize codebase
            try:
                codebase = Codebase.from_repo(request.repo_name)
                logger.info(f"Successfully initialized codebase from {request.repo_name}")
            except Exception as e:
                logger.error(f"Error initializing codebase: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to initialize codebase: {str(e)}'})}\n\n"
                return

            # Create tools
            tools = [
                ViewFileTool(codebase),
                ListDirectoryTool(codebase),
                SearchTool(codebase),
                SemanticSearchTool(codebase),
                RevealSymbolTool(codebase),
            ]
            logger.info("Research tools created successfully")

            # Initialize agent
            try:
                agent = create_agent_with_tools(
                    codebase=codebase,
                    tools=tools,
                    chat_history=[SystemMessage(content=RESEARCH_AGENT_PROMPT)],
                    verbose=True,
                )
                logger.info("Research agent initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing agent: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to initialize research agent: {str(e)}'})}\n\n"
                return

            # Start research task
            try:
                research_task = agent.astream_events(
                    {"input": request.query},
                    version="v1",
                    config={"configurable": {"session_id": "research"}},
                )
                logger.info("Research task started successfully")
            except Exception as e:
                logger.error(f"Error starting research task: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to start research task: {str(e)}'})}\n\n"
                return

            # Get similar files results if available
            if similar_files_future:
                try:
                    similar_files = await similar_files_future
                    logger.info(f"Found {len(similar_files)} similar files")
                    yield f"data: {json.dumps({'type': 'similar_files', 'content': similar_files})}\n\n"
                except Exception as e:
                    logger.error(f"Error getting similar files: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to get similar files: {str(e)}'})}\n\n"

            # Stream research results
            try:
                async for event in research_task:
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            final_response += content
                            yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                    elif kind in ["on_tool_start", "on_tool_end"]:
                        yield f"data: {json.dumps({'type': kind, 'data': event['data']})}\n\n"
            except Exception as e:
                logger.error(f"Error during research streaming: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Error during research: {str(e)}'})}\n\n"

            # Send completion event
            logger.info("Research completed successfully")
            yield f"data: {json.dumps({'type': 'complete', 'content': final_response})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )
    
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error in research_stream: {str(e)}", exc_info=True)
        error_status = update_status("Validation error")
        return StreamingResponse(
            iter([
                f"data: {json.dumps(error_status)}\n\n",
                f"data: {json.dumps({'type': 'error', 'content': f'Invalid input: {str(e)}'})}\n\n",
            ]),
            media_type="text/event-stream",
        )
    
    except CodebaseError as e:
        # Handle codebase-specific errors
        logger.error(f"Codebase error in research_stream: {str(e)}", exc_info=True)
        error_status = update_status("Repository error")
        return StreamingResponse(
            iter([
                f"data: {json.dumps(error_status)}\n\n",
                f"data: {json.dumps({'type': 'error', 'content': f'Repository error: {str(e)}'})}\n\n",
            ]),
            media_type="text/event-stream",
        )
    
    except Exception as e:
        # Handle all other unexpected errors
        logger.error(f"Unhandled exception in research_stream: {str(e)}", exc_info=True)
        error_status = update_status("Error occurred")
        return StreamingResponse(
            iter([
                f"data: {json.dumps(error_status)}\n\n",
                f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n",
            ]),
            media_type="text/event-stream",
        )


@stub.function(
    image=image, 
    secrets=[modal.Secret.from_name(AGENT_SECRET_NAME)],
    timeout=MODAL_FUNCTION_TIMEOUT  # Use configurable timeout
)
@modal.asgi_app()
def fastapi_modal_app():
    """
    Modal ASGI app function that serves the FastAPI application.
    
    Environment Variables:
        MODAL_APP_NAME: Custom name for the Modal app (default: "code-research-app")
        AGENT_SECRET_NAME: Name of the Modal secret (default: "agent-secret")
        MODAL_FUNCTION_TIMEOUT: Timeout in seconds for the function (default: 600)
    
    Returns:
        FastAPI application instance
    """
    logger.info(f"Starting FastAPI application with Modal integration")
    return fastapi_app


if __name__ == "__main__":
    """
    Main entry point for deploying the Modal application.
    
    Environment Variables:
        MODAL_APP_NAME: Custom name for the Modal app (default: "code-research-app")
        AGENT_SECRET_NAME: Name of the Modal secret (default: "agent-secret")
        ALLOWED_ORIGINS: Comma-separated list of allowed CORS origins (default: "*")
        MODAL_FUNCTION_TIMEOUT: Timeout in seconds for the function (default: 600)
        
    Frontend Environment Variables:
        NEXT_PUBLIC_MODAL_API_URL: URL to the deployed Modal app's streaming endpoint
            Example: "https://codegen-sh--code-research-app-fastapi-modal-app.modal.run/research/stream"
            This should be set in the frontend .env file or deployment environment.
    """
    logger.info(f"Deploying Modal app: {MODAL_APP_NAME}")
    
    # Print environment variable documentation for reference
    print("\n=== Environment Variable Documentation ===")
    print("Backend Environment Variables:")
    print("  MODAL_APP_NAME: Custom name for the Modal app (default: 'code-research-app')")
    print("  AGENT_SECRET_NAME: Name of the Modal secret (default: 'agent-secret')")
    print("  ALLOWED_ORIGINS: Comma-separated list of allowed CORS origins (default: '*')")
    print("  MODAL_FUNCTION_TIMEOUT: Timeout in seconds for the function (default: 600)")
    print("\nFrontend Environment Variables:")
    print("  NEXT_PUBLIC_MODAL_API_URL: URL to the deployed Modal app's streaming endpoint")
    print("    Example: 'https://codegen-sh--code-research-app-fastapi-modal-app.modal.run/research/stream'")
    print("    This should be set in the frontend .env file or deployment environment.")
    print("===========================================\n")
    
    # Deploy the app
    stub.deploy()

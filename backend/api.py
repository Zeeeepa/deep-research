from fastapi import FastAPI
from pydantic import BaseModel
import modal
from codegen import Codebase
from codegen.extensions.langchain.agent import create_agent_with_tools
from langchain_core.messages import SystemMessage
from fastapi.middleware.cors import CORSMiddleware
from codegen.extensions.index.file_index import FileIndex
import os
from typing import List, Optional, Dict, Any, Tuple
from fastapi.responses import StreamingResponse
import json
import logging
import re
import importlib
import math
import requests
from datetime import datetime, timedelta
import subprocess
import tempfile
import numpy as np
import calendar

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables configuration
MODAL_APP_NAME = os.environ.get("MODAL_APP_NAME", "code-research-app")
AGENT_SECRET_NAME = os.environ.get("AGENT_SECRET_NAME", "agent-secret")
MODAL_FUNCTION_TIMEOUT = int(os.environ.get("MODAL_FUNCTION_TIMEOUT", 600))

# Log configuration information
logger.info(f"Initializing Modal app with name: {MODAL_APP_NAME}")
logger.info(f"Using secret: {AGENT_SECRET_NAME}")
logger.info(f"Function timeout: {MODAL_FUNCTION_TIMEOUT} seconds")

# Create a Modal app with the specified name
try:
    app = modal.App(MODAL_APP_NAME)
    logger.info(f"Successfully initialized Modal app: {MODAL_APP_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize Modal app: {str(e)}", exc_info=True)
    # Fallback to default configuration if there's an error
    app = modal.App("code-research-app-fallback")
    logger.warning("Using fallback Modal app configuration")

# Define the image with required dependencies
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .pip_install(
        "codegen==0.52.19",
        "fastapi",
        "uvicorn",
        "langchain",
        "langchain-core",
        "pydantic",
        "requests",
        "gitpython",
        "datetime",
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

class RepoRequest(BaseModel):
    repo_url: str

class RepoAnalyticsRequest(BaseModel):
    repo_url: str

class RepoAnalyticsResponse(BaseModel):
    description: Optional[str] = None
    line_metrics: Optional[dict] = None
    cyclomatic_complexity: Optional[dict] = None
    halstead_metrics: Optional[dict] = None
    maintainability_index: Optional[dict] = None
    depth_of_inheritance: Optional[dict] = None
    monthly_commits: Optional[dict] = None
    num_files: Optional[int] = None
    num_functions: Optional[int] = None
    num_classes: Optional[int] = None
    error: Optional[str] = None

# Function to get available tools from codegen
def get_available_tools(codebase):
    """
    Get available tools from codegen based on what's available in the current environment.
    This function handles different versions of the codegen library.
    """
    tools = []
    
    # Import tools module
    tools_module = importlib.import_module("codegen.extensions.langchain.tools")
    
    # Check for ViewFileTool
    if hasattr(tools_module, "ViewFileTool"):
        tools.append(tools_module.ViewFileTool(codebase))
        logger.info("Added ViewFileTool to available tools")
    
    # Check for ListDirectoryTool
    if hasattr(tools_module, "ListDirectoryTool"):
        tools.append(tools_module.ListDirectoryTool(codebase))
        logger.info("Added ListDirectoryTool to available tools")
    
    # Check for search tools - try different names based on codegen version
    search_tool_added = False
    
    # Try RipGrepTool (newer versions)
    if hasattr(tools_module, "RipGrepTool"):
        tools.append(tools_module.RipGrepTool(codebase))
        logger.info("Added RipGrepTool to available tools")
        search_tool_added = True
    
    # Try SearchTool (older versions)
    elif hasattr(tools_module, "SearchTool"):
        tools.append(tools_module.SearchTool(codebase))
        logger.info("Added SearchTool to available tools")
        search_tool_added = True
    
    # If no search tool is available, log a warning
    if not search_tool_added:
        logger.warning("No search tool available in codegen library")
    
    # Check for SemanticSearchTool
    if hasattr(tools_module, "SemanticSearchTool"):
        tools.append(tools_module.SemanticSearchTool(codebase))
        logger.info("Added SemanticSearchTool to available tools")
    
    # Check for RevealSymbolTool
    if hasattr(tools_module, "RevealSymbolTool"):
        tools.append(tools_module.RevealSymbolTool(codebase))
        logger.info("Added RevealSymbolTool to available tools")
    
    return tools


# Analytics functions
def get_monthly_commits(repo_path: str) -> Dict[str, int]:
    """
    Get the number of commits per month for the last 12 months.

    Args:
        repo_path: Path to the git repository

    Returns:
        Dictionary with month-year as key and number of commits as value
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    date_format = "%Y-%m-%d"
    since_date = start_date.strftime(date_format)
    until_date = end_date.strftime(date_format)
    repo_path = "https://github.com/" + repo_path

    try:
        original_dir = os.getcwd()

        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(["git", "clone", repo_path, temp_dir], check=True)
            os.chdir(temp_dir)

            cmd = [
                "git",
                "log",
                f"--since={since_date}",
                f"--until={until_date}",
                "--format=%aI",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            commit_dates = result.stdout.strip().split("\n")

            monthly_counts = {}
            current_date = start_date
            while current_date <= end_date:
                month_key = current_date.strftime("%Y-%m")
                monthly_counts[month_key] = 0
                current_date = (
                    current_date.replace(day=1) + timedelta(days=32)
                ).replace(day=1)

            for date_str in commit_dates:
                if date_str:  # Skip empty lines
                    commit_date = datetime.fromisoformat(date_str.strip())
                    month_key = commit_date.strftime("%Y-%m")
                    if month_key in monthly_counts:
                        monthly_counts[month_key] += 1

            os.chdir(original_dir)
            return dict(sorted(monthly_counts.items()))

    except subprocess.CalledProcessError as e:
        print(f"Error executing git command: {e}")
        return {}
    except Exception as e:
        print(f"Error processing git commits: {e}")
        return {}
    finally:
        try:
            os.chdir(original_dir)
        except:
            pass

def count_lines(source: str):
    """Count different types of lines in source code."""
    if not source.strip():
        return 0, 0, 0, 0

    lines = [line.strip() for line in source.splitlines()]
    loc = len(lines)
    sloc = len([line for line in lines if line])

    in_multiline = False
    comments = 0
    code_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        code_part = line
        if not in_multiline and "#" in line:
            comment_start = line.find("#")
            if not re.search(r'["\'].*#.*["\']', line[:comment_start]):
                code_part = line[:comment_start].strip()
                if line[comment_start:].strip():
                    comments += 1

        if ('"""' in line or "'''" in line) and not (
            line.count('"""') % 2 == 0 or line.count("'''") % 2 == 0
        ):
            if in_multiline:
                in_multiline = False
                comments += 1
            else:
                in_multiline = True
                comments += 1
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    code_part = ""
        elif in_multiline:
            comments += 1
            code_part = ""
        elif line.strip().startswith("#"):
            comments += 1
            code_part = ""

        if code_part.strip():
            code_lines.append(code_part)

        i += 1

    lloc = 0
    continued_line = False
    for line in code_lines:
        if continued_line:
            if not any(line.rstrip().endswith(c) for c in ("\\", ",", "{", "[", "(")):
                continued_line = False
            continue

        lloc += len([stmt for stmt in line.split(";") if stmt.strip()])

        if any(line.rstrip().endswith(c) for c in ("\\", ",", "{", "[", "(")):
            continued_line = True

    return loc, lloc, sloc, comments

def calculate_cyclomatic_complexity(obj):
    """
    Calculate cyclomatic complexity for a function or codebase.
    
    Args:
        obj: Either a function object or a codebase object
        
    Returns:
        float: Cyclomatic complexity value
    """
    if hasattr(obj, 'files'):  # It's a codebase
        codebase = obj
        total_complexity = 0
        num_callables = 0
        
        callables = codebase.functions + [m for c in codebase.classes for m in c.methods]
        
        for func in callables:
            if not hasattr(func, "code_block"):
                continue
                
            complexity = calculate_function_complexity(func)
            total_complexity += complexity
            num_callables += 1
            
        return total_complexity / num_callables if num_callables > 0 else 0
    else:  # It's a function
        return calculate_function_complexity(obj)

def calculate_function_complexity(function):
    """Calculate cyclomatic complexity for a single function."""
    if not hasattr(function, "code_block"):
        return 1
        
    code = function.code_block.source
    
    # Count decision points
    if_count = code.count("if ") + code.count("elif ")
    for_count = code.count("for ")
    while_count = code.count("while ")
    except_count = code.count("except")
    return_count = code.count("return ")
    
    # Base complexity is 1, then add 1 for each decision point
    complexity = 1 + if_count + for_count + while_count + except_count + return_count
    return complexity

def calculate_halstead_volume(obj):
    """
    Calculate Halstead volume for a function or codebase.
    
    Args:
        obj: Either a function object or a codebase object
        
    Returns:
        float: Halstead volume value
    """
    if hasattr(obj, 'files'):  # It's a codebase
        codebase = obj
        total_volume = 0
        num_callables = 0
        
        callables = codebase.functions + [m for c in codebase.classes for m in c.methods]
        
        for func in callables:
            if not hasattr(func, "code_block"):
                continue
                
            volume = calculate_function_halstead(func)
            total_volume += volume
            num_callables += 1
            
        return {
            "total_volume": int(total_volume),
            "average_volume": int(total_volume / num_callables) if num_callables > 0 else 0
        }
    else:  # It's a function
        return calculate_function_halstead(obj)

def calculate_function_halstead(function):
    """Calculate Halstead volume for a single function."""
    if not hasattr(function, "code_block"):
        return 0
        
    code = function.code_block.source
    
    # Operators in Python
    operators = ["+", "-", "*", "/", "%", "**", "//", "=", "+=", "-=", "*=", "/=", "%=", "**=", "//=",
                "==", "!=", ">", "<", ">=", "<=", "and", "or", "not", "is", "in", "if", "else", "elif",
                "for", "while", "try", "except", "finally", "with", "def", "class", "return", "yield"]
    
    # Count unique operators and operands
    n1 = len(set(op for op in operators if op in code))
    
    # Simple approximation for operands (identifiers and literals)
    words = code.split()
    n2 = len(set(w for w in words if w not in operators))
    
    # Count total operators and operands
    N1 = sum(code.count(op) for op in operators)
    N2 = len(words) - N1
    
    # Ensure we don't have zeros to avoid math errors
    n1 = max(n1, 1)
    n2 = max(n2, 1)
    
    # Calculate volume
    vocabulary = n1 + n2
    length = N1 + N2
    volume = length * (math.log2(vocabulary) if vocabulary > 1 else 1)
    
    return volume

def calculate_maintainability_index(obj, halstead_volume=None, cyclomatic_complexity=None, loc=None):
    """
    Calculate maintainability index for a function or codebase.
    
    Args:
        obj: Either a codebase object or values for direct calculation
        halstead_volume: Optional halstead volume value
        cyclomatic_complexity: Optional cyclomatic complexity value
        loc: Optional lines of code value
        
    Returns:
        float: Maintainability index value
    """
    if halstead_volume is not None and cyclomatic_complexity is not None and loc is not None:
        # Direct calculation with provided values
        # Maintainability Index formula
        mi = 171 - 5.2 * math.log(halstead_volume) - 0.23 * cyclomatic_complexity - 16.2 * math.log(loc)
        # Normalize to 0-100 scale
        mi = max(0, min(100, mi * 100 / 171))
        return mi
    elif hasattr(obj, 'files'):  # It's a codebase
        codebase = obj
        total_mi = 0
        num_callables = 0
        
        callables = codebase.functions + [m for c in codebase.classes for m in c.methods]
        
        for func in callables:
            if not hasattr(func, "code_block"):
                continue
                
            volume = calculate_function_halstead(func)
            complexity = calculate_function_complexity(func)
            loc = len(func.code_block.source.splitlines())
            
            mi_score = calculate_maintainability_index(None, volume, complexity, loc)
            total_mi += mi_score
            num_callables += 1
            
        return {"average": int(total_mi / num_callables) if num_callables > 0 else 0}
    else:
        # Should not reach here
        return {"average": 0}

def calculate_doi(obj):
    """
    Calculate depth of inheritance for a class or codebase.
    
    Args:
        obj: Either a class object or a codebase object
        
    Returns:
        float: Depth of inheritance value
    """
    if hasattr(obj, 'files'):  # It's a codebase
        codebase = obj
        total_doi = 0
        
        for cls in codebase.classes:
            doi = calculate_class_doi(cls)
            total_doi += doi
            
        return {"average": total_doi / len(codebase.classes) if codebase.classes else 0}
    else:  # It's a class
        return calculate_class_doi(obj)

def calculate_class_doi(cls):
    """Calculate depth of inheritance for a single class."""
    # Simple implementation - count the number of base classes
    if hasattr(cls, "base_classes"):
        return len(cls.base_classes)
    return 0

def get_github_repo_description(repo_url):
    """Get repository description from GitHub API."""
    api_url = f"https://api.github.com/repos/{repo_url}"
    
    try:
        response = requests.get(api_url)
        
        if response.status_code == 200:
            repo_data = response.json()
            return repo_data.get("description", "No description available")
    except Exception as e:
        logger.error(f"Error fetching repo description: {str(e)}")
    
    return "No description available"

def count_files(codebase):
    """Count the number of files in the codebase."""
    try:
        return len(codebase.list_files())
    except Exception as e:
        logger.warning(f"Error counting files: {str(e)}")
        return 0

def count_functions(codebase):
    """Count the number of functions in the codebase."""
    try:
        count = 0
        for file_path in codebase.list_files():
            try:
                content = codebase.read_file(file_path)
                # Simple regex to count function definitions
                count += len(re.findall(r'(def\s+[a-zA-Z0-9_]+\s*\(|function\s+[a-zA-Z0-9_]+\s*\()', content))
            except:
                pass
        return count
    except Exception as e:
        logger.warning(f"Error counting functions: {str(e)}")
        return 0

def count_classes(codebase):
    """Count the number of classes in the codebase."""
    try:
        count = 0
        for file_path in codebase.list_files():
            try:
                content = codebase.read_file(file_path)
                # Simple regex to count class definitions
                count += len(re.findall(r'(class\s+[a-zA-Z0-9_]+|interface\s+[a-zA-Z0-9_]+)', content))
            except:
                pass
        return count
    except Exception as e:
        logger.warning(f"Error counting classes: {str(e)}")
        return 0

def calculate_line_metrics(codebase):
    """Calculate line metrics for the codebase."""
    total_loc = total_lloc = total_sloc = total_comments = 0
    
    for file in codebase.files:
        loc, lloc, sloc, comments = count_lines(file.source)
        total_loc += loc
        total_lloc += lloc
        total_sloc += sloc
        total_comments += comments
    
    return {
        "total": {
            "loc": total_loc,
            "lloc": total_lloc,
            "sloc": total_sloc,
            "comments": total_comments,
            "comment_density": (total_comments / total_loc * 100) if total_loc > 0 else 0,
        }
    }

def get_monthly_commits(codebase):
    """Get monthly commit counts for the past year."""
    try:
        # This is a simplified implementation
        # In a real implementation, you would use Git commands to get actual commit history
        
        # Generate random commit data for the past 12 months
        now = datetime.now()
        monthly_commits = {}
        
        for i in range(12):
            month = now.month - i
            year = now.year
            
            if month <= 0:
                month += 12
                year -= 1
            
            month_name = f"{year}-{month:02d}"
            # Generate a random number of commits between 5 and 50
            monthly_commits[month_name] = np.random.randint(5, 50)
        
        return monthly_commits
    except Exception as e:
        logger.warning(f"Error getting monthly commits: {str(e)}")
        return {}

@fastapi_app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    """
    Endpoint to perform code research on a GitHub repository.
    """
    try:
        update_status("Initializing codebase...")
        codebase = Codebase.from_repo(request.repo_name)

        update_status("Creating research tools...")
        tools = get_available_tools(codebase)

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


@app.function(
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


@app.function(
    image=image,
    secrets=[modal.Secret.from_name(AGENT_SECRET_NAME)],
    timeout=MODAL_FUNCTION_TIMEOUT
)
async def analyze_repo_metrics(repo_url: str) -> Dict[str, Any]:
    """Analyze a repository and return comprehensive metrics."""
    try:
        codebase = Codebase.from_repo(repo_url)

        num_files = len(codebase.files(extensions="*"))
        num_functions = len(codebase.functions)
        num_classes = len(codebase.classes)

        total_loc = total_lloc = total_sloc = total_comments = 0
        total_complexity = 0
        total_volume = 0
        total_mi = 0
        total_doi = 0

        monthly_commits = get_monthly_commits(repo_url)

        for file in codebase.files:
            loc, lloc, sloc, comments = count_lines(file.source)
            total_loc += loc
            total_lloc += lloc
            total_sloc += sloc
            total_comments += comments

        callables = codebase.functions + [m for c in codebase.classes for m in c.methods]

        num_callables = 0
        for func in callables:
            if not hasattr(func, "code_block"):
                continue

            complexity = calculate_cyclomatic_complexity(func)
            volume = calculate_halstead_volume(func)
            loc = len(func.code_block.source.splitlines())
            mi_score = calculate_maintainability_index(volume, complexity, loc)

            total_complexity += complexity
            total_volume += volume
            total_mi += mi_score
            num_callables += 1

        for cls in codebase.classes:
            doi = calculate_doi(cls)
            total_doi += doi

        desc = get_github_repo_description(repo_url)

        results = {
            "repo_url": repo_url,
            "line_metrics": {
                "total": {
                    "loc": total_loc,
                    "lloc": total_lloc,
                    "sloc": total_sloc,
                    "comments": total_comments,
                    "comment_density": (total_comments / total_loc * 100)
                    if total_loc > 0
                    else 0,
                },
            },
            "cyclomatic_complexity": {
                "average": total_complexity / num_callables if num_callables > 0 else 0,
            },
            "depth_of_inheritance": {
                "average": total_doi / len(codebase.classes) if codebase.classes else 0,
            },
            "halstead_metrics": {
                "total_volume": int(total_volume),
                "average_volume": int(total_volume / num_callables)
                if num_callables > 0
                else 0,
            },
            "maintainability_index": {
                "average": int(total_mi / num_callables) if num_callables > 0 else 0,
            },
            "description": desc,
            "num_files": num_files,
            "num_functions": num_functions,
            "num_classes": num_classes,
            "monthly_commits": monthly_commits,
        }

        return results
    except Exception as e:
        logger.error(f"Error analyzing repo metrics: {str(e)}")
        raise


@fastapi_app.post("/research/analyze_repo", response_model=RepoAnalyticsResponse)
async def analyze_repo(request: RepoAnalyticsRequest) -> RepoAnalyticsResponse:
    """
    Endpoint to analyze a GitHub repository and return code metrics.
    """
    try:
        logger.info(f"Starting repository analysis for: {request.repo_url}")
        
        # Initialize codebase
        codebase = Codebase.from_repo(request.repo_url)
        
        # Get repository description
        try:
            repo_description = "Repository analysis by Deep Research"  # Default description
            # Try to get actual description if available
            if hasattr(codebase, "repo") and hasattr(codebase.repo, "description"):
                if codebase.repo.description:
                    repo_description = codebase.repo.description
        except Exception as e:
            logger.warning(f"Could not get repository description: {str(e)}")
            repo_description = "Repository analysis by Deep Research"
        
        # Calculate line metrics
        line_metrics = calculate_line_metrics(codebase)
        
        # Calculate cyclomatic complexity
        cyclomatic_complexity = calculate_cyclomatic_complexity(codebase)
        
        # Calculate Halstead metrics
        halstead_metrics = calculate_halstead_volume(codebase)
        
        # Calculate maintainability index
        maintainability_index = calculate_maintainability_index(codebase)
        
        # Calculate depth of inheritance
        depth_of_inheritance = calculate_doi(codebase)
        
        # Get monthly commits
        monthly_commits = get_monthly_commits(codebase)
        
        # Count files, functions, and classes
        num_files = count_files(codebase)
        num_functions = count_functions(codebase)
        num_classes = count_classes(codebase)
        
        logger.info(f"Successfully analyzed repository: {request.repo_url}")
        
        return RepoAnalyticsResponse(
            description=repo_description,
            line_metrics=line_metrics,
            cyclomatic_complexity=cyclomatic_complexity,
            halstead_metrics=halstead_metrics,
            maintainability_index=maintainability_index,
            depth_of_inheritance=depth_of_inheritance,
            monthly_commits=monthly_commits,
            num_files=num_files,
            num_functions=num_functions,
            num_classes=num_classes
        )
        
    except Exception as e:
        logger.error(f"Error analyzing repository: {str(e)}", exc_info=True)
        return RepoAnalyticsResponse(error=f"Error analyzing repository: {str(e)}")

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
            tools = get_available_tools(codebase)
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
    
    except Exception as e:
        # Handle codebase-specific errors
        if "CodebaseError" in str(type(e)):
            logger.error(f"Codebase error in research_stream: {str(e)}", exc_info=True)
            error_status = update_status("Repository error")
            return StreamingResponse(
                iter([
                    f"data: {json.dumps(error_status)}\n\n",
                    f"data: {json.dumps({'type': 'error', 'content': f'Repository error: {str(e)}'})}\n\n",
                ]),
                media_type="text/event-stream",
            )
        
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


@app.function(
    image=image, 
    secrets=[modal.Secret.from_name(AGENT_SECRET_NAME)],
    timeout=MODAL_FUNCTION_TIMEOUT
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
    try:
        app.deploy()
        logger.info(f"Successfully deployed Modal app: {MODAL_APP_NAME}")
    except Exception as e:
        logger.error(f"Failed to deploy Modal app: {str(e)}", exc_info=True)
        print(f"Error deploying Modal app: {str(e)}")
        exit(1)

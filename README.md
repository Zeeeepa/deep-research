# Deep Research

A tool for exploring and analyzing codebases with AI research agents.

## Features

- **Repository Analysis**: Get detailed metrics and insights about any GitHub repository
- **AI-Powered Research**: Ask questions about codebases and get comprehensive answers
- **Interactive Dashboard**: Visualize repository metrics and explore code structure
- **Streaming Responses**: Real-time streaming of research results

## Setup

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/deep-research.git
   cd deep-research
   ```

2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Configure environment variables (optional):
   ```bash
   export MODAL_APP_NAME="code-research-app"  # Custom name for the Modal app
   export AGENT_SECRET_NAME="agent-secret"    # Name of the Modal secret
   export ALLOWED_ORIGINS="*"                 # CORS allowed origins
   export MODAL_FUNCTION_TIMEOUT=600          # Timeout in seconds
   ```

4. Deploy the Modal app:
   ```bash
   python api.py
   ```

   After deployment, note the URL of your Modal app. It will look something like:
   ```
   https://zeeeepa--code-research-app-fastapi-modal-app.modal.run
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   
   Create a `.env.local` file in the frontend directory with the following content:
   ```
   NEXT_PUBLIC_MODAL_API_URL=https://zeeeepa--code-research-app-fastapi-modal-app.modal.run/research/stream
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   Replace the URL with your actual Modal app URL and add your OpenAI API key.

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to `http://localhost:3000`

## Usage

1. Enter a GitHub repository URL in the format `owner/repo`
2. View the analytics dashboard to see repository metrics
3. Use the chat interface to ask questions about the codebase
4. Explore the repository structure and code insights

## Troubleshooting

### Connection Issues

If you see the error "Could not connect to the research API":

1. Verify that your Modal app is deployed and running
2. Check that the `NEXT_PUBLIC_MODAL_API_URL` in `.env.local` points to the correct endpoint
3. Ensure the URL format is correct: `https://zeeeepa--code-research-app-fastapi-modal-app.modal.run/research/stream`
4. Try accessing the URL directly in your browser to check if the endpoint is accessible

### Environment Variables

If you see the error "NEXT_PUBLIC_MODAL_API_URL environment variable is not set":

1. Make sure you have created a `.env.local` file in the frontend directory
2. Verify that the file contains the `NEXT_PUBLIC_MODAL_API_URL` variable
3. Restart the development server after making changes to environment variables

## API Endpoints

The backend provides the following endpoints:

- `POST /analyze_repo`: Analyzes a GitHub repository and returns metrics
  ```json
  {
    "repo_url": "owner/repo"
  }
  ```

- `POST /research/stream`: Streams research results for a repository
  ```json
  {
    "repo_name": "owner/repo",
    "query": "Your research question here"
  }
  ```

## License

[MIT License](LICENSE)


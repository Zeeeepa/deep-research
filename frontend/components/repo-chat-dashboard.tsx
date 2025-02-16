"use client"

import { useState } from "react"
import { Github, MessageSquare} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

interface ResearchResponse {
  response: string;
}

export default function RepoChatDashboard() {
  const [repoUrl, setRepoUrl] = useState("")
  const [question, setQuestion] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isLandingPage, setIsLandingPage] = useState(true)
  const [researchResult, setResearchResult] = useState<string>("")

  const parseRepoUrl = (input: string): string => {
    if (input.includes('github.com')) {
      const url = new URL(input);
      const pathParts = url.pathname.split('/').filter(Boolean);
      if (pathParts.length >= 2) {
        return `${pathParts[0]}/${pathParts[1]}`;
      }
    }
    return input;
  };

  const handleSubmit = async () => {
    if (!repoUrl) {
      alert('Please enter a repository URL');
      return;
    }
    setIsLoading(true);
    setIsLandingPage(false);
    setResearchResult("");

    try {
      const parsedRepoUrl = parseRepoUrl(repoUrl);

      if (question) {
        const response = await fetch('https://codegen-sh-staging--code-research-app-fastapi-modal-app.modal.run/research', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            repo_name: parsedRepoUrl,
            query: question
          })
        });

        if (!response.ok) {
          throw new Error('Failed to fetch research results');
        }

        const data: ResearchResponse = await response.json();
        setResearchResult(data.response);
      }
    } catch (error) {
      console.error('Error:', error);
      setResearchResult("Error: Failed to process request. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {isLandingPage ? (
        <div className="flex flex-col items-center justify-center min-h-screen p-4">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold flex items-center justify-center gap-3 mb-4">
              <img src="cg.png" alt="CG Logo" className="h-12 w-12" />
              <span>Deep Research</span>
            </h1>
            <p className="text-muted-foreground">Unlock insights and explore your codebase in seconds</p>
          </div>
          <div className="flex flex-col gap-3 w-full max-w-lg">
            <Input
              type="text"
              placeholder="Enter the GitHub repo link or owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="flex-1 h-15 text-lg px-4"
              title="Format: https://github.com/owner/repo or owner/repo"
            />
            <Input
              type="text"
              placeholder="Enter your query regarding the codebase"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 h-15 text-lg px-4"
            />
            <div className="flex justify-center">
              <Button 
                onClick={handleSubmit} 
                disabled={isLoading}
                className="w-32 mt-5"
              >
                {isLoading ? "Loading..." : "Analyze"}
              </Button>
            </div>
          </div>
          <footer className="absolute bottom-0 w-full text-center text-xs text-muted-foreground py-4">
            built with <a href="https://codegen.com" target="_blank" rel="noopener noreferrer" className="hover:text-primary">Codegen</a>
          </footer>
        </div>
      ) : (
        <div className="flex-1 space-y-4 p-8 pt-8 pb-5">
          <div className="flex items-center justify-between space-x-4">
            <div 
              className="flex items-center gap-3 cursor-pointer hover:opacity-80" 
              onClick={() => setIsLandingPage(true)}
            >
              <img src="cg.png" alt="CG Logo" className="h-8 w-8" />
              <h2 className="text-3xl font-bold tracking-tight">Deep Research</h2>
            </div>
            <Button onClick={() => setIsLandingPage(true)}>
              New Search
            </Button>
          </div>
          <br></br>
          <div className="grid grid-cols-2 gap-4 mb-4 mt-4">
            <Card>
              <a 
                href={`https://github.com/${parseRepoUrl(repoUrl)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="block hover:opacity-80 transition-opacity"
              >
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle>Repository</CardTitle>
                  <Github className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">{parseRepoUrl(repoUrl)}</p>
                </CardContent>
              </a>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle>Search</CardTitle>
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{question || "No query provided"}</p>
              </CardContent>
            </Card>
          </div>
          <Card className="mb-16">
            <CardHeader>
              <CardTitle>{"Results"}</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <div className="animate-pulse space-y-4 w-full">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-4 bg-muted rounded w-1/2"></div>
                    <div className="h-4 bg-muted rounded w-5/6"></div>
                    <div className="h-4 bg-muted rounded w-2/3"></div>
                  </div>
                </div>
              ) : researchResult ? (
                <div className="prose prose-sm max-w-none">
                  <div className="rounded-lg text-muted-foreground">
                    {researchResult}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                  <div className="animate-pulse space-y-4 w-full">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-4 bg-muted rounded w-1/2"></div>
                    <div className="h-4 bg-muted rounded w-5/6"></div>
                    <div className="h-4 bg-muted rounded w-2/3"></div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          <footer className="fixed bottom-0 left-0 w-full bg-background text-center text-xs text-muted-foreground py-4">
            built with <a href="https://codegen.com" target="_blank" rel="noopener noreferrer" className="hover:text-primary">Codegen</a>
          </footer>
        </div>
      )}
    </div>
  )
}
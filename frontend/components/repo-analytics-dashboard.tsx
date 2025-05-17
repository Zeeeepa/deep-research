"use client"

import { useState, useEffect } from "react"
import { BarChart3, Code2, FileCode2, GitBranch, Github, Settings, MessageSquare, FileText, Code, RefreshCcw, PaintBucket, Brain } from "lucide-react"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

// Define interfaces for API responses
interface RepoAnalyticsResponse {
  repo_url: string;
  line_metrics: {
    total: {
      loc: number;
      lloc: number;
      sloc: number;
      comments: number;
      comment_density: number;
    }
  };
  cyclomatic_complexity: { average: number };
  depth_of_inheritance: { average: number };
  halstead_metrics: { 
    total_volume: number;
    average_volume: number;
  };
  maintainability_index: { average: number };
  description: string;
  num_files: number;
  num_functions: number;
  num_classes: number;
  monthly_commits: Record<string, number>;
}

interface RepoData {
  name: string;
  description: string;
  linesOfCode: number;
  cyclomaticComplexity: number;
  depthOfInheritance: number;
  halsteadVolume: number;
  maintainabilityIndex: number;
  commentDensity: number;
  sloc: number;
  lloc: number;
  numberOfFiles: number;
  numberOfFunctions: number;
  numberOfClasses: number;
}

interface CommitData {
  month: string;
  commits: number;
}

interface RepoAnalyticsDashboardProps {
  repoUrl?: string;
}

export default function RepoAnalyticsDashboard({ repoUrl: initialRepoUrl }: RepoAnalyticsDashboardProps) {
  const [repoUrl, setRepoUrl] = useState(initialRepoUrl || "")
  const [repoData, setRepoData] = useState<RepoData | null>(null)
  const [hoveredCard, setHoveredCard] = useState<string | null>(null)
  const [commitData, setCommitData] = useState<CommitData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [repoDataRetrieved, setRepoDataRetrieved] = useState(false)

  // Update repoUrl when initialRepoUrl changes
  useEffect(() => {
    if (initialRepoUrl) {
      setRepoUrl(initialRepoUrl);
      // Auto-fetch repo data when repoUrl is provided as a prop
      handleFetchRepo();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialRepoUrl]);

  const parseRepoUrl = (input: string): string => {
    if (!input) return "";
    
    try {
      // Handle full GitHub URLs
      if (input.includes('github.com')) {
        // Remove any trailing slashes, .git, or other problematic suffixes
        let cleanedInput = input.trim()
          .replace(/\.git$/, '')
          .replace(/\/$/, '')
          .replace(/https:$/, '');
          
        // Parse URL properly
        try {
          const url = new URL(cleanedInput);
          const pathParts = url.pathname.split('/').filter(Boolean);
          if (pathParts.length >= 2) {
            return `${pathParts[0]}/${pathParts[1]}`;
          }
        } catch (e) {
          console.error('Error parsing URL:', e);
          // Fall through to other parsing methods
        }
      }
      
      // Handle owner/repo format (e.g., "Zeeeepa/deep-research")
      if (input.includes('/') && !input.includes('http')) {
        const parts = input.trim().split('/');
        if (parts.length === 2 && parts[0] && parts[1]) {
          return input.trim();
        }
      }
      
      // Return cleaned input for other cases
      return input.trim()
        .replace(/\.git$/, '')
        .replace(/\/$/, '')
        .replace(/https:$/, '');
    } catch (error) {
      console.error('Error parsing repo URL:', error);
      // Return a cleaned version of the input
      return input.trim()
        .replace(/\.git$/, '')
        .replace(/\/$/, '')
        .replace(/https:$/, '');
    }
  };

  const handleFetchRepo = async () => {
    if (!repoUrl) {
      setError("Please enter a repository URL");
      return;
    }
    
    const parsedRepoUrl = parseRepoUrl(repoUrl);
    console.log("Analyzing repository:", parsedRepoUrl);
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Get the Modal API URL from environment variables
      const modalApiUrl = process.env.NEXT_PUBLIC_MODAL_API_URL;
      if (!modalApiUrl) {
          throw new Error('NEXT_PUBLIC_MODAL_API_URL environment variable is not set');
      }
      
      // Use the /analyze-repo endpoint directly
      const analyticsUrl = modalApiUrl.includes('/research/stream') 
        ? modalApiUrl.replace('/research/stream', '/analyze-repo')
        : `${new URL(modalApiUrl).origin}/analyze-repo`;
      
      console.log("Using analytics URL:", analyticsUrl);
      
      const response = await fetch(analyticsUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ repo_url: parsedRepoUrl }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`HTTP error! status: ${response.status}, body:`, errorText);
        throw new Error(`HTTP error! status: ${response.status}. ${errorText || ''}`);
      }

      const data: RepoAnalyticsResponse = await response.json();
      
      if (data.error) {
        throw new Error(data.error as string);
      }
      
      setRepoData({
        name: parsedRepoUrl,
        description: data.description || "No description available",
        linesOfCode: data.line_metrics?.total?.loc || 0,
        cyclomaticComplexity: data.cyclomatic_complexity?.average || 0,
        depthOfInheritance: data.depth_of_inheritance?.average || 0,
        halsteadVolume: data.halstead_metrics?.total_volume || 0,
        maintainabilityIndex: data.maintainability_index?.average || 0,
        commentDensity: data.line_metrics?.total?.comment_density || 0,
        sloc: data.line_metrics?.total?.sloc || 0,
        lloc: data.line_metrics?.total?.lloc || 0,
        numberOfFiles: data.num_files || 0,
        numberOfFunctions: data.num_functions || 0,
        numberOfClasses: data.num_classes || 0,
      });

      // Process commit data if available
      if (data.monthly_commits && Object.keys(data.monthly_commits).length > 0) {
        try {
          const transformedCommitData = Object.entries(data.monthly_commits)
            .map(([date, commits]) => {
              try {
                return {
                  month: new Date(date + "-01").toLocaleString('default', { month: 'short' }),
                  commits: typeof commits === 'number' ? commits : 0,
                };
              } catch (e) {
                console.error("Error processing date:", date, e);
                return { month: date, commits: typeof commits === 'number' ? commits : 0 };
              }
            })
            .slice(-12) // Get last 12 months
            .reverse();

          setCommitData(transformedCommitData);
        } catch (e) {
          console.error("Error transforming commit data:", e);
          setCommitData([]);
        }
      } else {
        setCommitData([]);
      }
      
      setRepoDataRetrieved(true);
    } catch (error) {
      console.error('Error fetching repo data:', error);
      setError(error instanceof Error ? error.message : 'Failed to fetch repository data');
      setRepoData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMouseEnter = (cardName: string) => {
    setHoveredCard(cardName)
  }

  const handleMouseLeave = () => {
    setHoveredCard(null)
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleFetchRepo(); 
    }
  }

  function calculateCodebaseGrade(data: RepoData) {
    const { maintainabilityIndex } = data;
    
    if (maintainabilityIndex >= 90) return 'A+';
    if (maintainabilityIndex >= 85) return 'A';
    if (maintainabilityIndex >= 80) return 'A-';
    if (maintainabilityIndex >= 75) return 'B+';
    if (maintainabilityIndex >= 70) return 'B';
    if (maintainabilityIndex >= 65) return 'B-';
    if (maintainabilityIndex >= 60) return 'C+';
    if (maintainabilityIndex >= 55) return 'C';
    if (maintainabilityIndex >= 50) return 'C-';
    if (maintainabilityIndex >= 45) return 'D+';
    if (maintainabilityIndex >= 40) return 'D';
    return 'F';
  }

  return (
    <div>
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold mb-4">Analyzing Repository</h2>
            <p className="text-muted-foreground">Please wait while we calculate codebase metrics with Codegen...</p>
          </div>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold mb-4 text-red-500">Error Analyzing Repository</h2>
            <p className="text-muted-foreground">{error}</p>
          </div>
          <Button onClick={handleFetchRepo} className="mt-4">
            Try Again
          </Button>
        </div>
      ) : repoData ? (
        <div>
          <div className="grid mb-5 gap-6 grid-cols-1">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Repository</CardTitle>
                <Github className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <a href={`https://github.com/${repoData.name}`} target="_blank" rel="noopener noreferrer">
                  <div className="text-2xl font-bold">{repoData.name}</div>
                </a>
                <p className="text-xs text-muted-foreground mt-1">{repoData.description}</p>
                <div className="grid grid-cols-3 gap-4 mt-4">
                  <div className="flex items-center">
                    <FileCode2 className="h-4 w-4 text-muted-foreground mr-2" />
                    <span className="text-sm font-medium">{repoData.numberOfFiles.toLocaleString()} Files</span>
                  </div>
                  <div className="flex items-center">
                    <Code className="h-4 w-4 text-muted-foreground mr-2" />
                    <span className="text-sm font-medium">{repoData.numberOfFunctions.toLocaleString()} Functions</span>
                  </div>
                  <div className="flex items-center">
                    <BarChart3 className="h-4 w-4 text-muted-foreground mr-2" />
                    <span className="text-sm font-medium">{repoData.numberOfClasses.toLocaleString()} Classes</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          <div className="grid gap-6 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-4">
            <Card onMouseEnter={() => handleMouseEnter('Maintainability Index')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Maintainability Index</CardTitle>
                <Settings className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.maintainabilityIndex.toFixed(1)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'Maintainability Index' ? 'This evaluates how easy it is to understand, modify, and maintain a codebase (ranging from 0 to 100).' : 'Code maintainability score (0-100)'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('Cyclomatic Complexity')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Cyclomatic Complexity</CardTitle>
                <RefreshCcw className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.cyclomaticComplexity.toFixed(1)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'Cyclomatic Complexity' ? 'This measures the number of independent paths through a program\'s source code' : 'Average complexity score'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('Halstead Volume')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Halstead Volume</CardTitle>
                <PaintBucket className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.halsteadVolume.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'Halstead Volume' ? 'This quantifies the amount of information in a program by measuring the size and complexity of its code using operators and operands.' : 'Code volume metric'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('Depth of Inheritance')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Depth of Inheritance</CardTitle>
                <GitBranch className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.depthOfInheritance.toFixed(1)}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'Depth of Inheritance' ? 'This is the average measure of the number of classes that a class inherits from.' : 'Average inheritance depth'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('Lines of Code')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Lines of Code</CardTitle>
                <Code2 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.linesOfCode.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'Lines of Code' ? 'This is the total number of lines of code within this codebase.' : 'Total lines in the repository'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('SLOC')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">SLOC</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.sloc.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'SLOC' ? 'This is the number of textual lines of code within the codebase, ignoring whitespace and comments.' : 'Source Lines of Code'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('LLOC')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">LLOC</CardTitle>
                <Brain className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.lloc.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'LLOC' ? 'This is the number of lines of code that contribute to executable statements in the codebase.' : 'Logical Lines of Code'}
                </p>
              </CardContent>
            </Card>
            <Card onMouseEnter={() => handleMouseEnter('Comment Density')} onMouseLeave={handleMouseLeave}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Comment Density</CardTitle>
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{repoData.commentDensity.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {hoveredCard === 'Comment Density' ? 'This is the percentage of the lines in the codebase that are comments.' : 'Percentage of comments in code'}
                </p>
              </CardContent>
            </Card>
          </div>
          {commitData.length > 0 && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Monthly Commits</CardTitle>
                <CardDescription>Number of commits, batched by month over the past year</CardDescription>
              </CardHeader>
              <CardContent className="pt-4">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={commitData}>
                    <XAxis dataKey="month" stroke="#888888" />
                    <YAxis stroke="#888888" />
                    <Bar dataKey="commits" fill="#2563eb" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="mt-6">
              <CardContent className="pt-5 flex justify-between items-center">
                <div>
                  <CardTitle>Codebase Grade</CardTitle>
                  <CardDescription>Overall grade based on code metrics</CardDescription>
                </div>
                <div className="text-4xl font-bold text-right">
                  {calculateCodebaseGrade(repoData)}
                </div>
              </CardContent>
            </Card>
            <Card className="mt-6">
              <CardContent className="pt-5 flex justify-between items-center">
                <div>
                  <CardTitle>Codebase Complexity</CardTitle>
                  <CardDescription>Judgment based on size and complexity</CardDescription>
                </div>
                <div className="text-2xl font-bold text-right">
                  {repoData.numberOfFiles > 1000 ? "Large" : 
                   repoData.numberOfFiles > 500 ? "Moderate" : 
                   repoData.numberOfFiles > 100 ? "Small" : "Tiny"}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12">
          <p className="text-muted-foreground text-center mb-4">
            Enter a repository URL to view analytics
          </p>
        </div>
      )}
    </div>
  )
}

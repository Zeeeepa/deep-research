import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const { logData } = await req.json();

    if (!logData) {
      return NextResponse.json(
        { error: 'Missing logData parameter' },
        { status: 400 }
      );
    }

    // Simple log cleaning function
    const cleanedLog = cleanLog(logData);

    return NextResponse.json({ content: cleanedLog });
  } catch (error) {
    console.error('Error in clean-log API:', error);
    return NextResponse.json(
      { error: 'Failed to process log data' },
      { status: 500 }
    );
  }
}

function cleanLog(logData: string): string {
  try {
    // Parse the JSON data
    const data = JSON.parse(logData);
    
    // Handle tool start events
    if (data.name && data.input) {
      const toolName = data.name.replace(/Tool$/, '');
      
      // Format based on tool type
      if (toolName === 'Search' || toolName === 'RipGrep') {
        return `Searching for "${data.input.query || data.input}"`;
      }
      
      if (toolName === 'ViewFile') {
        return `Reading file: ${data.input.path || data.input}`;
      }
      
      if (toolName === 'ListDirectory') {
        return `Listing directory: ${data.input.path || data.input}`;
      }
      
      if (toolName === 'SemanticSearch') {
        return `Performing semantic search for: "${data.input.query || data.input}"`;
      }
      
      if (toolName === 'RevealSymbol') {
        return `Analyzing symbol: ${data.input.symbol || data.input}`;
      }
      
      // Generic format for other tools
      return `Using ${toolName} tool with input: ${JSON.stringify(data.input).substring(0, 50)}${JSON.stringify(data.input).length > 50 ? '...' : ''}`;
    }
    
    // Handle tool end events
    if (data.output) {
      if (typeof data.output === 'string') {
        return `Completed with result: ${data.output.substring(0, 50)}${data.output.length > 50 ? '...' : ''}`;
      } else {
        return `Completed with result: ${JSON.stringify(data.output).substring(0, 50)}${JSON.stringify(data.output).length > 50 ? '...' : ''}`;
      }
    }
    
    // Default case
    return `Processing: ${JSON.stringify(data).substring(0, 50)}${JSON.stringify(data).length > 50 ? '...' : ''}`;
  } catch (e) {
    // If parsing fails, return a simplified version of the original
    return logData.substring(0, 100) + (logData.length > 100 ? '...' : '');
  }
}


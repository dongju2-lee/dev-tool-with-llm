/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextResponse } from 'next/server';

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { addMcpServer, deleteMcpServer, mcpServers } from "@/utils/mcpServer";
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { EMcpServerStatus, EMcpServerType } from '@/types/mcp.type';

export async function GET() {
  try {
    return NextResponse.json({ 
      status: 'success',
      servers: mcpServers
    });
  } catch (error) {
    console.error('Server error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
    
    const { command , args , name , url , type: serverType } = await request.json();

  try {
    

    let transport;

    if (serverType === EMcpServerType.LOCAL) {
        transport = new StdioClientTransport({
            command,
            args
        });
    } else {
        transport = new SSEClientTransport(new URL(url));
    }

    const client = new Client({
      name,
      version: "1.0.0"
    });

    await client.connect(transport);
    const tools = await client.listTools();

    addMcpServer({
        id: crypto.randomUUID(),
        name,
        desc: '',
        status: EMcpServerStatus.RUNNING,
        type: serverType as EMcpServerType,
        url,
        command: command || '',
        args: args || [],
        
        tools: tools.tools,
        histories: [
            {
                message: 'MCP Server registered SUCCESS',
            }
        ],

    })
    console.log(mcpServers)
    return NextResponse.json({ 
      status: 'success',
      servers: mcpServers
    });
  } catch (error) {
    console.error('Server error:', error);

    addMcpServer({
        id: crypto.randomUUID(),
        name,
        desc: '',
        status: EMcpServerStatus.ERROR,
        type: serverType as EMcpServerType,
        url,
        command: command || '',
        args: args || [],
        
        tools: [],
        histories: [
            {
                message: 'MCP Server registered ERROR',
            }
        ],
    });

    return NextResponse.json({ 
        status: 'error',
        servers: mcpServers
    });
  }
}

export async function DELETE(request: Request) {
  const { id } = await request.json();
  deleteMcpServer(id);
  
  return NextResponse.json({ 
      status: 'success',
        servers: mcpServers
  });

}
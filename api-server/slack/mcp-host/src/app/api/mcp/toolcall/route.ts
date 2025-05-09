import { NextResponse } from 'next/server';

import { EMcpServerType } from '@/types/mcp.type';
import { mcpServers } from "@/utils/mcpServer";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

// tools call
export async function POST(request: Request) {
  try {
    const { id, toolName, toolArguments } = await request.json();
    
    const server = mcpServers.find(s => s.id === id);
    
    if (!server) {
      return NextResponse.json({ error: 'Server not found' }, { status: 404 });
    }

    console.log(toolName)
    console.log(toolArguments)

    let transport;

    if (server.type === EMcpServerType.LOCAL) {
      if (!server.command || !server.args) return NextResponse.json({ error: 'Server not found info: ' + JSON.stringify(server) }, { status: 500 });;

      transport = new StdioClientTransport({
        command: server.command,
        args: server.args,
      });
    } else {
      if (!server.url) return NextResponse.json({ error: 'Server not found info: ' + JSON.stringify(server) }, { status: 500 });;

      transport = new SSEClientTransport(new URL(server.url || ''));
    }

    const client = new Client({
      name: server.name || '',
      version: "1.0.0",
    });

    await client.connect(transport);
    
    const res = await client.callTool({
      name: toolName,
      arguments: toolArguments,
    });
    
    return NextResponse.json({ 
      result: res.content,
      status: 'success'
    });

  } catch (error) {
    console.error('Server error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

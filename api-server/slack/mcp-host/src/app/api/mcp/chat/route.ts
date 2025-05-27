/* eslint-disable @typescript-eslint/no-explicit-any */
import { EMcpServerType, TMcpServer } from "@/types/mcp.type";
import { NextResponse } from "next/server";

import { mcpServers } from "@/utils/mcpServer";
import { model, model2 } from "@/utils/model";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { MultiServerMCPClient } from "@langchain/mcp-adapters";

function getMcpServerTransport(server: TMcpServer) {
  let temp = {};
  if (server.type === EMcpServerType.LOCAL) {
    temp = {
      transport: "stdio",
      command: server.command as string,
      args: server.args as string[],
    };
  } else {
    temp = {
      transport: "sse",
      url: server.url as string,
    };
  }
  const rst = {
    [server.name]: temp,
  };

  return rst;
}

export async function POST(request: Request) {
  try {
    const { message } = await request.json();
    console.log(message);

    if (mcpServers.length === 0) {
      // MCP 서버가 없을 때 사용자에게 안내 메시지 제공
      return NextResponse.json(
        {
          result: {
            content:
              "MCP 서버가 등록되지 않았습니다. 먼저 서버를 등록해주세요.",
          },
          status: "no_server",
        },
        { status: 200 }
      ); // 200 상태 코드로 변경하여 클라이언트에서 정상적으로 처리
    }

    // 각 서버에 대한 전송 구성 생성
    const mcpServersTransport = mcpServers.map((server: TMcpServer) =>
      getMcpServerTransport(server)
    );

    // 다중 서버 MCP 클라이언트 생성
    const client = new MultiServerMCPClient({
      mcpServers: mcpServersTransport.reduce(
        (acc, curr) => ({ ...acc, ...curr }),
        {}
      ) as any,
    });

    // 서버에서 도구 가져오기
    const tools = await client.getTools();

    // 도구를 가져온 후, 이를 ReAct 에이전트에 제공
    const agent = createReactAgent({
      tools,
      llm: model2,
    });

    // 사용자 메시지가 에이전트에 전달
    const result = await agent.invoke({
      messages: [
        {
          role: "user",
          content: message,
        },
      ],
    });

    console.log(result);
    await client.close();

    // 프로세스 ID 반환
    return NextResponse.json({
      result,
      status: "started",
    });
  } catch (error) {
    console.error("Server error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
// what's (3+3) * 3 ?

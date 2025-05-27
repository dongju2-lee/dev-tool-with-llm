"use client";

import McpServerToolsInspectorView from "@/components/organisms/McpServerToolsInspectorView";
import { McpServerView } from "@/components/organisms/McpServerView";
import useMcpServers from "@/hooks/useMcpServers";
import { AgentChatView } from "../../organisms/AgentChatView";

import { useEffect } from "react";

export const HomeTemplate = () => {
  const { servers, addServer, server, clickServer, deleteServer } =
    useMcpServers();

  useEffect(() => {
    fetch("/api/recreationForest")
      .then((res) => res.json())
      .then((data) => {
        console.log(data);
      });
  }, []);

  return (
    <div className="p-3 bg-white rounded-lg">
      <h1 className="text-3xl font-bold mb-8 text-center">MCP Host</h1>

      <main className="flex items-center justify-center">
        <McpServerView
          servers={servers}
          onAddServer={addServer}
          onDeleteServer={deleteServer}
          onServerClick={clickServer}
        />
      </main>

      <main className="flex items-start justify-center mt-3 gap-3 px-3">
        <div className="w-1/2">
          <McpServerToolsInspectorView server={server} />
        </div>
        <div className="w-1/2">
          <AgentChatView />
        </div>
      </main>
    </div>
  );
};

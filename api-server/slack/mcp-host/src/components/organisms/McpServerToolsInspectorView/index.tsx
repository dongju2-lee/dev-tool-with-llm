import { useState } from "react";
import {
  EMcpServerStatus,
  EMcpServerType,
  TCallData,
  TMcpServer,
} from "../../../types/mcp.type";
import { Card } from "../../molecules/Card";
import { McpServerIndicator } from "../../molecules/McpServerIndicator";

interface McpServerToolsInspectorViewProps {
  server: TMcpServer | null;
  onStart?: () => void;
  onStop?: () => void;
  onRestart?: () => void;
}

export const McpServerToolsInspectorView = ({
  server,
  onStart,
  onStop,
  onRestart,
}: McpServerToolsInspectorViewProps) => {
  console.log("server: ", server);
  const isRunning = server?.status === EMcpServerStatus.RUNNING;
  const isError = server?.status === EMcpServerStatus.ERROR;

  const [selectTool, setSelectTool] = useState<number>(-1);
  const [callData, setCallData] = useState<TCallData>({});

  const [result, setResult] = useState<string>("");
  const handleSelectTool = (idx: number) => {
    setSelectTool(idx);
    setCallData({});
  };

  const propertyTypeProcessing = (c: { [key: string]: string | number }) => {
    const temp: { [key: string]: string | number } = {};
    const tool = server?.tools[selectTool];

    if (!tool) return callData;
    for (const key in tool.inputSchema.properties) {
      if (tool.inputSchema.properties[key].type === "string") {
        temp[key] = c[key];
      } else if (tool.inputSchema.properties[key].type === "number") {
        temp[key] = Number(c[key]);
      }
    }
    console.log(temp);
    return temp;
  };

  const handleRunTool = async () => {
    if (selectTool < 0) return;

    const tool = server?.tools[selectTool];
    console.log(tool);
    if (!tool) return;
    if (!server?.id) return;

    const res = await fetch("/api/mcp/toolcall", {
      method: "POST",
      body: JSON.stringify({
        id: server?.id,
        toolName: tool.name,
        toolArguments: propertyTypeProcessing(callData),
      }),
    });

    const data = await res.json();
    console.log(data);
    setResult(data.result);
  };

  return (
    <Card className="w-full">
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800">
            Tools Inspector
          </h3>
        </div>
      </div>

      {server && (
        <div className="space-y-4">
          {/* Server Info Header */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-800">
                {server.name}
              </h3>
              <p className="text-sm text-gray-500">
                {server.type === EMcpServerType.LOCAL
                  ? "Local Server"
                  : "SSE Server"}
              </p>
            </div>
            <McpServerIndicator status={server.status} />
          </div>

          {/* Server Details */}
          <div className="space-y-2">
            {server.type === EMcpServerType.LOCAL ? (
              <>
                <div className="text-sm">
                  <span className="font-medium">Command:</span>{" "}
                  <code className="bg-gray-100 px-2 py-1 rounded">
                    {server.command}
                  </code>
                </div>
                {server.args.length > 0 && (
                  <div className="text-sm">
                    <span className="font-medium">Arguments:</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {server.args.map((arg, index) => (
                        <code
                          key={index}
                          className="bg-gray-100 px-2 py-1 rounded text-xs"
                        >
                          {arg}
                        </code>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-sm">
                <span className="font-medium">URL:</span>{" "}
                <code className="bg-gray-100 px-2 py-1 rounded break-all">
                  {server.url}
                </code>
              </div>
            )}
          </div>

          <div className="text-sm">
            <span className="font-medium">Tools:</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {server.tools.map((tool, idx) => (
                <code
                  key={tool.name}
                  className={`px-2 py-1 rounded text-xs ${
                    selectTool === idx
                      ? "bg-blue-500 text-white"
                      : "bg-gray-100 "
                  }`}
                  onClick={() => handleSelectTool(idx)}
                >
                  {tool.name}
                </code>
              ))}
            </div>

            <span>actions</span>
            <div className="flex flex-col flex-wrap gap-2 mt-1">
              {selectTool > -1 &&
                Object.keys(
                  server.tools[selectTool].inputSchema.properties
                ).map((key: string) => (
                  <div key={key} className="flex items-center gap-2">
                    <span>{key}</span>
                    <input
                      type="text"
                      className="w-full border border-gray-300 rounded-md p-1"
                      placeholder={
                        server.tools[selectTool].inputSchema.properties[key]
                          .type
                      }
                      onChange={(e) =>
                        setCallData({ ...callData, [key]: e.target.value })
                      }
                      value={callData[key] || ""}
                    />
                  </div>
                ))}

              <div className="flex items-center gap-2 justify-end">
                <button
                  className="px-2 py-1 rounded text-xs bg-blue-500 text-white"
                  onClick={handleRunTool}
                >
                  Run
                </button>
              </div>
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex gap-3 pt-2">
            {onStart && !isRunning && (
              <button
                onClick={onStart}
                className="flex items-center gap-2 px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 text-sm"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Start
              </button>
            )}

            {onStop && isRunning && (
              <button
                onClick={onStop}
                className="flex items-center gap-2 px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 10h6v4H9z"
                  />
                </svg>
                Stop
              </button>
            )}

            {onRestart && (isRunning || isError) && (
              <button
                onClick={onRestart}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Restart
              </button>
            )}
          </div>

          {/* Logs Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700">Logs</h4>
              <button className="text-xs text-blue-500 hover:text-blue-600">
                View Result
              </button>
            </div>
            <div className="bg-gray-50 rounded p-2 h-32 overflow-y-auto">
              <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                {/* Placeholder for logs */}
                <code>{JSON.stringify(result)}</code>
              </pre>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

export default McpServerToolsInspectorView;

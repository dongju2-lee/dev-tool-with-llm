import { useState } from 'react';
import { EMcpServerType, TMcpServer } from '../../../types/mcp.type';
import { Card } from '../../molecules/Card';
import { AddServerModal } from '../AddServerModal';
import { McpServerIndicator } from '../../molecules/McpServerIndicator';
import { cn } from '@/utils/cn';

interface McpServerViewProps {
  servers: TMcpServer[];
  onAddServer: (server: Omit<TMcpServer, 'id'>) => void;
  onDeleteServer: (id: string) => void;
  onServerClick: (server: TMcpServer) => void;
}

export const McpServerView = ({ servers, onAddServer, onDeleteServer, onServerClick }: McpServerViewProps) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  const handleAddServer = (serverData: Omit<TMcpServer, 'id'>) => {
    onAddServer(serverData);
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center bg-white p-6 rounded-lg shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">MCP Servers</h2>
          <p className="text-gray-500 mt-1">Manage your MCP server instances</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className={cn(
            "px-4 py-2 bg-primary text-black rounded-md",
            "hover:bg-primary/90 transition-colors duration-200",
            "flex items-center gap-2 font-medium",
            "shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-primary/50"
          )}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Server
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {servers.map((server) => (
          <Card
            key={server.id}
            title={server.name}
            subtitle={server.type === EMcpServerType.LOCAL ? 'Local Server' : 'SSE Server'}
            className={cn(
              "hover:shadow-lg transition-all duration-200",
              "border border-gray-100 bg-white",
              "cursor-pointer transform hover:-translate-y-1"
            )}
            onClick={() => onServerClick(server)}
          >
            <div className="space-y-4">
              <McpServerIndicator status={server.status} className="mb-4" />
              
              {server.type === EMcpServerType.LOCAL ? (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center text-sm text-gray-600">
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <span className="font-medium">Command</span>
                    </div>
                    <code className="block w-full bg-gray-50 px-3 py-2 rounded-md text-sm font-mono text-gray-800">
                      {server.command}
                    </code>
                  </div>

                  {server.args.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center text-sm text-gray-600">
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                        <span className="font-medium">Arguments</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {server.args.map((arg, index) => (
                          <code
                            key={index}
                            className="bg-gray-50 px-2 py-1 rounded-md text-xs font-mono text-gray-800"
                          >
                            {arg}
                          </code>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    <div className="flex items-center text-sm text-gray-600">
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                      </svg>
                      <span className="font-medium">Tools</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {server.tools.map((tool) => (
                        <span
                          key={tool.name}
                          className="bg-primary/10 text-primary px-2 py-1 rounded-md text-xs font-medium"
                        >
                          {tool.name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center text-sm text-gray-600">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                    </svg>
                    <span className="font-medium">URL</span>
                  </div>
                  <code className="block w-full bg-gray-50 px-3 py-2 rounded-md text-sm font-mono text-gray-800 break-all">
                    {server.url}
                  </code>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteServer(server.id);
                }}
                className={cn(
                  "text-red-500 hover:text-red-600 text-sm",
                  "flex items-center gap-2 px-3 py-2 rounded-md",
                  "hover:bg-red-50 transition-colors duration-200"
                )}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete Server
              </button>
            </div>
          </Card>
        ))}
      </div>

      <AddServerModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleAddServer}
      />
    </div>
  );
};

export default McpServerView;
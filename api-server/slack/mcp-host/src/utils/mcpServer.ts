import { TMcpServer } from "@/types/mcp.type";

export let mcpServers: TMcpServer[] = [];

export const addMcpServer = (server: TMcpServer) => {
    mcpServers.push(server);
}

export const getMcpServer = (id: string) => {
    return mcpServers.find((server) => server.id === id);
}

export const deleteMcpServer = (id: string) => {
    mcpServers = mcpServers.filter((server) => server.id !== id);
}
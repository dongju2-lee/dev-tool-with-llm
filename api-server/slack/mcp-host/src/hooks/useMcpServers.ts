/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'react';
import { EMcpServerStatus, TMcpServer } from '../types/mcp.type';

export const useMcpServers = () => {
  const [servers, setServers] = useState<TMcpServer[]>([]);
  const [server, setServer] = useState<TMcpServer | null>(null);
  
  // load mcp servers from api
  useEffect(() => {
    loadMcpServers();
  }, [])

  const loadMcpServers = async () => {
    const res = await fetch('/api/mcp/registry');
    const data = await res.json();
    setServers(data.servers);
  }

  useEffect(() => {
    const isExist = servers.find((s) => s.id === server?.id)

    if (!isExist) setServer(null)

    if (servers.length <1) {
      return
    }

    const runningServers = servers
      .filter(s => s.status !== EMcpServerStatus.RUNNING)
      .filter(s => s.status !== EMcpServerStatus.ERROR);
    
    if (runningServers.length < 1) {
      return;
    }

    startServer();
  }, [servers])

  const addServer = (serverData: Omit<TMcpServer, 'id'>) => {
    const newServer: TMcpServer = {
      ...serverData,
      id: crypto.randomUUID(),
      status: EMcpServerStatus.STOPPED,
    };
    setServers((prev) => [...prev, newServer]);
  };

  const clickServer = (server: TMcpServer) => {
    setServer(server);
  };

  const deleteServer = async (id: string) => {
    if (server?.id === id) setServer(null)

    const res = await fetch('/api/mcp/registry', {
      method: 'DELETE',
      body: JSON.stringify({ id }),
    });

    const data = await res.json();
    setServers(data.servers)

    if (server?.id === id) setServer(null)
  };

  const startServer = async () => {
    console.log('startServer');
    const server = servers.slice(-1)[0];
    
    if (!server) return;
    onFetchRegistryServer(server)
  };

  const onFetchRegistryServer = async (server: TMcpServer) => {
    try {
      console.log(server)
      const res = await fetch('/api/mcp/registry', {
        method: 'POST',
        body: JSON.stringify(server),
      });

      const data = await res.json();
      console.log(data);
      setServers(data.servers)
    } catch (error) {
      console.error('Error starting registry server:', error);
    }
  };

  return {
    server,
    servers,
    addServer,
    clickServer,
    deleteServer,
  };
};

export default useMcpServers; 
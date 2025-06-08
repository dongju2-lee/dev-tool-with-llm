export interface AgentMessage {
  role: 'human' | 'assistant';
  content: string;
}

export interface AgentInput {
  messages: AgentMessage[];
}

export interface AgentResponse {
  messages: AgentMessage[];
}

export interface AgentConfig {
  configurable?: {
    thread_id?: string;
  };
}

export interface StreamChunk {
  agent?: {
    messages: AgentMessage[];
  };
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  timestamp?: Date;
}

export interface ApiChatRequest {
  content: string;
  thread_id?: string;
  model_settings?: {
    model?: string;
    timeout_seconds?: number;
  };
}

export interface ApiChatResponse {
  id: string;
  role: string;
  content: string;
  type: string;
  timestamp: string;
  metadata?: {
    thread_id?: string;
    agent_used?: string;
    tools_used?: string[];
    supervisor_reasoning?: string;
  };
}

export interface ApiSessionResponse {
  session_id: string;
  created_at: string;
}

export interface ApiHealthResponse {
  status: string;
  timestamp: string;
  version: string;
}

export interface SessionConfig {
  configurable: {
    thread_id: string;
  };
}

export interface ErrorWithResponse {
  response?: {
    status: number;
    statusText: string;
  };
  request?: any;
  message?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  message?: string;
}

export interface EnvironmentConfig {
  API_BASE_URL: string;
} 
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
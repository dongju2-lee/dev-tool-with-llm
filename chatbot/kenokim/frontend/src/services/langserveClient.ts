import config from '../config/environment';

export interface ChatRequest {
  content: string;
  thread_id?: string;
  model_settings?: {
    model?: string;
    timeout_seconds?: number;
  };
}

export interface ChatResponse {
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

export interface StreamChatRequest {
  content: string;
  thread_id?: string;
  model_settings?: {
    model?: string;
    timeout_seconds?: number;
  };
}

export interface SessionCreateResponse {
  session_id: string;
  created_at: string;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  version: string;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  private getHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
    };
  }

  // 일반 채팅
  async sendMessage(content: string, threadId?: string): Promise<ChatResponse> {
    try {
      const request: ChatRequest = {
        content,
        thread_id: threadId,
        model_settings: {
          model: "gemini-2.5-flash-preview",
          timeout_seconds: 60
        }
      };

      const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json() as ChatResponse;
    } catch (error: any) {
      console.error("Chat API error:", error);
      throw error;
    }
  }

  // 스트리밍 채팅
  async* streamMessage(content: string, threadId?: string): AsyncGenerator<string, void, unknown> {
    try {
      const request: StreamChatRequest = {
        content,
        thread_id: threadId,
        model_settings: {
          model: "gemini-2.5-flash-preview",
          timeout_seconds: 60
        }
      };

      const response = await fetch(`${this.baseUrl}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') {
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                yield parsed.content;
              }
            } catch (e) {
              console.warn('Failed to parse streaming data:', line);
            }
          }
        }
      }
    } catch (error: any) {
      console.error("Streaming API error:", error);
      throw error;
    }
  }

  // 세션 생성
  async createSession(): Promise<SessionCreateResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/sessions`, {
        method: 'POST',
        headers: this.getHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json() as SessionCreateResponse;
    } catch (error: any) {
      console.error("Session creation error:", error);
      throw error;
    }
  }

  // 세션 삭제
  async deleteSession(sessionId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: this.getHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error: any) {
      console.error("Session deletion error:", error);
      throw error;
    }
  }

  // 헬스체크
  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json() as HealthCheckResponse;
    } catch (error: any) {
      console.error("Health check error:", error);
      throw error;
    }
  }

  // 연결 테스트
  async testConnection(): Promise<boolean> {
    try {
      await this.healthCheck();
      return true;
    } catch {
      return false;
    }
  }
}

export default new ApiClient(); 
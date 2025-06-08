import { Client } from "@langchain/langgraph-sdk";
import config from '../config/environment';
import { 
  AgentMessage, 
  AgentInput, 
  AgentResponse, 
  AgentConfig, 
  StreamChunk 
} from '../types';

class LangServeClient {
  private baseUrl: string;
  private client: Client;

  constructor() {
    this.baseUrl = config.API_BASE_URL;
    this.client = this.createClient();
  }

  private createClient(): Client {
    return new Client({
      apiUrl: this.baseUrl,
    });
  }

  private getHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
    };
  }

  // 단일 응답 호출
  async invoke(input: AgentInput, config: AgentConfig = {}): Promise<AgentResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/agent/invoke`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ input, config }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json() as AgentResponse;
    } catch (error: any) {
      console.error("Agent invocation error:", error);
      throw error;
    }
  }

  // 스트리밍 응답 호출
  async* stream(input: AgentInput, config: AgentConfig = {}): AsyncGenerator<StreamChunk, void, unknown> {
    try {
      const response = await fetch(`${this.baseUrl}/agent/stream`, {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ input, config }),
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
            try {
              const data = JSON.parse(line.slice(6));
              yield data as StreamChunk;
            } catch (e) {
              console.warn('Failed to parse streaming data:', line);
            }
          }
        }
      }
    } catch (error: any) {
      console.error("Agent streaming error:", error);
      throw error;
    }
  }

  // 배치 처리
  async batch(inputs: AgentInput[], config: AgentConfig = {}): Promise<AgentResponse[]> {
    try {
      const response = await fetch(`${this.baseUrl}/agent/batch`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ inputs, config }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json() as AgentResponse[];
    } catch (error: any) {
      console.error("Agent batch error:", error);
      throw error;
    }
  }

  // 연결 테스트
  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export default new LangServeClient(); 
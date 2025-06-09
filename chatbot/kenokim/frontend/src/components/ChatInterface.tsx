import React, { useState, useRef, useEffect, FormEvent, ChangeEvent } from 'react';
import apiClient from '../services/langserveClient';
import { ChatMessage } from '../types';
import './ChatInterface.css';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  onMessagesUpdate: (messages: ChatMessage[]) => void;
  chatId: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  messages, 
  onMessagesUpdate, 
  chatId 
}) => {
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(true);
  const [threadId, setThreadId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkConnection();
    // 스레드 ID 초기화 또는 채팅 ID 사용
    if (chatId && !threadId) {
      setThreadId(chatId);
    }
  }, [chatId]);

  const checkConnection = async (): Promise<void> => {
    try {
      const connected = await apiClient.testConnection();
      setIsConnected(connected);
    } catch {
      setIsConnected(false);
    }
  };

  // 일반 응답 처리
  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!input.trim() || isLoading || isStreaming) return;

    const userMessage: ChatMessage = { 
      role: 'user', 
      content: input,
      timestamp: new Date()
    };
    const newMessages = [...messages, userMessage];
    onMessagesUpdate(newMessages);
    
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      const response = await apiClient.sendMessage(currentInput, threadId || undefined);

      const aiMessage: ChatMessage = { 
        role: 'assistant', 
        content: response.content,
        timestamp: new Date()
      };
      onMessagesUpdate([...newMessages, aiMessage]);

      // 메타데이터가 있으면 로그에 출력
      if (response.metadata) {
        console.log('Agent metadata:', {
          agent_used: response.metadata.agent_used,
          tools_used: response.metadata.tools_used,
          supervisor_reasoning: response.metadata.supervisor_reasoning
        });
      }

    } catch (error: any) {
      console.error('API Error:', error);
      let errorMessage = '죄송합니다. 오류가 발생했습니다.';
      
      if (error.message.includes('HTTP 404')) {
        errorMessage = '서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.';
      } else if (error.message.includes('HTTP 500')) {
        errorMessage = '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      }
      
      onMessagesUpdate([...newMessages, { 
        role: 'assistant', 
        content: errorMessage,
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 스트리밍 응답 처리
  const handleStreamSubmit = async (): Promise<void> => {
    if (!input.trim() || isLoading || isStreaming) return;

    const userMessage: ChatMessage = { 
      role: 'user', 
      content: input,
      timestamp: new Date()
    };
    const newMessages = [...messages, userMessage];
    onMessagesUpdate(newMessages);
    
    const currentInput = input;
    setInput('');
    setIsStreaming(true);

    // 스트리밍용 임시 메시지 추가
    const tempMessage: ChatMessage = { 
      role: 'assistant', 
      content: '', 
      isStreaming: true,
      timestamp: new Date()
    };
    const messagesWithTemp = [...newMessages, tempMessage];
    onMessagesUpdate(messagesWithTemp);

    try {
      let fullContent = '';
      const stream = apiClient.streamMessage(currentInput, threadId || undefined);

      for await (const chunk of stream) {
        fullContent += chunk;
        const updatedMessages = [...newMessages, { 
          role: 'assistant' as const, 
          content: fullContent,
          isStreaming: true,
          timestamp: new Date()
        }];
        onMessagesUpdate(updatedMessages);
      }

      // 스트리밍 완료 표시
      const finalMessages = [...newMessages, { 
        role: 'assistant' as const, 
        content: fullContent,
        isStreaming: false,
        timestamp: new Date()
      }];
      onMessagesUpdate(finalMessages);

    } catch (error: any) {
      console.error('Streaming error:', error);
      let errorMessage = '스트리밍 중 오류가 발생했습니다.';
      
      if (error.message.includes('HTTP 404')) {
        errorMessage = '스트리밍 엔드포인트를 찾을 수 없습니다. 백엔드 서버 설정을 확인해주세요.';
      }
      
      const errorMessages = [...newMessages, { 
        role: 'assistant' as const, 
        content: errorMessage,
        timestamp: new Date()
      }];
      onMessagesUpdate(errorMessages);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setInput(e.target.value);
  };

  const clearChat = (): void => {
    const welcomeMessage: ChatMessage = {
      role: 'assistant',
      content: '안녕하세요! LangGraph AI 어시스턴트입니다. 다음과 같은 업무를 도와드릴 수 있습니다:\n\n🔗 LangGraph 워크플로우 설계 및 구축\n⚡ 에이전트 시스템 개발 및 최적화\n🤖 AI 에이전트 간 협업 구성\n📊 복잡한 멀티 에이전트 아키텍처 설계\n\n무엇을 도와드릴까요?',
      timestamp: new Date()
    };
    onMessagesUpdate([welcomeMessage]);
  };

  const createNewSession = async (): Promise<void> => {
    try {
      const session = await apiClient.createSession();
      setThreadId(session.session_id);
      clearChat();
      console.log('새 세션 생성됨:', session.session_id);
    } catch (error) {
      console.error('세션 생성 실패:', error);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="header-left">
          <h1>LangGraph AI Assistant</h1>
          <div className="connection-status">
            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
          {threadId && (
            <div className="thread-info">
              <small>Thread: {threadId.substring(0, 8)}...</small>
            </div>
          )}
        </div>
        <div className="header-right">
          <button onClick={createNewSession} className="new-session-button">
            새 세션
          </button>
          <button onClick={clearChat} className="clear-button">
            채팅 지우기
          </button>
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h3>LangGraph AI 어시스턴트에 오신 것을 환영합니다!</h3>
            <p>LangGraph 워크플로우 및 에이전트 시스템을 전문적으로 지원합니다.</p>
                          <div className="feature-grid">
                <div className="feature-item">
                  <span className="feature-icon">🔗</span>
                  <div>
                    <strong>워크플로우 설계</strong>
                    <p>복잡한 LangGraph 워크플로우 구축 및 최적화</p>
                  </div>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⚡</span>
                  <div>
                    <strong>에이전트 개발</strong>
                    <p>AI 에이전트 시스템 설계 및 구현</p>
                  </div>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">🤖</span>
                  <div>
                    <strong>멀티 에이전트</strong>
                    <p>에이전트 간 협업 및 통신 구성</p>
                  </div>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">📊</span>
                  <div>
                    <strong>아키텍처 설계</strong>
                    <p>확장 가능한 에이전트 아키텍처 구축</p>
                  </div>
                </div>
              </div>
            <p><strong>예시:</strong> "LangGraph 워크플로우를 설계해줘", "멀티 에이전트 시스템을 구성하는 방법을 알려줘"</p>
          </div>
        ) : (
          messages.map((message: ChatMessage, index: number) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                <div className="message-text">
                  {message.content}
                  {message.isStreaming && <span className="streaming-indicator">▋</span>}
                </div>
                {message.timestamp && (
                  <div className="message-timestamp">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          placeholder="메시지를 입력하세요... (예: LangGraph 워크플로우 설계, 멀티 에이전트 구성)"
          disabled={isLoading || isStreaming}
          className="message-input"
        />
        <div className="button-group">
          <button 
            type="submit" 
            disabled={isLoading || isStreaming || !input.trim()}
            className="send-button"
          >
            {isLoading ? '전송 중...' : '전송'}
          </button>
          <button 
            type="button"
            onClick={handleStreamSubmit}
            disabled={isLoading || isStreaming || !input.trim()}
            className="stream-button"
          >
            {isStreaming ? '스트리밍 중...' : '스트림'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface; 
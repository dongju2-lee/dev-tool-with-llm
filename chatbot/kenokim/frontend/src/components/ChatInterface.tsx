import React, { useState, useRef, useEffect, FormEvent, ChangeEvent } from 'react';
import langserveClient from '../services/langserveClient';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkConnection();
  }, []);

  const checkConnection = async (): Promise<void> => {
    try {
      const connected = await langserveClient.testConnection();
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
      const response = await langserveClient.invoke({
        messages: [{ role: 'human', content: currentInput }]
      });

      if (response.messages && response.messages.length > 0) {
        const lastMessage = response.messages[response.messages.length - 1];
        const aiMessage: ChatMessage = { 
          role: 'assistant', 
          content: lastMessage.content,
          timestamp: new Date()
        };
        onMessagesUpdate([...newMessages, aiMessage]);
      }
    } catch (error: any) {
      console.error('Error:', error);
      const errorMessage = '죄송합니다. 오류가 발생했습니다.';
      
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
      const stream = langserveClient.stream({
        messages: [{ role: 'human', content: currentInput }]
      });

      for await (const chunk of stream) {
        if (chunk.agent && chunk.agent.messages) {
          const lastMessage = chunk.agent.messages[chunk.agent.messages.length - 1];
          if (lastMessage.content) {
            fullContent = lastMessage.content;
                         const updatedMessages = [...newMessages, { 
                role: 'assistant' as const, 
                content: fullContent,
                isStreaming: true,
                timestamp: new Date()
             }];
            onMessagesUpdate(updatedMessages);
          }
        }
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
      const errorMessage = '스트리밍 중 오류가 발생했습니다.';
      
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
      content: '안녕하세요! LangGraph Agent에 오신 것을 환영합니다. Grafana 모니터링 시스템을 도와드릴 수 있습니다. 무엇을 도와드릴까요?',
      timestamp: new Date()
    };
    onMessagesUpdate([welcomeMessage]);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="header-left">
          <h1>LangGraph Agent Chat</h1>
          <div className="connection-status">
            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <div className="header-right">
          <button onClick={clearChat} className="clear-button">
            채팅 지우기
          </button>
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h3>Grafana 모니터링 에이전트에 오신 것을 환영합니다!</h3>
            <p>다음과 같은 요청을 할 수 있습니다:</p>
            <ul>
              <li>📊 시스템 메트릭 분석 (CPU, 메모리, 디스크)</li>
              <li>📈 애플리케이션 성능 분석</li>
              <li>🖼️ 대시보드 이미지 생성</li>
              <li>🖥️ 서버 정보 조회</li>
            </ul>
            <p>무엇을 도와드릴까요?</p>
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
          placeholder="메시지를 입력하세요... (예: CPU 사용률을 확인해줘)"
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
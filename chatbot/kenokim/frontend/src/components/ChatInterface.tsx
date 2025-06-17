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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    
    // 로딩 메시지 추가
    const loadingMessage: ChatMessage = {
      role: 'assistant',
      content: '답변을 생성하고 있습니다...',
      isStreaming: true,
      timestamp: new Date()
    };
    const messagesWithLoading = [...newMessages, loadingMessage];
    onMessagesUpdate(messagesWithLoading);
    
    const currentInput = input;
    setInput('');
    // textarea 높이 리셋
    if (textareaRef.current) {
      textareaRef.current.style.height = '40px';
    }
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
    // textarea 높이 리셋
    if (textareaRef.current) {
      textareaRef.current.style.height = '40px';
    }
    setIsStreaming(true);

    // 스트리밍용 로딩 메시지 추가
    const loadingMessage: ChatMessage = { 
      role: 'assistant', 
      content: '답변을 생성하고 있습니다...', 
      isStreaming: true,
      timestamp: new Date()
    };
    const messagesWithLoading = [...newMessages, loadingMessage];
    onMessagesUpdate(messagesWithLoading);

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

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>): void => {
    setInput(e.target.value);
    
    // 자동 높이 조절
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.closest('form');
      if (form) {
        const event = new Event('submit', { cancelable: true });
        form.dispatchEvent(event);
      }
    }
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

  // 메시지 내용에서 base64 이미지를 감지하고 렌더링하는 함수
  const renderMessageContent = (content: string) => {
    // 1. 마크다운 이미지 패턴 감지 (![alt](data:image/...))
    const markdownImageRegex = /!\[([^\]]*)\]\((data:image\/[^;]+;base64,[A-Za-z0-9+/]+=*)\)/g;
    
    // 마크다운 이미지 먼저 확인
    const markdownMatches = Array.from(content.matchAll(markdownImageRegex));
    if (markdownMatches.length > 0) {
      let processedContent = content;
      const elements: (string | React.ReactElement)[] = [];
      let lastIndex = 0;

      markdownMatches.forEach((match, index) => {
        const fullMatch = match[0];
        const altText = match[1];
        const imageDataUrl = match[2];
        const matchIndex = match.index!;

        // 이미지 앞의 텍스트 추가
        if (matchIndex > lastIndex) {
          const beforeText = content.substring(lastIndex, matchIndex);
          elements.push(
            <div key={`text-${index}`}>
              {beforeText.split('\n').map((line, lineIndex) => (
                <div key={lineIndex}>{line}</div>
              ))}
            </div>
          );
        }

        // 이미지 요소 추가
        elements.push(
          <div key={`image-${index}`} className="image-container">
            <img 
              src={imageDataUrl} 
              alt={altText || "Generated dashboard"} 
              style={{ 
                maxWidth: '100%', 
                height: 'auto', 
                borderRadius: '8px', 
                margin: '10px 0',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
              }}
            />
          </div>
        );

        lastIndex = matchIndex + fullMatch.length;
      });

      // 마지막 이미지 이후의 텍스트 추가
      if (lastIndex < content.length) {
        const afterText = content.substring(lastIndex);
        elements.push(
          <div key="text-final">
            {afterText.split('\n').map((line, lineIndex) => (
              <div key={lineIndex}>{line}</div>
            ))}
          </div>
        );
      }

      return <div>{elements}</div>;
    }

    // 2. "[렌더링된 이미지 데이터]" 패턴 감지 - 새로 추가!
    // 단순하게 텍스트에서 해당 패턴을 찾고 분리하는 방식
    if (content.includes('[렌더링된 이미지 데이터]')) {
      // "[렌더링된 이미지 데이터]" 텍스트를 기준으로 분리
      const parts = content.split('[렌더링된 이미지 데이터]');
      
      if (parts.length >= 2) {
        const beforeText = parts[0];
        const afterPart = parts[1];
        
        // 두 번째 부분에서 base64 데이터 찾기
        const base64Match = afterPart.match(/([A-Za-z0-9+/]{500,}={0,2})/);
        
        if (base64Match) {
          const base64Data = base64Match[1];
          const imageDataUrl = `data:image/png;base64,${base64Data}`;
          
          // base64 데이터 이후의 텍스트 추출
          const afterImageText = afterPart.replace(base64Data, '').trim();
          
          return (
            <div>
              {/* 이미지 이전 텍스트 */}
              {beforeText && (
                <div>
                  {beforeText.split('\n').map((line, lineIndex) => (
                    <div key={lineIndex}>{line}</div>
                  ))}
                </div>
              )}
              
              {/* 이미지 */}
              <div className="image-container">
                <img 
                  src={imageDataUrl} 
                  alt="Generated dashboard" 
                  style={{ 
                    maxWidth: '100%', 
                    height: 'auto', 
                    borderRadius: '8px', 
                    margin: '10px 0',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                  }}
                />
              </div>
              
              {/* 이미지 이후 텍스트 */}
              {afterImageText && (
                <div>
                  {afterImageText.split('\n').map((line, lineIndex) => (
                    <div key={lineIndex}>{line}</div>
                  ))}
                </div>
              )}
            </div>
          );
        }
      }
    }

    // 3. data:image 형식 확인
    const dataImageRegex = /data:image\/[^;]+;base64,([A-Za-z0-9+/]+=*)/g;
    const dataImageMatches = content.match(dataImageRegex);
    if (dataImageMatches) {
      const parts = content.split(dataImageRegex);
      return (
        <div>
          {parts.map((part, index) => {
            if (dataImageMatches.includes(part)) {
              return (
                <div key={index} className="image-container">
                  <img 
                    src={part} 
                    alt="Generated dashboard" 
                    style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px', marginTop: '10px' }}
                  />
                </div>
              );
            }
            return <span key={index}>{part}</span>;
          })}
        </div>
      );
    }
    
    // 4. 단순 base64 문자열 확인 (매우 긴 문자열)
    const base64ImageRegex = /[A-Za-z0-9+/]{1000,}={0,2}/g;
    const longBase64Matches = content.match(base64ImageRegex);
    if (longBase64Matches) {
      // 가장 긴 base64 문자열을 이미지로 가정
      const longestMatch = longBase64Matches.reduce((a, b) => a.length > b.length ? a : b);
      
      const parts = content.split(longestMatch);
      const imageDataUrl = `data:image/png;base64,${longestMatch}`;
      
      return (
        <div>
          <div>{parts[0]}</div>
          <div className="image-container">
            <img 
              src={imageDataUrl} 
              alt="Generated dashboard" 
              style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px', margin: '10px 0' }}
            />
          </div>
          <div>{parts[1]}</div>
        </div>
      );
    }
    
    // 5. 일반 텍스트 처리 (줄바꿈 보존)
    return content.split('\n').map((line, index) => (
      <div key={index}>{line}</div>
    ));
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
            <div key={index} className={`message ${message.role} ${message.isStreaming ? 'streaming' : ''}`}>
              <div className="message-content">
                <div 
                  className="message-text" 
                  data-loading={message.isStreaming && message.content.includes('답변을 생성하고 있습니다') ? 'true' : 'false'}
                >
                  {renderMessageContent(message.content)}
                  {message.isStreaming && !message.content.includes('답변을 생성하고 있습니다') && <span className="streaming-indicator">▋</span>}
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
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="메시지를 입력하세요... (예: LangGraph 워크플로우 설계, 멀티 에이전트 구성) | 💡 Shift + Enter: 줄바꿈 | Enter: 전송"
          disabled={isLoading || isStreaming}
          className="message-input"
          rows={1}
          style={{
            minHeight: '40px',
            maxHeight: '120px',
            resize: 'none',
            overflow: 'auto'
          }}
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
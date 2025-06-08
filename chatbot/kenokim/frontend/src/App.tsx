import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';
import { ChatMessage } from './types';
import './App.css';

interface ChatSession {
  id: string;
  title: string;
  timestamp: Date;
  messages: ChatMessage[];
}

const App: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string>('');
  const [currentMessages, setCurrentMessages] = useState<ChatMessage[]>([]);

  // 초기 로드 시 localStorage에서 채팅 히스토리 불러오기
  useEffect(() => {
    const savedHistory = localStorage.getItem('chatHistory');
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        const historyWithDates = parsed.map((session: any) => ({
          ...session,
          timestamp: new Date(session.timestamp),
          messages: session.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        setChatHistory(historyWithDates);
        
        // 저장된 히스토리가 있으면 가장 최근 채팅으로 설정
        if (historyWithDates.length > 0) {
          const latestChat = historyWithDates[0];
          setCurrentChatId(latestChat.id);
          setCurrentMessages(latestChat.messages);
        } else {
          // 저장된 히스토리가 없으면 새 채팅 생성
          createInitialChat();
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
        createInitialChat();
      }
    } else {
      // localStorage가 비어있으면 새 채팅 생성
      createInitialChat();
    }
  }, []);

  // 초기 채팅 생성 함수
  const createInitialChat = () => {
    const newChatId = `chat_${Date.now()}`;
    const newSession: ChatSession = {
      id: newChatId,
      title: '새 채팅',
      timestamp: new Date(),
      messages: [{
        role: 'assistant',
        content: '안녕하세요! LangGraph Agent에 오신 것을 환영합니다. devops 작업을 도와줄 수 있습니다. 무엇을 도와드릴까요?',
        timestamp: new Date()
      }]
    };

    setChatHistory([newSession]);
    setCurrentChatId(newChatId);
    setCurrentMessages(newSession.messages);
  };

  // 채팅 히스토리 저장
  useEffect(() => {
    if (chatHistory.length > 0) {
      localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }
  }, [chatHistory]);

  // 사이드바 토글
  const toggleSidebar = (): void => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // 새 채팅 생성
  const handleNewChat = (): void => {
    const newChatId = `chat_${Date.now()}`;
    const newSession: ChatSession = {
      id: newChatId,
      title: '새 채팅',
      timestamp: new Date(),
      messages: [{
        role: 'assistant',
        content: '안녕하세요! LangGraph Agent에 오신 것을 환영합니다. Grafana 모니터링 시스템을 도와드릴 수 있습니다. 무엇을 도와드릴까요?',
        timestamp: new Date()
      }]
    };

    // 현재 채팅이 있고 메시지가 있다면 저장
    if (currentChatId && currentMessages.length > 1) {
      saveChatSession();
    }

    setChatHistory(prev => [newSession, ...prev]);
    setCurrentChatId(newChatId);
    setCurrentMessages(newSession.messages);
  };

  // 채팅 선택
  const handleSelectChat = (chatId: string): void => {
    // 현재 채팅 저장
    if (currentChatId && currentMessages.length > 0) {
      saveChatSession();
    }

    const selectedChat = chatHistory.find(chat => chat.id === chatId);
    if (selectedChat) {
      setCurrentChatId(chatId);
      setCurrentMessages(selectedChat.messages);
    }
  };

  // 현재 채팅 세션 저장
  const saveChatSession = (): void => {
    if (!currentChatId || currentMessages.length === 0) return;

    setChatHistory(prev => 
      prev.map(session => 
        session.id === currentChatId 
          ? { 
              ...session, 
              messages: currentMessages,
              title: generateChatTitle(currentMessages),
              timestamp: new Date()
            }
          : session
      )
    );
  };

  // 채팅 제목 생성
  const generateChatTitle = (messages: ChatMessage[]): string => {
    const firstUserMessage = messages.find(msg => msg.role === 'user');
    if (firstUserMessage && firstUserMessage.content) {
      return firstUserMessage.content.length > 30 
        ? firstUserMessage.content.substring(0, 30) + '...'
        : firstUserMessage.content;
    }
    return '새 채팅';
  };

  // 메시지 업데이트 핸들러
  const handleMessagesUpdate = (newMessages: ChatMessage[]): void => {
    setCurrentMessages(newMessages);
  };

  // 메인 콘텐츠 영역 마진 계산
  const getMainContentStyle = () => ({
    marginLeft: isSidebarOpen ? '280px' : '60px',
    transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  });

  return (
    <div className="App">
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={toggleSidebar}
        onNewChat={handleNewChat}
        chatHistory={chatHistory}
        onSelectChat={handleSelectChat}
        currentChatId={currentChatId}
      />
      
      <div className="main-content" style={getMainContentStyle()}>
        <ChatInterface
          messages={currentMessages}
          onMessagesUpdate={handleMessagesUpdate}
          chatId={currentChatId}
        />
      </div>
    </div>
  );
};

export default App;

import React, { useState } from 'react';
import { ChatMessage } from '../types';
import './Sidebar.css';

interface SidebarProps {
  onNewChat: () => void;
  chatHistory: Array<{
    id: string;
    title: string;
    timestamp: Date;
    messages: ChatMessage[];
  }>;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
  currentChatId?: string;
}

const Sidebar: React.FC<SidebarProps> = ({
  onNewChat,
  chatHistory,
  onSelectChat,
  onDeleteChat,
  currentChatId
}) => {
  const [hoveredChat, setHoveredChat] = useState<string | null>(null);

  const formatChatTitle = (messages: ChatMessage[]): string => {
    const firstUserMessage = messages.find(msg => msg.role === 'user');
    if (firstUserMessage && firstUserMessage.content) {
      return firstUserMessage.content.length > 30 
        ? firstUserMessage.content.substring(0, 30) + '...'
        : firstUserMessage.content;
    }
    return '새 채팅';
  };

  const formatTimestamp = (timestamp: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - timestamp.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return '방금 전';
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;
    return timestamp.toLocaleDateString('ko-KR');
  };

  const handleDeleteClick = (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation(); // 채팅 선택을 방지
    onDeleteChat(chatId);
  };

  return (
    <div className="sidebar open">
      {/* 헤더 */}
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">🔗</div>
          <span className="logo-text">LangGraph AI</span>
        </div>
        
        <button 
          className="new-chat-button"
          onClick={onNewChat}
          title="새 채팅 시작"
        >
          <span>+</span>
          <span className="button-text">새 채팅</span>
        </button>
      </div>

      {/* 채팅 목록 */}
      <div className="chat-list">
        {chatHistory.length === 0 ? (
          <div className="empty-chat-list">
            아직 채팅 기록이 없습니다.<br />
            새 채팅을 시작해보세요!
          </div>
        ) : (
          chatHistory.map((chat) => (
            <div
              key={chat.id}
              className={`chat-item ${currentChatId === chat.id ? 'active' : ''}`}
              onClick={() => onSelectChat(chat.id)}
              onMouseEnter={() => setHoveredChat(chat.id)}
              onMouseLeave={() => setHoveredChat(null)}
            >
              <div className="chat-content">
                <div className="chat-title">
                  {chat.title || formatChatTitle(chat.messages)}
                </div>
                <div className="chat-timestamp">
                  {formatTimestamp(chat.timestamp)}
                </div>
              </div>
              {hoveredChat === chat.id && (
                <button
                  className="delete-chat-button"
                  onClick={(e) => handleDeleteClick(e, chat.id)}
                  title="채팅 삭제"
                >
                  ×
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* 푸터 */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-content">
          <div className="footer-text">
            LangGraph 전문<br />
            AI 어시스턴트
          </div>
          <div className="footer-version">
            v1.0.0
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar; 
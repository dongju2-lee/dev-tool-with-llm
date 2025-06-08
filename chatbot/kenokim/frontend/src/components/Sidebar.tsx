import React, { useState } from 'react';
import { ChatMessage } from '../types';
import './Sidebar.css';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  chatHistory: Array<{
    id: string;
    title: string;
    timestamp: Date;
    messages: ChatMessage[];
  }>;
  onSelectChat: (chatId: string) => void;
  currentChatId?: string;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onToggle,
  onNewChat,
  chatHistory,
  onSelectChat,
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

  return (
    <>
      {/* 사이드바 오버레이 (모바일용) */}
      {isOpen && (
        <div 
          className="sidebar-overlay"
          onClick={onToggle}
        />
      )}
      
      {/* 사이드바 */}
      <div className={`sidebar ${isOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        {/* 헤더 */}
        <div className="sidebar-header">
          <button 
            className="sidebar-toggle-btn"
            onClick={onToggle}
            aria-label="사이드바 토글"
          >
            <span className="hamburger-icon">
              <span></span>
              <span></span>
              <span></span>
            </span>
          </button>
          
          {isOpen && (
            <button 
              className="new-chat-btn"
              onClick={onNewChat}
            >
              <span className="plus-icon">+</span>
              새 채팅
            </button>
          )}
        </div>

        {/* 채팅 히스토리 */}
        {isOpen && (
          <div className="sidebar-content">
            <div className="chat-history-section">
              <h3 className="section-title">채팅 기록</h3>
              
              {chatHistory.length === 0 ? (
                <div className="empty-history">
                  <p>채팅 기록이 없습니다</p>
                  <span>새 채팅을 시작해보세요!</span>
                </div>
              ) : (
                <div className="chat-history-list">
                  {chatHistory.map((chat) => (
                    <div
                      key={chat.id}
                      className={`chat-history-item ${
                        currentChatId === chat.id ? 'active' : ''
                      }`}
                      onClick={() => onSelectChat(chat.id)}
                      onMouseEnter={() => setHoveredChat(chat.id)}
                      onMouseLeave={() => setHoveredChat(null)}
                    >
                      <div className="chat-title">
                        {chat.title || formatChatTitle(chat.messages)}
                      </div>
                      <div className="chat-timestamp">
                        {formatTimestamp(chat.timestamp)}
                      </div>
                      
                      {hoveredChat === chat.id && (
                        <div className="chat-actions">
                          <button 
                            className="delete-chat-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              // TODO: 삭제 기능 구현
                            }}
                            aria-label="채팅 삭제"
                          >
                            🗑️
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 하단 메뉴 */}
            <div className="sidebar-footer">
              <div className="footer-menu">
                <button className="footer-menu-item">
                  <span className="menu-icon">⚙️</span>
                  설정
                </button>
                <button className="footer-menu-item">
                  <span className="menu-icon">ℹ️</span>
                  정보
                </button>
                <button className="footer-menu-item">
                  <span className="menu-icon">📖</span>
                  도움말
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default Sidebar; 
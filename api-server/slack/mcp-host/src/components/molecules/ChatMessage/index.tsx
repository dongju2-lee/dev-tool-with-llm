import './style.css';
import { ReactNode, useState, useEffect } from 'react';

interface ChatMessageProps {
  children: ReactNode;
  isLoading?: boolean;
}

const ChatMessage = ({ children, isLoading = false }: ChatMessageProps) => {
  const [displayText, setDisplayText] = useState<string>('');

  useEffect(() => {
    if (isLoading) {
      setDisplayText('Generating');
    } else {
      setDisplayText(children as string);
    }
  }, [children, isLoading]);

  return (
    <span className={`inline-block px-3 py-2 rounded-lg bg-gray-200 text-gray-800 ${isLoading ? 'loading-dots' : ''}`}>
      { displayText}
    </span>
  );
};

export default ChatMessage;
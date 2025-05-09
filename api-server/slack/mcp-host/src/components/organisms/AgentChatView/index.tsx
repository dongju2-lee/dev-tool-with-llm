/* eslint-disable @typescript-eslint/no-explicit-any */
import ChatMessage from "@/components/molecules/ChatMessage";
import { useState } from "react";

interface Message {
  text: string;
  type: "user" | "AIMessage" | "ToolMessage";
}

export const AgentChatView = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (input.trim()) {
      setMessages((prev) => [...prev, { text: input, type: "user" }]);
      setInput("");
      setIsLoading(true);

      const res = await fetch("/api/mcp/chat", {
        method: "POST",
        body: JSON.stringify({ message: input }),
      });

      const data = await res.json();
      console.log("API 응답:", data); // 디버깅용

      // 안전하게 messages 접근
      if (data.result && data.result.messages) {
        data.result.messages.slice(1).forEach((message: any) => {
          if (message.kwargs && message.kwargs.content) {
            setMessages((prev) => [
              ...prev,
              {
                text: `[tools] ${message.kwargs.content}`,
                type: message.id.slice(-1)[0],
              },
            ]);
          }
        });
      } else {
        // messages가 없는 경우의 처리
        // 결과를 직접 메시지로 변환
        setMessages((prev) => [
          ...prev,
          {
            text: data.result?.content || JSON.stringify(data.result),
            type: "AIMessage",
          },
        ]);
      }

      setIsLoading(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      handleSend();
    }
  };

  return (
    <div className="p-4 bg-white rounded shadow-md">
      <div className="h-64 overflow-y-auto mb-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`mb-2 flex ${
              msg.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <ChatMessage>
              {msg.type === "ToolMessage" ? (
                <div dangerouslySetInnerHTML={{ __html: msg.text }}></div>
              ) : (
                msg.text
              )}
            </ChatMessage>
          </div>
        ))}

        {isLoading && (
          <div className="mb-2 flex justify-start">
            <ChatMessage isLoading={true}>Generating...</ChatMessage>
          </div>
        )}
      </div>
      <div className="flex">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          className="flex-grow p-2 border rounded-l focus:outline-none"
          placeholder="Type a message..."
        />
        <button
          onClick={handleSend}
          className="p-2 bg-blue-500 text-white rounded-r hover:bg-blue-600"
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default AgentChatView;

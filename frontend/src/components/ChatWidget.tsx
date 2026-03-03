import React, { useState, useRef, useEffect } from 'react';
import { Send, Minimize2, X } from 'lucide-react';
import { sendChatMessage } from '../lib/botApi';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface ChatWidgetProps {
  botId: string;
  botName?: string;
  companyName?: string;
  isPreview?: boolean;
  onToggleMinimize?: () => void;
  onClose?: () => void;
  className?: string;
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({
  botId,
  botName = 'AI Assistant',
  companyName = 'Chatbot',
  isPreview = false,
  onToggleMinimize,
  onClose,
  className
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: `Hello! I'm your AI assistant. How can I help you today?`,
      sender: 'bot',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      if (isPreview) {
        setTimeout(() => {
          const previewResponse: Message = {
            id: (Date.now() + 1).toString(),
            text: 'This is a preview response. In production, this bot will answer based on your uploaded documents.',
            sender: 'bot',
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, previewResponse]);
          setIsTyping(false);
        }, 1000);
      } else {
        const response = await sendChatMessage(botId, userMessage.text);
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: response.response,
          sender: 'bot',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, botMessage]);
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-xl overflow-hidden flex flex-col ${className || 'h-[600px]'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <div>
            <div className="text-sm font-medium text-gray-900">{botName}</div>
            <div className="text-xs text-gray-500">{companyName}</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {onToggleMinimize && (
            <button
              onClick={onToggleMinimize}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
            >
              <Minimize2 className="w-4 h-4 text-gray-400" />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3.5 py-2.5 ${message.sender === 'user'
                ? 'bg-gray-900 text-white'
                : 'bg-white border border-gray-200 text-gray-900'
                }`}
            >
              {message.sender === 'bot' ? (
                <div className="text-sm leading-relaxed chat-markdown">
                  <ReactMarkdown>{message.text}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.text}</p>
              )}
              <span className={`text-[10px] mt-1.5 block ${message.sender === 'user' ? 'text-gray-400' : 'text-gray-400'
                }`}>
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg px-3.5 py-2.5">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-200 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message…"
            className="flex-1 input-field"
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim()}
            className="btn-primary px-3"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
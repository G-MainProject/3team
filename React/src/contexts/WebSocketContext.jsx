import { createContext, useContext, useEffect, useRef, useState } from 'react';
import SockJS from 'sockjs-client';
import { Client } from '@stomp/stompjs';

const WebSocketContext = createContext();

const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const isConnecting = useRef(false);

  useEffect(() => {
    const connect = () => {
      // 이미 연결 중이거나 연결된 경우 중복 연결 방지
      if (isConnecting.current || isConnected) {
        return;
      }
      
      isConnecting.current = true;
      
      try {
        // STOMP 클라이언트 생성
        const stompClient = new Client({
          webSocketFactory: () => new SockJS('http://localhost:8080/ws'),
          debug: (str) => {
            // 중요한 메시지만 로그 출력
            if (str.includes('CONNECTED') || str.includes('ERROR') || str.includes('DISCONNECTED')) {
              console.log('STOMP:', str);
            }
          },
          reconnectDelay: 5000,
          heartbeatIncoming: 4000,
          heartbeatOutgoing: 4000,
        });

        stompClient.onConnect = () => {
          setIsConnected(true);
          socketRef.current = stompClient;
          reconnectAttempts.current = 0;
          isConnecting.current = false;
        };

        stompClient.onStompError = (frame) => {
          console.error('❌ STOMP 오류:', frame.headers['message']);
          console.error('❌ 세부사항:', frame.body);
          setIsConnected(false);
          isConnecting.current = false;
        };

        stompClient.onWebSocketClose = () => {
          setIsConnected(false);
          socketRef.current = null;
          isConnecting.current = false;

          // 자동 재연결 시도
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 지수 백오프
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttempts.current++;
              connect();
            }, delay);
          }
        };

        stompClient.onWebSocketError = () => {
          setIsConnected(false);
          isConnecting.current = false;
        };

        // 연결 시작
        stompClient.activate();

      } catch {
        setIsConnected(false);
        isConnecting.current = false;
      }
    };

    // 컴포넌트 마운트 시에만 연결 시도
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.deactivate();
      }
    };
  }, []); // 의존성 배열 제거 - 컴포넌트 마운트 시에만 실행

  const sendMessage = (destination, message) => {
    if (socketRef.current && isConnected) {
      socketRef.current.publish({ destination, body: JSON.stringify(message) });
    }
  };

  const subscribe = (destination, callback) => {
    if (socketRef.current && isConnected) {
      return socketRef.current.subscribe(destination, callback);
    }
    return null;
  };

  const value = {
    socket: socketRef.current,
    isConnected,
    sendMessage,
    subscribe
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export { useWebSocketContext };

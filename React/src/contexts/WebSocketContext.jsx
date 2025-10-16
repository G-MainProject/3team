import { useEffect, useRef, useState } from 'react';
import SockJS from 'sockjs-client';
import { Client } from '@stomp/stompjs';
import { WebSocketContext } from './WebSocketContext';


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
        const wsUrl = import.meta.env.VITE_WS_URL || 
          (window.location.hostname.includes('devtunnels.ms')
            ? `${window.location.protocol}//${window.location.hostname}/ws`  // Dev Tunnels: 포트 번호 제거
            : window.location.protocol === 'https:' 
              ? `https://${window.location.hostname}:8080/ws`
              : `http://${window.location.hostname}:8080/ws`);
        
        const stompClient = new Client({
          webSocketFactory: () => new SockJS(wsUrl),
          debug: () => {
            // STOMP 메시지 처리 (디버깅 로그 제거됨)
          },
          reconnectDelay: 10000, // 재연결 지연 시간 증가 (10초)
          heartbeatIncoming: 0, // 하트비트 비활성화
          heartbeatOutgoing: 0, // 하트비트 비활성화
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

          // 자동 재연결 시도 (더 보수적으로)
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.min(Math.pow(2, reconnectAttempts.current) * 2000, 30000); // 최대 30초
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
  }, []); // 의존성 배열 비우기 - 마운트 시에만 실행

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

export default WebSocketProvider;

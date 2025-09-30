import { useEffect, useRef, useState } from 'react';
import SockJS from 'sockjs-client';
import { Client } from '@stomp/stompjs';

export const useWebSocket = (url, options = {}) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = options.maxReconnectAttempts || 5;
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
          webSocketFactory: () => new SockJS(url),
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

        stompClient.onConnect = (frame) => {
          console.log('🔌 WebSocket 연결 성공:', url);
          setIsConnected(true);
          setSocket(stompClient);
          reconnectAttempts.current = 0;
          isConnecting.current = false;
        };

        stompClient.onStompError = (frame) => {
          console.error('❌ STOMP 오류:', frame.headers['message']);
          console.error('❌ 세부사항:', frame.body);
          setIsConnected(false);
          isConnecting.current = false;
        };

        stompClient.onWebSocketClose = (event) => {
          console.log('🔌 WebSocket 연결 종료:', event.code, event.reason);
          setIsConnected(false);
          setSocket(null);
          isConnecting.current = false;

          // 자동 재연결 시도
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 지수 백오프
            console.log(`🔄 WebSocket 재연결 시도 ${reconnectAttempts.current + 1}/${maxReconnectAttempts} (${delay}ms 후)`);
            
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttempts.current++;
              connect();
            }, delay);
          } else {
            console.error('❌ WebSocket 최대 재연결 시도 횟수 초과');
          }
        };

        stompClient.onWebSocketError = (error) => {
          console.error('❌ WebSocket 오류:', error);
          setIsConnected(false);
          isConnecting.current = false;
        };

        // 연결 시작
        stompClient.activate();

      } catch (error) {
        console.error('❌ WebSocket 연결 실패:', error);
        setIsConnected(false);
        isConnecting.current = false;
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socket) {
        socket.deactivate();
      }
    };
  }, [url, maxReconnectAttempts]);

  const sendMessage = (destination, message) => {
    if (socket && isConnected) {
      socket.publish({ destination, body: JSON.stringify(message) });
    } else {
      console.warn('WebSocket이 연결되지 않았습니다.');
    }
  };

  const subscribe = (destination, callback) => {
    if (socket && isConnected) {
      return socket.subscribe(destination, callback);
    } else {
      console.warn('WebSocket이 연결되지 않았습니다.');
      return null;
    }
  };

  return {
    socket,
    isConnected,
    lastMessage,
    sendMessage,
    subscribe
  };
};

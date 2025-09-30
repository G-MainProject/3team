import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';
import { useWebSocket } from './useWebSocket';

// 통합된 실시간 주식 데이터를 관리하는 커스텀 훅
export const useRealtimeStockData = (symbol = '005930') => {
  const [stockData, setStockData] = useState([]);
  const [volumeData, setVolumeData] = useState([]);
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [lastTradeTime, setLastTradeTime] = useState(null);
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);

  // 통합 데이터 로드 함수
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 통합 API 사용 (주가, 거래량, 요약 정보를 한 번에)
      const unifiedResponse = await apiService.getUnifiedStockData(symbol, '1m');

      // 통합 API 응답 구조 처리 (CachedDataResponse 구조)
      if (unifiedResponse.success && unifiedResponse.data) {
        const responseData = unifiedResponse.data;
        const unifiedData = responseData.data || responseData; // CachedDataResponse 또는 직접 데이터
        
        setStockData(unifiedData.stockData || []);
        setVolumeData(unifiedData.volumeData || []);
        setSummaryData(unifiedData.summary || null);
        
        // 실제 거래 마지막 시간 추출 (차트 데이터의 마지막 시간)
        if (unifiedData.stockData && unifiedData.stockData.length > 0) {
          const lastStockItem = unifiedData.stockData[unifiedData.stockData.length - 1];
          if (lastStockItem && lastStockItem.time) {
            // HH:mm 형식의 시간을 오늘 날짜와 결합
            const today = new Date();
            const [hours, minutes] = lastStockItem.time.split(':').map(Number);
            const lastTradeDateTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
            setLastTradeTime(lastTradeDateTime);
          }
        }
        
        // 장중/장마감 상태에 따라 적절한 시간 설정
        const currentTime = new Date();
        
        // 한국 시간대를 올바르게 계산
        const koreaTime = new Date(currentTime.toLocaleString("en-US", {timeZone: "Asia/Seoul"}));
        const hour = koreaTime.getHours();
        const minute = koreaTime.getMinutes();
        const day = koreaTime.getDay(); // 0=일요일, 6=토요일
        
        // 주말이면 장마감
        const isWeekend = day === 0 || day === 6;
        
        // 평일 15:30 이후면 장마감 (현재 시간 기준으로 판단)
        const isAfterClose = hour > 15 || (hour === 15 && minute >= 30);
        
        if (isWeekend || isAfterClose) {
          // 장마감 후: 실제 거래 마지막 시간 사용
          setLastUpdate(null); // lastUpdate는 null로 설정
        } else {
          // 장중 또는 장 시작 전: 현재 시간을 lastUpdate로 설정
          setLastUpdate(currentTime);
        }
      } else {
        console.warn('⚠️ 통합 API 응답 실패 또는 데이터 없음');
        // 503 에러인 경우 빈 데이터로 설정 (스케줄러가 데이터를 준비 중)
        if (unifiedResponse.status === 503) {
          console.log('📊 주식 데이터를 준비 중입니다. 잠시 후 다시 시도해주세요.');
        }
        setStockData([]);
        setVolumeData([]);
        setSummaryData(null);
      }
    } catch (err) {
      console.error('[useRealtimeStockData] 데이터 로드 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  // WebSocket 연결 설정
  const { isConnected: wsConnected, subscribe } = useWebSocket(
    `http://localhost:8080/ws`,
    { maxReconnectAttempts: 5 }
  );

  // WebSocket 연결 상태 업데이트
  useEffect(() => {
    setIsWebSocketConnected(wsConnected);
  }, [wsConnected]);

  // WebSocket 구독 설정
  useEffect(() => {
    if (wsConnected && subscribe) {
      console.log('📡 WebSocket 구독 시작:', `/topic/stock/${symbol}`);
      
      const subscription = subscribe(`/topic/stock/${symbol}`, (message) => {
        try {
          const data = JSON.parse(message.body);
          console.log('📨 WebSocket 실시간 데이터 수신:', data);
          
          // 실시간 데이터 업데이트
          setStockData(data.stockData || []);
          setVolumeData(data.volumeData || []);
          setSummaryData(data.summary || null);
          setLastUpdate(new Date());
          setError(null);
        } catch (error) {
          console.error('WebSocket 메시지 파싱 오류:', error);
        }
      });

      return () => {
        if (subscription) {
          subscription.unsubscribe();
        }
      };
    }
  }, [wsConnected, subscribe, symbol]);

  // 초기 데이터 로드
  useEffect(() => {
    loadData();
  }, [symbol, loadData]);

  // WebSocket이 연결되지 않은 경우에만 폴링 사용
  useEffect(() => {
    const interval = setInterval(() => {
      if (!wsConnected) {
        console.log('🔄 WebSocket 미연결 - 폴링으로 데이터 갱신');
        loadData();
      }
    }, 60000); // 1분마다

    return () => clearInterval(interval);
  }, [loadData, wsConnected]);

  // 수동 새로고침 함수
  const refreshData = useCallback(() => {
    loadData();
  }, [loadData]); // loadData를 의존성으로 사용

  return {
    stockData,
    volumeData,
    summaryData,
    loading,
    error,
    lastUpdate,
    lastTradeTime,
    isWebSocketConnected,
    refreshData,
  };
};

// useStockSummary 훅 제거됨 - useRealtimeStockData의 summaryData로 대체

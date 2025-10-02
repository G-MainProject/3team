import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../services/api';
import { useWebSocketContext } from '../contexts/WebSocketContext';

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
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 데이터 기반으로 lastUpdate 설정하는 헬퍼 함수
  const setLastUpdateFromData = useCallback((stockData) => {
    if (stockData && stockData.length > 0) {
      const lastStockItem = stockData[stockData.length - 1];
      if (lastStockItem && lastStockItem.timestamp) {
        // timestamp가 있으면 해당 시간 사용 (가장 정확)
        setLastUpdate(new Date(lastStockItem.timestamp));
      } else if (lastStockItem && lastStockItem.time) {
        // time만 있으면 오늘 날짜와 결합하여 사용
        const today = new Date();
        const [hours, minutes] = lastStockItem.time.split(':').map(Number);
        const dataUpdateTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
        setLastUpdate(dataUpdateTime);
      } else {
        // 시간 정보가 없으면 null로 설정 (새로고침 시간 사용 안함)
        setLastUpdate(null);
      }
    } else {
      setLastUpdate(null);
    }
  }, []);

  // 통합 데이터 로드 함수
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setIsRefreshing(true);

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
        
        // 데이터 기반으로 lastUpdate 설정 (장마감 로직 무시)
        setLastUpdateFromData(unifiedData.stockData);
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
      setIsRefreshing(false);
    }
  }, [symbol, setLastUpdateFromData]);

  // 전역 WebSocket 연결 사용
  const { isConnected: wsConnected, subscribe } = useWebSocketContext();

  // WebSocket 연결 상태 업데이트
  useEffect(() => {
    setIsWebSocketConnected(wsConnected);
  }, [wsConnected]);

  // WebSocket 구독 설정 (중복 구독 방지)
  const subscriptionRef = useRef(null);
  const currentSymbolRef = useRef(null);
  
  useEffect(() => {
    if (wsConnected && subscribe) {
      // 심볼이 변경되었거나 구독이 없을 때만 새로 구독
      if (currentSymbolRef.current !== symbol || !subscriptionRef.current) {
        // 기존 구독이 있으면 먼저 해제
        if (subscriptionRef.current) {
          subscriptionRef.current.unsubscribe();
          subscriptionRef.current = null;
        }
        
        
        const subscription = subscribe(`/topic/stock/${symbol}`, (message) => {
          try {
            // WebSocket 데이터 수신 시 갱신 중 상태 시작
            setIsRefreshing(true);
            
            const data = JSON.parse(message.body);
            
            // 실시간 데이터 업데이트
            setStockData(data.stockData || []);
            setVolumeData(data.volumeData || []);
            setSummaryData(data.summary || null);
            
            // 데이터 기반으로 lastUpdate 설정
            setLastUpdateFromData(data.stockData);
            
            setError(null);
            setLoading(false);
            
            // 갱신 완료 후 약간의 지연을 두고 갱신 중 상태 해제
            setTimeout(() => {
              setIsRefreshing(false);
            }, 1000); // 1초 후 갱신 중 상태 해제
          } catch (error) {
            console.error('WebSocket 메시지 파싱 오류:', error);
            setIsRefreshing(false);
          }
        });

        subscriptionRef.current = subscription;
        currentSymbolRef.current = symbol;
      }

      return () => {
        if (subscriptionRef.current) {
          subscriptionRef.current.unsubscribe();
          subscriptionRef.current = null;
        }
      };
    }
  }, [wsConnected, subscribe, symbol, setLastUpdateFromData]);

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
    isRefreshing,
    refreshData,
  };
};

// useStockSummary 훅 제거됨 - useRealtimeStockData의 summaryData로 대체

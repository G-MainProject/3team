import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../services/api';
import { useWebSocketContext } from './useWebSocketContext';

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

  // 데이터 기반으로 lastUpdate 설정하는 헬퍼 함수 (주식 데이터 우선)
  const setLastUpdateFromData = useCallback((stockData, volumeData = null) => {
    // 주식 데이터를 우선으로 하되, 없으면 거래량 데이터 사용
    let latestItem = null;
    let latestTime = null;
    
    // 주식 데이터에서 최신 시간 찾기 (우선순위 1)
    if (stockData && stockData.length > 0) {
      const lastStockItem = stockData[stockData.length - 1];
      if (lastStockItem) {
        let stockTime = null;
        if (lastStockItem.timestamp) {
          stockTime = new Date(lastStockItem.timestamp);
        } else if (lastStockItem.time) {
          const today = new Date();
          const [hours, minutes] = lastStockItem.time.split(':').map(Number);
          stockTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
        }
        
        if (stockTime) {
          latestTime = stockTime;
          latestItem = lastStockItem;
        }
      }
    }
    
    // 주식 데이터가 없으면 거래량 데이터에서 최신 시간 찾기 (우선순위 2)
    if (!latestTime && volumeData && volumeData.length > 0) {
      const lastVolumeItem = volumeData[volumeData.length - 1];
      if (lastVolumeItem) {
        let volumeTime = null;
        if (lastVolumeItem.timestamp) {
          volumeTime = new Date(lastVolumeItem.timestamp);
        } else if (lastVolumeItem.time) {
          const today = new Date();
          const [hours, minutes] = lastVolumeItem.time.split(':').map(Number);
          volumeTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
        }
        
        if (volumeTime) {
          latestTime = volumeTime;
          latestItem = lastVolumeItem;
        }
      }
    }
    
    // lastUpdate 설정
    if (latestTime) {
      setLastUpdate(latestTime);
    } else {
      setLastUpdate(null);
    }
    
    // lastTradeTime 설정 (주식 데이터의 마지막 거래 시간 우선)
    if (latestItem && latestItem.marketCloseTime) {
      const marketCloseTime = new Date(latestItem.marketCloseTime);
      setLastTradeTime(marketCloseTime);
    } else if (latestTime) {
      setLastTradeTime(latestTime);
    } else {
      setLastTradeTime(null);
    }
  }, []);

  // 통합 데이터 로드 함수
  const loadData = useCallback(async (interval = '1m') => {
    try {
      setLoading(true);
      setError(null);
      setIsRefreshing(true);

      // 통합 API 사용 (주가, 거래량, 요약 정보를 한 번에)
      const unifiedResponse = await apiService.getUnifiedStockData(symbol, interval);

      // 통합 API 응답 구조 처리 (CachedDataResponse 구조)
      if (unifiedResponse.success && unifiedResponse.data) {
        const responseData = unifiedResponse.data;
        const unifiedData = responseData.data || responseData; // CachedDataResponse 또는 직접 데이터
        
        setStockData(unifiedData.stockData || []);
        setVolumeData(unifiedData.volumeData || []);
        setSummaryData(unifiedData.summary || null);
        
        // 실제 거래 마지막 시간 추출 (timestamp 우선 사용)
        if (unifiedData.stockData && unifiedData.stockData.length > 0) {
          const lastStockItem = unifiedData.stockData[unifiedData.stockData.length - 1];
          
          let lastTradeDateTime = null;
          
          // timestamp가 있으면 우선 사용 (더 정확)
          if (lastStockItem && lastStockItem.timestamp) {
            lastTradeDateTime = new Date(lastStockItem.timestamp);
          } else if (lastStockItem && lastStockItem.time) {
            // timestamp가 없으면 time 사용
            const today = new Date();
            const [hours, minutes] = lastStockItem.time.split(':').map(Number);
            lastTradeDateTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
          }
          
          if (lastTradeDateTime) {
            setLastTradeTime(lastTradeDateTime);
          }
        }
        
        // 데이터 기반으로 lastUpdate 설정 (장마감 로직 무시)
        setLastUpdateFromData(unifiedData.stockData, unifiedData.volumeData);
      } else {
        // 503 에러인 경우 빈 데이터로 설정 (스케줄러가 데이터를 준비 중)
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

  // 장마감 상태 관리
  const [isMarketClosed, setIsMarketClosed] = useState(false);
  const [wasMarketClosed, setWasMarketClosed] = useState(false);

  // WebSocket 구독 설정 (중복 구독 방지, 장마감 시 제외)
  const subscriptionRef = useRef(null);
  const currentSymbolRef = useRef(null);
  
  useEffect(() => {
    if (wsConnected && subscribe && !isMarketClosed) {
      // 심볼이 변경되었거나 구독이 없을 때만 새로 구독
      if (currentSymbolRef.current !== symbol || !subscriptionRef.current) {
        // 기존 구독이 있으면 먼저 해제
        if (subscriptionRef.current) {
          subscriptionRef.current.unsubscribe();
          subscriptionRef.current = null;
        }
        
        const subscription = subscribe(`/topic/stock/${symbol}`, (message) => {
          try {
            // 장마감 상태 재확인 (구독 중에 장이 마감될 수 있음)
            if (isMarketClosed) {
              return;
            }
            
            // WebSocket 데이터 수신 시 갱신 중 상태 시작
            setIsRefreshing(true);
            
            const data = JSON.parse(message.body);
            
            // 실시간 데이터 업데이트
            setStockData(data.stockData || []);
            setVolumeData(data.volumeData || []);
            setSummaryData(data.summary || null);
            
            // 데이터 기반으로 lastUpdate 설정
            setLastUpdateFromData(data.stockData, data.volumeData);
            
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
    } else if (isMarketClosed) {
      // 장마감 시 기존 구독 해제
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
    }
  }, [wsConnected, subscribe, symbol, setLastUpdateFromData, isMarketClosed]);

  // 초기 데이터 로드
  useEffect(() => {
    loadData();
  }, [symbol, loadData]);

  // 장마감 상태 확인 함수 (각 주식의 실제 마지막 거래 시간 기준)
  const checkMarketStatus = useCallback(() => {
    const now = new Date();
    const day = now.getDay(); // 0=일요일, 6=토요일
    
    // 주말이면 장마감
    if (day === 0 || day === 6) {
      return true;
    }
    
    // 각 주식의 실제 마지막 거래 시간을 기준으로 판단
    if (stockData && stockData.length > 0) {
      const lastStockItem = stockData[stockData.length - 1];
      
      if (lastStockItem) {
        // API에서 가져온 장마감 시간이 있으면 그 기준으로 판단
        if (lastStockItem.marketCloseTime) {
          const marketCloseTime = new Date(lastStockItem.marketCloseTime);
          return now >= marketCloseTime;
        }
        
        // 장마감 시간이 없으면 해당 주식의 마지막 거래 시간 기준으로 판단
        if (lastStockItem.timestamp) {
          const lastTradeTime = new Date(lastStockItem.timestamp);
          // 해당 주식의 마지막 거래 시간이 현재 시간보다 30분 이상 지났으면 장마감으로 판단
          const timeDiff = now.getTime() - lastTradeTime.getTime();
          return timeDiff > 30 * 60 * 1000; // 30분
        }
      }
    }
    
    // 데이터가 없으면 현재 시간 기준으로 판단 (15:30)
    const hour = now.getHours();
    const minute = now.getMinutes();
    return hour > 15 || (hour === 15 && minute >= 30);
  }, [stockData]);

  // 장마감 상태 업데이트
  useEffect(() => {
    const currentMarketStatus = checkMarketStatus();
    setIsMarketClosed(currentMarketStatus);
    
    // 장이 마감에서 시작으로 변경된 경우 (다음날 장 시작)
    if (wasMarketClosed && !currentMarketStatus) {
      loadData(); // 즉시 데이터 갱신
    }
    
    setWasMarketClosed(currentMarketStatus);
  }, [checkMarketStatus, wasMarketClosed, loadData]);

  // WebSocket이 연결되지 않은 경우에만 폴링 사용 (장마감 시 제외)
  useEffect(() => {
    const interval = setInterval(() => {
      if (!wsConnected && !isMarketClosed) {
        loadData();
      }
    }, 60000); // 1분마다

    return () => clearInterval(interval);
  }, [loadData, wsConnected, isMarketClosed]);

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
    isMarketClosed,
    refreshData,
  };
};

// useStockSummary 훅 제거됨 - useRealtimeStockData의 summaryData로 대체

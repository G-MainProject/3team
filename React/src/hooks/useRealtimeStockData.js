import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

// 통합된 실시간 주식 데이터를 관리하는 커스텀 훅
export const useRealtimeStockData = (symbol = '005930') => {
  const [stockData, setStockData] = useState([]);
  const [volumeData, setVolumeData] = useState([]);
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [lastTradeTime, setLastTradeTime] = useState(null); // 실제 거래 마지막 시간

  // 통합 데이터 로드 함수
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 통합 API 사용 (주가, 거래량, 요약 정보를 한 번에)
      const [stockResponse, volumeResponse, summaryResponse] = await Promise.all([
        apiService.getRealtimeStockData(symbol),
        apiService.getVolumeData(symbol),
        apiService.getStockSummary(symbol)
      ]);

      // 새로운 API 응답 구조 처리
      const stockResult = stockResponse.success ? stockResponse.data.data : [];
      const volumeResult = volumeResponse.success ? volumeResponse.data.data : [];
      const summaryResult = summaryResponse.success ? summaryResponse.data.data : null;

      // 캐시 메타데이터에서 lastUpdate 시간 추출
      let cacheLastUpdate = null;
      if (stockResponse.success && stockResponse.data.metadata) {
        cacheLastUpdate = new Date(stockResponse.data.metadata.lastUpdated);
      } else if (volumeResponse.success && volumeResponse.data.metadata) {
        cacheLastUpdate = new Date(volumeResponse.data.metadata.lastUpdated);
      } else if (summaryResponse.success && summaryResponse.data.metadata) {
        cacheLastUpdate = new Date(summaryResponse.data.metadata.lastUpdated);
      }

      setStockData(stockResult);
      setVolumeData(volumeResult);
      setSummaryData(summaryResult);
      
      // 실제 거래 마지막 시간 추출 (차트 데이터의 마지막 시간)
      if (stockResult && stockResult.length > 0) {
        const lastStockItem = stockResult[stockResult.length - 1];
        if (lastStockItem && lastStockItem.time) {
          // HH:mm 형식의 시간을 오늘 날짜와 결합
          const today = new Date();
          const [hours, minutes] = lastStockItem.time.split(':').map(Number);
          const lastTradeDateTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
          setLastTradeTime(lastTradeDateTime);
          console.log('✅ 실제 거래 마지막 시간:', lastTradeDateTime);
        }
      }
      
      // 캐시 시간이 있을 때만 업데이트, 없으면 기존 시간 유지
      if (cacheLastUpdate) {
        setLastUpdate(cacheLastUpdate);
        console.log('✅ 주식 데이터 로드 완료 (캐시 시간 사용):', cacheLastUpdate);
      } else {
        console.log('⚠️ 주식 데이터 캐시 메타데이터 없음, 기존 시간 유지');
      }
    } catch (err) {
      console.error('[useRealtimeStockData] 데이터 로드 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  // 초기 데이터 로드
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 1분마다 데이터 자동 갱신 (Redis 캐시와 동기화)
  useEffect(() => {
    const interval = setInterval(() => {
      loadData();
    }, 60000); // 1분마다

    return () => clearInterval(interval);
  }, [loadData]);

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
    refreshData,
  };
};

// useStockSummary 훅 제거됨 - useRealtimeStockData의 summaryData로 대체

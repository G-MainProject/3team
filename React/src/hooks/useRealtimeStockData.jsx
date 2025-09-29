import { useState, useEffect, useCallback, useRef } from 'react';
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
  const [cacheLastUpdate, setCacheLastUpdate] = useState(null); // 캐시 데이터 마지막 업데이트 시간
  const nextUpdateTime = useRef(null); // 다음 갱신 예정 시간
  
  // 로컬 스토리지 키
  const CACHE_KEY = `stock_cache_${symbol}`;
  const CACHE_TIME_KEY = `stock_cache_time_${symbol}`;

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
        const metadata = responseData.metadata || null; // 캐시 메타데이터
        
        setStockData(unifiedData.stockData || []);
        setVolumeData(unifiedData.volumeData || []);
        setSummaryData(unifiedData.summary || null);
        
        // 로컬 스토리지에 데이터 저장
        localStorage.setItem(CACHE_KEY, JSON.stringify({
          stockData: unifiedData.stockData || [],
          volumeData: unifiedData.volumeData || [],
          summary: unifiedData.summary || null
        }));
        
        
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
        
        // 캐시 메타데이터에서 실제 lastUpdated 시간 사용
        if (metadata && metadata.lastUpdated) {
          const cacheUpdateTime = new Date(metadata.lastUpdated);
          setCacheLastUpdate(cacheUpdateTime);
          
          // 다음 갱신 시간 계산 (캐시 업데이트 시간 + 1분)
          const nextUpdate = new Date(cacheUpdateTime.getTime() + 60000);
          nextUpdateTime.current = nextUpdate;
          
          console.log('📅 캐시 업데이트 시간:', cacheUpdateTime.toLocaleString());
          console.log('⏰ 다음 갱신 예정 시간:', nextUpdate.toLocaleString());
          
          // 로컬 스토리지에 캐시 시간 저장
          localStorage.setItem(CACHE_TIME_KEY, cacheUpdateTime.toISOString());
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
  }, [symbol, CACHE_KEY, CACHE_TIME_KEY]);

  // 초기 데이터 로드 - 로컬 스토리지에서 복원 시도
  useEffect(() => {
    // 로컬 스토리지에서 캐시된 데이터 복원 시도
    try {
      const cachedData = localStorage.getItem(CACHE_KEY);
      const cachedTime = localStorage.getItem(CACHE_TIME_KEY);
      
      if (cachedData && cachedTime) {
        const data = JSON.parse(cachedData);
        const cacheTime = new Date(cachedTime);
        
        // 캐시된 데이터가 1분 이내인지 확인
        const now = new Date();
        const timeDiff = now.getTime() - cacheTime.getTime();
        
        if (timeDiff < 60000) { // 1분 이내
          console.log('📦 로컬 스토리지에서 캐시된 데이터 복원');
          setStockData(data.stockData || []);
          setVolumeData(data.volumeData || []);
          setSummaryData(data.summary || null);
          setCacheLastUpdate(cacheTime);
          
          // 다음 갱신 시간 계산
          const nextUpdate = new Date(cacheTime.getTime() + 60000);
          nextUpdateTime.current = nextUpdate;
          
          setLoading(false);
          return; // API 호출하지 않음
        }
      }
    } catch (error) {
      console.warn('로컬 스토리지 데이터 복원 실패:', error);
    }
    
    // 로컬 스토리지에 유효한 데이터가 없으면 API 호출
    loadData();
  }, [symbol]); // symbol만 의존성으로 사용

  // 캐시 업데이트 시점을 기준으로 한 자동 갱신
  useEffect(() => {
    if (!nextUpdateTime.current) return;

    const scheduleNextUpdate = () => {
      const now = new Date();
      const timeUntilNext = nextUpdateTime.current.getTime() - now.getTime();
      
      if (timeUntilNext > 0) {
        console.log('⏳ 다음 갱신까지 남은 시간:', Math.round(timeUntilNext / 1000), '초');
        
        const timeoutId = setTimeout(() => {
          loadData();
          scheduleNextUpdate(); // 다음 갱신 스케줄링
        }, timeUntilNext);
        
        return () => clearTimeout(timeoutId);
      } else {
        // 이미 시간이 지났으면 즉시 갱신
        loadData();
        scheduleNextUpdate();
        return () => {};
      }
    };

    const cleanup = scheduleNextUpdate();
    return cleanup;
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
    cacheLastUpdate,
    refreshData,
  };
};

// useStockSummary 훅 제거됨 - useRealtimeStockData의 summaryData로 대체

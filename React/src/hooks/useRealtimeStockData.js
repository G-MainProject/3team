import { useState, useEffect, useCallback } from 'react';
import { getRealtimeStockData, getVolumeData, subscribeRealtimeData } from '../services/kiwoomApi';

// 실시간 주식 데이터를 관리하는 커스텀 훅
export const useRealtimeStockData = (symbol = '005930') => {
  const [stockData, setStockData] = useState([]);
  const [volumeData, setVolumeData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // 데이터 로드 함수
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 주가 데이터와 거래량 데이터를 병렬로 가져오기
      const [stockResult, volumeResult] = await Promise.all([
        getRealtimeStockData(symbol),
        getVolumeData(symbol)
      ]);

      setStockData(stockResult);
      setVolumeData(volumeResult);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('데이터 로드 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  // 초기 데이터 로드
  useEffect(() => {
    loadData();
  }, [loadData]);

  // 실시간 데이터 구독
  useEffect(() => {
    const unsubscribe = subscribeRealtimeData(symbol, (newData) => {
      setStockData(prevData => {
        // 새로운 데이터를 기존 데이터에 추가 (최대 50개 유지)
        const updatedData = [...prevData, ...newData];
        return updatedData.slice(-50);
      });
      setLastUpdate(new Date());
    });

    return unsubscribe;
  }, [symbol]);

  // 수동 새로고침 함수
  const refreshData = useCallback(() => {
    loadData();
  }, [loadData]);

  return {
    stockData,
    volumeData,
    loading,
    error,
    lastUpdate,
    refreshData,
  };
};

// 주식 정보 요약 데이터를 가져오는 훅
export const useStockSummary = (symbol = '005930') => {
  const [summary, setSummary] = useState({
    currentPrice: 0,
    change: 0,
    changePercent: 0,
    volume: 0,
    marketCap: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        const data = await getRealtimeStockData(symbol);
        
        if (data && data.length > 0) {
          const latest = data[data.length - 1];
          const previous = data[data.length - 2] || latest;
          
          const change = latest.price - previous.price;
          const changePercent = (change / previous.price) * 100;
          
          setSummary({
            currentPrice: latest.price,
            change: change,
            changePercent: changePercent,
            volume: latest.volume || 0,
            marketCap: latest.price * 1000000000, // 가정: 10억 주
          });
        }
      } catch (error) {
        console.error('주식 요약 정보 가져오기 실패:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
    
    // 30초마다 업데이트
    const interval = setInterval(fetchSummary, 30000);
    return () => clearInterval(interval);
  }, [symbol]);

  return { summary, loading };
};

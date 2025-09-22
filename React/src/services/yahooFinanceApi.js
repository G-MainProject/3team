// Spring 백엔드 API 서비스
const SPRING_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';


// Spring 백엔드 API 호출
const callSpringAPI = async (endpoint) => {
  try {
    const response = await fetch(`${SPRING_BASE_URL}${endpoint}`);
    
    if (!response.ok) {
      throw new Error(`Spring API 호출 실패: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Spring API 오류:', error);
    throw error;
  }
};

// 실시간 주가 데이터 가져오기
export const getRealtimeStockData = async (symbol = '005930') => {
  try {
    const response = await callSpringAPI(`/stock/realtime/${symbol}`);
    
    if (response.success && response.data) {
      return response.data;
    } else {
      throw new Error('주가 데이터를 찾을 수 없습니다.');
    }
  } catch (error) {
    console.error('실시간 주가 데이터 가져오기 실패:', error);
    // API 호출 실패 시 빈 배열 반환
    return [];
  }
};

// 주식 요약 정보 가져오기
export const getStockSummary = async (symbol = '005930') => {
  try {
    const response = await callSpringAPI(`/stock/summary/${symbol}`);
    
    if (response.success && response.data) {
      return response.data;
    } else {
      throw new Error('주식 정보를 찾을 수 없습니다.');
    }
  } catch (error) {
    console.error('주식 요약 정보 가져오기 실패:', error);
    // API 호출 실패 시 null 반환
    return null;
  }
};

// 거래량 데이터 가져오기
export const getVolumeData = async (symbol = '005930') => {
  try {
    const response = await callSpringAPI(`/stock/volume/${symbol}`);
    
    if (response.success && response.data) {
      return response.data;
    } else {
      throw new Error('거래량 데이터를 찾을 수 없습니다.');
    }
  } catch (error) {
    console.error('거래량 데이터 가져오기 실패:', error);
    // API 호출 실패 시 빈 배열 반환
    return [];
  }
};



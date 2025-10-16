// Spring Backend API 연동 서비스
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (window.location.hostname.includes('devtunnels.ms')
    ? `${window.location.protocol}//${window.location.hostname}/api`  // Dev Tunnels: 포트 번호 제거
    : window.location.protocol === 'https:' 
      ? `https://${window.location.hostname}:8080/api`
      : `http://${window.location.hostname}:8080/api`);

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // 공통 요청 메서드
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      throw error;
    }
  }

  // GET 요청
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  // POST 요청
  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // PUT 요청
  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // DELETE 요청
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  // 헬스체크 API
  async getHealth() {
    return this.get('/health');
  }

  // SNS 데이터 조회 API
  async getSnsData(symbol) {
    return this.get(`/sns/${symbol}`);
  }

  // SNS 헬스체크 API
  async getSnsHealth() {
    return this.get('/sns/health');
  }

  // 주식 요약 정보 조회 API
  async getStockSummary(symbol) {
    return this.get(`/stock/summary/${symbol}`);
  }

  // 실시간 주가 데이터 조회 API
  async getRealtimeStockData(symbol) {
    return this.get(`/stock/realtime/${symbol}`);
  }

  // 거래량 데이터 조회 API
  async getVolumeData(symbol) {
    return this.get(`/stock/volume/${symbol}`);
  }

  // 통합 주식 데이터 조회 API
  async getUnifiedStockData(symbol, interval = '1m') {
    return this.get(`/stock/unified/${symbol}?interval=${interval}`);
  }
}

// 싱글톤 인스턴스 생성
const apiService = new ApiService();

export default apiService;

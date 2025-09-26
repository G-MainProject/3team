package com.team3.backendapi.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.team3.backendapi.dto.CacheMetadata;
import com.team3.backendapi.dto.StockPriceDto;
import com.team3.backendapi.dto.StockSummaryDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class ScheduledStockDataService {
    
    private final YahooFinanceApiService yahooFinanceApiService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    // 1분마다 실행
    @Scheduled(fixedRate = 60000)
    public void collectStockData() {
        log.info("주식 데이터 수집 시작");
        
        try {
            // sentiment_report.json에서 주식 목록 가져오기
            List<String> stockCodes = getStockCodesFromFile();
            
            for (String stockCode : stockCodes) {
                try {
                    // 1. 주식 요약 정보 수집
                    StockSummaryDto stockData = yahooFinanceApiService.getStockSummary(stockCode);
                    if (stockData != null) {
                        String summaryCacheKey = "stock:" + stockCode;
                        String metadataKey = "metadata:stock:" + stockCode;
                        CacheMetadata metadata = new CacheMetadata("stock", stockCode, null);
                        
                        redisTemplate.opsForValue().set(summaryCacheKey, stockData, Duration.ofMinutes(2));
                        redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(2));
                        log.info("주식 요약 데이터 수집 완료: {} - {}", stockCode, stockData.getName());
                    }
                    
                    // 2. 실시간 주가 데이터 수집
                    try {
                        List<StockPriceDto> realtimeData = yahooFinanceApiService.getRealtimeStockData(stockCode, "1m");
                        if (realtimeData != null && !realtimeData.isEmpty()) {
                            String realtimeCacheKey = "realtime:" + stockCode + ":1m";
                            String metadataKey = "metadata:realtime:" + stockCode + ":1m";
                            CacheMetadata metadata = new CacheMetadata("realtime", stockCode, "1m");
                            
                            redisTemplate.opsForValue().set(realtimeCacheKey, realtimeData, Duration.ofMinutes(2));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(2));
                            log.info("실시간 주가 데이터 수집 완료: {} - {}개 데이터", stockCode, realtimeData.size());
                        }
                    } catch (Exception e) {
                        log.warn("실시간 주가 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                    }
                    
                    // 3. 거래량 데이터 수집
                    try {
                        List<StockPriceDto> volumeData = yahooFinanceApiService.getVolumeData(stockCode, "1m");
                        if (volumeData != null && !volumeData.isEmpty()) {
                            String volumeCacheKey = "volume:" + stockCode + ":1m";
                            String metadataKey = "metadata:volume:" + stockCode + ":1m";
                            CacheMetadata metadata = new CacheMetadata("volume", stockCode, "1m");
                            
                            redisTemplate.opsForValue().set(volumeCacheKey, volumeData, Duration.ofMinutes(2));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(2));
                            log.info("거래량 데이터 수집 완료: {} - {}개 데이터", stockCode, volumeData.size());
                        }
                    } catch (Exception e) {
                        log.warn("거래량 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                    }
                    
                } catch (Exception e) {
                    log.error("주식 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                }
            }
            
            log.info("주식 데이터 수집 완료 - 총 {}개 종목", stockCodes.size());
        } catch (Exception e) {
            log.error("주식 데이터 수집 중 오류 발생: {}", e.getMessage());
        }
    }
    
    private List<String> getStockCodesFromFile() {
        List<String> stockCodes = new ArrayList<>();
        
        try {
            // sentiment_report.json 파일 경로
            String filePath = "data/raws/sentiment_report.json";
            File file = new File(filePath);
            
            if (!file.exists()) {
                log.warn("sentiment_report.json 파일을 찾을 수 없습니다: {}", filePath);
                return getDefaultStockCodes();
            }
            
            // JSON 파일 읽기
            List<Map<String, Object>> data = objectMapper.readValue(file, new TypeReference<List<Map<String, Object>>>() {});
            
            // 중복 제거하여 주식 코드 추출
            for (Map<String, Object> item : data) {
                String stockCode = (String) item.get("stockCode");
                if (stockCode != null && !stockCodes.contains(stockCode)) {
                    stockCodes.add(stockCode);
                }
            }
            
            log.info("파일에서 {}개 주식 코드를 읽었습니다", stockCodes.size());
            
        } catch (IOException e) {
            log.error("sentiment_report.json 파일 읽기 실패: {}", e.getMessage());
            return getDefaultStockCodes();
        }
        
        return stockCodes.isEmpty() ? getDefaultStockCodes() : stockCodes;
    }
    
    private List<String> getDefaultStockCodes() {
        // 기본 주식 코드들 (파일을 읽을 수 없을 때 사용)
        // TODO: 설정 파일이나 데이터베이스에서 기본 종목 리스트를 관리하도록 개선 필요
        return List.of("005930"); // 삼성전자만 기본으로 설정
    }
}

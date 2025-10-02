package com.team3.backendapi.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.team3.backendapi.controller.WebSocketController;
import com.team3.backendapi.dto.CacheMetadata;
import com.team3.backendapi.dto.StockPriceDto;
import com.team3.backendapi.dto.StockSummaryDto;
import com.team3.backendapi.dto.UnifiedStockData;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import jakarta.annotation.PostConstruct;

import java.io.File;
import java.io.IOException;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class ScheduledStockDataService {
    
    private final YahooFinanceApiService yahooFinanceApiService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper;
    private final WebSocketController webSocketController;
    
    // 애플리케이션 시작 시 즉시 실행
    @PostConstruct
    public void initializeData() {
        log.info("🚀 애플리케이션 시작 - 초기 주식 데이터 수집");
        collectStockData();
    }
    
    // 매 정각 0초에 실행
    @Scheduled(cron = "0 * * * * *")
    public void collectStockData() {
        log.info("🔄 주식 데이터 수집 시작 - 현재 시간: {}", java.time.LocalDateTime.now());
        
        try {
            // sentiment_report.json에서 주식 목록 가져오기
            List<String> stockCodes = getStockCodesFromFile();
            log.info("📊 파일에서 {}개 주식 코드를 읽었습니다", stockCodes.size());
            
            int successCount = 0;
            int failCount = 0;
            
            for (String stockCode : stockCodes) {
                try {
                    // 1. 주식 요약 정보 수집
                    try {
                        StockSummaryDto stockData = yahooFinanceApiService.getStockSummary(stockCode);
                        if (stockData != null) {
                            String summaryCacheKey = "stock:" + stockCode;
                            String metadataKey = "metadata:stock:" + stockCode;
                            CacheMetadata metadata = new CacheMetadata("stock", stockCode, null);
                            
                            redisTemplate.opsForValue().set(summaryCacheKey, stockData, Duration.ofMinutes(5));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(5));
                            log.info("✅ 주식 요약 데이터 수집 완료: {} - {}", stockCode, stockData.getName());
                        } else {
                            log.warn("⚠️ 주식 요약 데이터가 null: {}", stockCode);
                        }
                    } catch (Exception e) {
                        log.warn("❌ 주식 요약 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                    }
                    
                    // 2. 실시간 주가 데이터 수집
                    try {
                        List<StockPriceDto> realtimeData = yahooFinanceApiService.getRealtimeStockData(stockCode, "1m");
                        if (realtimeData != null && !realtimeData.isEmpty()) {
                            String realtimeCacheKey = "realtime:" + stockCode + ":1m";
                            String metadataKey = "metadata:realtime:" + stockCode + ":1m";
                            CacheMetadata metadata = new CacheMetadata("realtime", stockCode, "1m");
                            
                            redisTemplate.opsForValue().set(realtimeCacheKey, realtimeData, Duration.ofMinutes(5));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(5));
                            log.info("✅ 실시간 주가 데이터 수집 완료: {} - {}개 데이터", stockCode, realtimeData.size());
                        } else {
                            log.warn("⚠️ 실시간 주가 데이터가 비어있음: {}", stockCode);
                        }
                    } catch (Exception e) {
                        log.warn("❌ 실시간 주가 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                    }
                    
                    // 3. 거래량 데이터 수집 (현재 시간 기준으로 조정)
                    try {
                        List<StockPriceDto> volumeData = yahooFinanceApiService.getVolumeData(stockCode, "1m");
                        if (volumeData != null && !volumeData.isEmpty()) {
                            // 현재 시간 기준으로 거래량 데이터 시간 조정
                            List<StockPriceDto> adjustedVolumeData = adjustVolumeDataToCurrentTime(volumeData);
                            
                            String volumeCacheKey = "volume:" + stockCode + ":1m";
                            String metadataKey = "metadata:volume:" + stockCode + ":1m";
                            CacheMetadata metadata = new CacheMetadata("volume", stockCode, "1m");
                            
                            redisTemplate.opsForValue().set(volumeCacheKey, adjustedVolumeData, Duration.ofMinutes(5));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(5));
                            log.info("✅ 거래량 데이터 수집 완료 (시간 조정): {} - {}개 데이터", stockCode, adjustedVolumeData.size());
                        } else {
                            log.warn("⚠️ 거래량 데이터가 비어있음: {}", stockCode);
                        }
                    } catch (Exception e) {
                        log.warn("❌ 거래량 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                    }
                    
                    // 4. 통합 데이터 생성 및 캐시 저장 (최소한의 데이터라도 있으면 생성)
                    try {
                        // 개별 데이터들을 안전하게 조회하여 통합 데이터 생성
                        Object summaryObj = redisTemplate.opsForValue().get("stock:" + stockCode);
                        Object realtimeObj = redisTemplate.opsForValue().get("realtime:" + stockCode + ":1m");
                        Object volumeObj = redisTemplate.opsForValue().get("volume:" + stockCode + ":1m");
                        
                        // 최소한 하나의 데이터라도 있으면 통합 데이터 생성
                        if (summaryObj != null || realtimeObj != null || volumeObj != null) {
                            // ObjectMapper를 사용해서 안전하게 변환
                            StockSummaryDto summaryData = null;
                            List<StockPriceDto> realtimeData = new ArrayList<>();
                            List<StockPriceDto> volumeData = new ArrayList<>();
                            
                            if (summaryObj != null) {
                                try {
                                    summaryData = objectMapper.convertValue(summaryObj, StockSummaryDto.class);
                                } catch (Exception e) {
                                    log.warn("요약 데이터 변환 실패: {} - {}", stockCode, e.getMessage());
                                }
                            }
                            
                            if (realtimeObj != null) {
                                try {
                                    realtimeData = objectMapper.convertValue(realtimeObj, new TypeReference<List<StockPriceDto>>() {});
                                } catch (Exception e) {
                                    log.warn("실시간 데이터 변환 실패: {} - {}", stockCode, e.getMessage());
                                }
                            }
                            
                            if (volumeObj != null) {
                                try {
                                    volumeData = objectMapper.convertValue(volumeObj, new TypeReference<List<StockPriceDto>>() {});
                                } catch (Exception e) {
                                    log.warn("거래량 데이터 변환 실패: {} - {}", stockCode, e.getMessage());
                                }
                            }
                            
                            // UnifiedStockData 객체 생성
                            UnifiedStockData unifiedData = new UnifiedStockData();
                            unifiedData.setStockData(realtimeData);
                            unifiedData.setVolumeData(volumeData);
                            unifiedData.setSummary(summaryData);
                            
                            // 통합 데이터 캐시 저장
                            String unifiedCacheKey = "unified:" + stockCode + ":1m";
                            redisTemplate.opsForValue().set(unifiedCacheKey, unifiedData, Duration.ofMinutes(5));
                            log.info("✅ 통합 주식 데이터 수집 완료: {} - 통합 캐시 저장", stockCode);
                            
                            // WebSocket으로 실시간 데이터 브로드캐스트
                            webSocketController.broadcastStockData(stockCode, unifiedData);
                            
                            successCount++;
                        } else {
                            log.warn("⚠️ 모든 데이터가 없어서 통합 데이터 생성 불가: {}", stockCode);
                            failCount++;
                        }
                    } catch (Exception e) {
                        log.warn("❌ 통합 데이터 생성 실패: {} - {}", stockCode, e.getMessage());
                        failCount++;
                    }
                    
                } catch (Exception e) {
                    log.error("❌ 주식 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                    failCount++;
                }
            }
            
            log.info("✅ 주식 데이터 수집 완료 - 성공: {}개, 실패: {}개, 총: {}개 종목", 
                    successCount, failCount, stockCodes.size());
        } catch (Exception e) {
            log.error("❌ 주식 데이터 수집 중 오류 발생: {}", e.getMessage());
            // Redis 연결 실패 등으로 인한 오류가 발생해도 스케줄러는 계속 실행되도록 함
        }
    }
    
    private List<String> getStockCodesFromFile() {
        List<String> stockCodes = new ArrayList<>();
        
        try {
            // sentiment_report.json 파일 경로 (Spring 폴더에서 상위 폴더의 data/raws 접근)
            String filePath = "../data/raws/sentiment_report.json";
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
    
    // 거래량 데이터를 현재 시간 기준으로 조정하는 메서드
    private List<StockPriceDto> adjustVolumeDataToCurrentTime(List<StockPriceDto> originalData) {
        List<StockPriceDto> adjustedData = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();
        
        // 최근 7시간(420분) 데이터를 현재 시간 기준으로 조정
        for (int i = 0; i < originalData.size(); i++) {
            StockPriceDto original = originalData.get(i);
            
            // 현재 시간에서 역산하여 시간 계산 (최신 데이터가 이전 분)
            LocalDateTime adjustedTime = now.minusMinutes(originalData.size() - i);
            String adjustedTimeString = adjustedTime.format(DateTimeFormatter.ofPattern("HH:mm"));
            
            // 조정된 시간으로 새로운 StockPriceDto 생성
            StockPriceDto adjusted = new StockPriceDto(
                adjustedTimeString,
                original.getPrice(),
                original.getVolume()
            );
            
            adjustedData.add(adjusted);
        }
        
        log.info("거래량 데이터 시간 조정 완료: {}개 데이터 ({} ~ {})", 
                adjustedData.size(), 
                adjustedData.get(0).getTime(),
                adjustedData.get(adjustedData.size() - 1).getTime());
        
        return adjustedData;
    }
}

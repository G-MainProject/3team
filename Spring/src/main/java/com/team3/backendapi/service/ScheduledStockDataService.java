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
        collectStockData();
    }
    
    // 매 정각 0초에 실행
    @Scheduled(cron = "0 * * * * *")
    public void collectStockData() {
        LocalDateTime now = LocalDateTime.now();
        boolean isMarketClosed = isMarketClosed(now);
        
        if (isMarketClosed) {
            maintainCachedData();
            return;
        }
        
        try {
            List<String> stockCodes = getStockCodesFromFile();
            int successCount = 0;
            int failCount = 0;
            
            for (String stockCode : stockCodes) {
                try {
                    try {
                        StockSummaryDto stockData = yahooFinanceApiService.getStockSummary(stockCode);
                        if (stockData != null) {
                            String summaryCacheKey = "stock:" + stockCode;
                            String metadataKey = "metadata:stock:" + stockCode;
                            CacheMetadata metadata = new CacheMetadata("stock", stockCode, null);
                            
                            redisTemplate.opsForValue().set(summaryCacheKey, stockData, Duration.ofMinutes(5));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(5));
                        }
                    } catch (Exception e) {
                        log.warn("Stock summary collection failed for {}: {}", stockCode, e.getMessage());
                    }
                    
                    try {
                        List<StockPriceDto> realtimeData = yahooFinanceApiService.getRealtimeStockData(stockCode, "1m");
                        if (realtimeData != null && !realtimeData.isEmpty()) {
                            String realtimeCacheKey = "realtime:" + stockCode + ":1m";
                            String metadataKey = "metadata:realtime:" + stockCode + ":1m";
                            CacheMetadata metadata = new CacheMetadata("realtime", stockCode, "1m");
                            
                            redisTemplate.opsForValue().set(realtimeCacheKey, realtimeData, Duration.ofMinutes(5));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(5));
                        }
                    } catch (Exception e) {
                        log.warn("Realtime stock data collection failed for {}: {}", stockCode, e.getMessage());
                    }
                    
                    try {
                        List<StockPriceDto> volumeData = yahooFinanceApiService.getVolumeData(stockCode, "1m");
                        if (volumeData != null && !volumeData.isEmpty()) {
                            String volumeCacheKey = "volume:" + stockCode + ":1m";
                            String metadataKey = "metadata:volume:" + stockCode + ":1m";
                            CacheMetadata metadata = new CacheMetadata("volume", stockCode, "1m");
                            
                            redisTemplate.opsForValue().set(volumeCacheKey, volumeData, Duration.ofMinutes(5));
                            redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(5));
                        }
                    } catch (Exception e) {
                        log.warn("Volume data collection failed for {}: {}", stockCode, e.getMessage());
                    }
                    
                    try {
                        Object summaryObj = redisTemplate.opsForValue().get("stock:" + stockCode);
                        Object realtimeObj = redisTemplate.opsForValue().get("realtime:" + stockCode + ":1m");
                        Object volumeObj = redisTemplate.opsForValue().get("volume:" + stockCode + ":1m");
                        
                        if (summaryObj != null || realtimeObj != null || volumeObj != null) {
                            StockSummaryDto summaryData = null;
                            List<StockPriceDto> realtimeData = new ArrayList<>();
                            List<StockPriceDto> volumeData = new ArrayList<>();
                            
                            if (summaryObj != null) {
                                try {
                                    summaryData = objectMapper.convertValue(summaryObj, StockSummaryDto.class);
                                } catch (Exception e) {
                                    log.warn("Summary data conversion failed for {}: {}", stockCode, e.getMessage());
                                }
                            }
                            
                            if (realtimeObj != null) {
                                try {
                                    realtimeData = objectMapper.convertValue(realtimeObj, new TypeReference<List<StockPriceDto>>() {});
                                } catch (Exception e) {
                                    log.warn("Realtime data conversion failed for {}: {}", stockCode, e.getMessage());
                                }
                            }
                            
                            if (volumeObj != null) {
                                try {
                                    volumeData = objectMapper.convertValue(volumeObj, new TypeReference<List<StockPriceDto>>() {});
                                } catch (Exception e) {
                                    log.warn("Volume data conversion failed for {}: {}", stockCode, e.getMessage());
                                }
                            }
                            
                            UnifiedStockData unifiedData = new UnifiedStockData();
                            unifiedData.setStockData(realtimeData);
                            unifiedData.setVolumeData(volumeData);
                            unifiedData.setSummary(summaryData);
                            
                            String unifiedCacheKey = "unified:" + stockCode + ":1m";
                            redisTemplate.opsForValue().set(unifiedCacheKey, unifiedData, Duration.ofMinutes(5));
                            
                            webSocketController.broadcastStockData(stockCode, unifiedData);
                            successCount++;
                        } else {
                            failCount++;
                        }
                    } catch (Exception e) {
                        log.warn("Unified data creation failed for {}: {}", stockCode, e.getMessage());
                        failCount++;
                    }
                    
                } catch (Exception e) {
                    log.error("Stock data collection failed for {}: {}", stockCode, e.getMessage());
                    failCount++;
                }
            }
        } catch (Exception e) {
            log.error("Stock data collection error: {}", e.getMessage());
        }
    }
    
    private List<String> getStockCodesFromFile() {
        List<String> stockCodes = new ArrayList<>();
        
        try {
            // sentiment_report.json 파일 경로 (Spring 폴더에서 상위 폴더의 data/raws 접근)
            String filePath = "../data/raws/sentiment_report.json";
            File file = new File(filePath);
            
            if (!file.exists()) {
                log.warn("sentiment_report.json file not found: {}", filePath);
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
            
        } catch (IOException e) {
            log.error("Failed to read sentiment_report.json: {}", e.getMessage());
            return getDefaultStockCodes();
        }
        
        return stockCodes.isEmpty() ? getDefaultStockCodes() : stockCodes;
    }
    
    private List<String> getDefaultStockCodes() {
        return List.of("005930");
    }
    
    private boolean isMarketClosed(LocalDateTime now) {
        int dayOfWeek = now.getDayOfWeek().getValue();
        
        if (dayOfWeek == 6 || dayOfWeek == 7) {
            return true;
        }
        
        int hour = now.getHour();
        int minute = now.getMinute();
        return hour > 15 || (hour == 15 && minute >= 30);
    }
    
    private void maintainCachedData() {
        try {
            List<String> stockCodes = getStockCodesFromFile();
            
            for (String stockCode : stockCodes) {
                try {
                    extendCacheTTL(stockCode);
                } catch (Exception e) {
                    log.warn("Cache TTL extension failed for {}: {}", stockCode, e.getMessage());
                }
            }
        } catch (Exception e) {
            log.error("Cache maintenance error: {}", e.getMessage());
        }
    }
    
    private void extendCacheTTL(String stockCode) {
        try {
            Duration extendedTTL = Duration.ofHours(1);
            
            String summaryCacheKey = "stock:" + stockCode;
            Object summaryData = redisTemplate.opsForValue().get(summaryCacheKey);
            if (summaryData != null) {
                redisTemplate.opsForValue().set(summaryCacheKey, summaryData, extendedTTL);
            }
            
            String realtimeCacheKey = "realtime:" + stockCode + ":1m";
            Object realtimeData = redisTemplate.opsForValue().get(realtimeCacheKey);
            if (realtimeData != null) {
                redisTemplate.opsForValue().set(realtimeCacheKey, realtimeData, extendedTTL);
            }
            
            String volumeCacheKey = "volume:" + stockCode + ":1m";
            Object volumeData = redisTemplate.opsForValue().get(volumeCacheKey);
            if (volumeData != null) {
                redisTemplate.opsForValue().set(volumeCacheKey, volumeData, extendedTTL);
            }
            
            String unifiedCacheKey = "unified:" + stockCode + ":1m";
            Object unifiedData = redisTemplate.opsForValue().get(unifiedCacheKey);
            if (unifiedData != null) {
                redisTemplate.opsForValue().set(unifiedCacheKey, unifiedData, extendedTTL);
            }
            
        } catch (Exception e) {
            log.error("Cache TTL extension failed for {}: {}", stockCode, e.getMessage());
        }
    }
    
}

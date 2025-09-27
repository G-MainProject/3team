package com.team3.backendapi.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.team3.backendapi.dto.ApiResponse;
import com.team3.backendapi.dto.CacheMetadata;
import com.team3.backendapi.dto.CachedDataResponse;
import com.team3.backendapi.dto.StockPriceDto;
import com.team3.backendapi.dto.StockSummaryDto;
import com.team3.backendapi.dto.UnifiedStockData;
import com.team3.backendapi.service.YahooFinanceApiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/stock")
@CrossOrigin(origins = "http://localhost:5173")
@RequiredArgsConstructor
@Slf4j
public class StockController {

    private final YahooFinanceApiService yahooFinanceApiService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    // Redis 연결 테스트
    @GetMapping("/test-redis")
    public ResponseEntity<String> testRedis() {
        try {
            redisTemplate.opsForValue().set("test", "Redis 연결 성공!");
            String result = (String) redisTemplate.opsForValue().get("test");
            return ResponseEntity.ok("Redis 테스트: " + result);
        } catch (Exception e) {
            return ResponseEntity.ok("Redis 연결 실패: " + e.getMessage());
        }
    }
    
    // 수동 캐시 데이터 생성 테스트
    @GetMapping("/create-cache/{symbol}")
    public ResponseEntity<String> createCache(@PathVariable String symbol) {
        try {
            log.info("수동 캐시 생성 시작: {}", symbol);
            StockSummaryDto summary = yahooFinanceApiService.getStockSummary(symbol);
            
            if (summary != null) {
                String cacheKey = "stock:" + symbol;
                redisTemplate.opsForValue().set(cacheKey, summary, java.time.Duration.ofMinutes(5));
                log.info("✅ 수동 캐시 생성 완료: {} - {}", symbol, summary.getName());
                return ResponseEntity.ok("캐시 생성 완료: " + summary.getName());
            } else {
                return ResponseEntity.ok("주식 데이터 조회 실패");
            }
        } catch (Exception e) {
            log.error("수동 캐시 생성 실패: {} - {}", symbol, e.getMessage());
            return ResponseEntity.ok("캐시 생성 실패: " + e.getMessage());
        }
    }

    // 실시간 주가 데이터 조회 (캐시 우선)
    @GetMapping("/realtime/{symbol}")
    public ResponseEntity<ApiResponse<CachedDataResponse<List<StockPriceDto>>>> getRealtimeStockData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval) {
        try {
            // Redis에서 캐시된 데이터 조회
            String cacheKey = "realtime:" + symbol + ":" + interval;
            String metadataKey = "metadata:realtime:" + symbol + ":" + interval;
            
            Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
            Object metadataObject = redisTemplate.opsForValue().get(metadataKey);
            List<StockPriceDto> cachedData = null;
            CacheMetadata metadata = null;
            
            if (cachedObject != null) {
                try {
                    ObjectMapper objectMapper = new ObjectMapper();
                    objectMapper.registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());
                    cachedData = objectMapper.convertValue(cachedObject, new com.fasterxml.jackson.core.type.TypeReference<List<StockPriceDto>>() {});
                    
                    if (metadataObject != null) {
                        metadata = objectMapper.convertValue(metadataObject, CacheMetadata.class);
                    } else {
                        metadata = new CacheMetadata("realtime", symbol, interval);
                    }
                    
                    log.info("캐시된 실시간 주가 데이터 반환: {} - {}", symbol, interval);
                } catch (Exception e) {
                    log.warn("캐시된 실시간 데이터 변환 실패: {} - {}", symbol, e.getMessage());
                    cachedData = null;
                    metadata = null;
                }
            }
            
            if (cachedData != null) {
                CachedDataResponse<List<StockPriceDto>> response = new CachedDataResponse<>(cachedData, metadata);
                return ResponseEntity.ok(ApiResponse.success("실시간 주가 데이터를 성공적으로 조회했습니다.", response));
            } else {
                // 캐시에 없으면 실시간 조회
                log.info("캐시에 없는 실시간 주가 데이터 실시간 조회: {} - {}", symbol, interval);
                List<StockPriceDto> data = yahooFinanceApiService.getRealtimeStockData(symbol, interval);
                
                if (data != null && !data.isEmpty()) {
                    // 조회한 데이터를 캐시에 저장 (2분 TTL)
                    metadata = new CacheMetadata("realtime", symbol, interval);
                    redisTemplate.opsForValue().set(cacheKey, data, java.time.Duration.ofMinutes(2));
                    redisTemplate.opsForValue().set(metadataKey, metadata, java.time.Duration.ofMinutes(2));
                }
                
                CachedDataResponse<List<StockPriceDto>> response = new CachedDataResponse<>(data, metadata);
                return ResponseEntity.ok(ApiResponse.success("실시간 주가 데이터를 성공적으로 조회했습니다.", response));
            }
        } catch (Exception e) {
            log.error("실시간 주가 데이터 조회 실패: {} - {}", symbol, e.getMessage());
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiResponse.error("실시간 주가 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."));
        }
    }

    // 주식 요약 정보 조회 (캐시 우선)
    @GetMapping("/summary/{symbol}")
    public ResponseEntity<ApiResponse<CachedDataResponse<StockSummaryDto>>> getStockSummary(
            @PathVariable String symbol) {
        try {
            // Redis에서 캐시된 데이터 조회
            String cacheKey = "stock:" + symbol;
            String metadataKey = "metadata:stock:" + symbol;
            log.info("Redis 캐시 조회 시도: {}", cacheKey);
            
            Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
            Object metadataObject = redisTemplate.opsForValue().get(metadataKey);
            log.info("Redis 캐시 조회 결과: {} - {}", cacheKey, cachedObject != null ? "데이터 존재" : "데이터 없음");
            
            StockSummaryDto cachedData = null;
            CacheMetadata metadata = null;
            
            if (cachedObject != null) {
                try {
                    // ObjectMapper를 사용하여 안전하게 변환
                    ObjectMapper objectMapper = new ObjectMapper();
                    objectMapper.registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());
                    cachedData = objectMapper.convertValue(cachedObject, StockSummaryDto.class);
                    
                    if (metadataObject != null) {
                        metadata = objectMapper.convertValue(metadataObject, CacheMetadata.class);
                    } else {
                        metadata = new CacheMetadata("stock", symbol, null);
                    }
                    
                    log.info("✅ 캐시된 주식 데이터 반환: {} - {}", symbol, cachedData.getName());
                } catch (Exception e) {
                    log.warn("❌ 캐시된 데이터 변환 실패: {} - {}", symbol, e.getMessage());
                    cachedData = null;
                    metadata = null;
                }
            } else {
                log.info("❌ 캐시에 데이터 없음: {}", symbol);
            }
            
            if (cachedData != null) {
                CachedDataResponse<StockSummaryDto> response = new CachedDataResponse<>(cachedData, metadata);
                return ResponseEntity.ok(ApiResponse.success("주식 요약 정보를 성공적으로 조회했습니다.", response));
            } else {
                // 캐시에 없으면 실시간 조회
                log.info("캐시에 없는 주식 데이터 실시간 조회: {}", symbol);
                StockSummaryDto summary = yahooFinanceApiService.getStockSummary(symbol);
                
                if (summary != null) {
                    // 조회한 데이터를 캐시에 저장 (2분 TTL)
                    try {
                        metadata = new CacheMetadata("stock", symbol, null);
                        redisTemplate.opsForValue().set(cacheKey, summary, java.time.Duration.ofMinutes(2));
                        redisTemplate.opsForValue().set(metadataKey, metadata, java.time.Duration.ofMinutes(2));
                        log.info("✅ Redis 캐시 저장 완료: {} - {}", symbol, summary.getName());
                    } catch (Exception e) {
                        log.error("❌ Redis 캐시 저장 실패: {} - {}", symbol, e.getMessage());
                    }
                    CachedDataResponse<StockSummaryDto> response = new CachedDataResponse<>(summary, metadata);
                    return ResponseEntity.ok(ApiResponse.success("주식 요약 정보를 성공적으로 조회했습니다.", response));
                } else {
                    log.warn("주식 요약 정보를 가져올 수 없습니다: {}", symbol);
                    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                        .body(ApiResponse.error("주식 요약 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."));
                }
            }
        } catch (Exception e) {
            log.error("주식 요약 정보 조회 실패: {} - {}", symbol, e.getMessage());
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiResponse.error("주식 요약 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."));
        }
    }

    // 거래량 데이터 조회 (캐시 우선)
    @GetMapping("/volume/{symbol}")
    public ResponseEntity<ApiResponse<CachedDataResponse<List<StockPriceDto>>>> getVolumeData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval) {
        try {
            // Redis에서 캐시된 데이터 조회
            String cacheKey = "volume:" + symbol + ":" + interval;
            String metadataKey = "metadata:volume:" + symbol + ":" + interval;
            
            Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
            Object metadataObject = redisTemplate.opsForValue().get(metadataKey);
            List<StockPriceDto> cachedData = null;
            CacheMetadata metadata = null;
            
            if (cachedObject != null) {
                try {
                    ObjectMapper objectMapper = new ObjectMapper();
                    objectMapper.registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());
                    cachedData = objectMapper.convertValue(cachedObject, new com.fasterxml.jackson.core.type.TypeReference<List<StockPriceDto>>() {});
                    
                    if (metadataObject != null) {
                        metadata = objectMapper.convertValue(metadataObject, CacheMetadata.class);
                    } else {
                        metadata = new CacheMetadata("volume", symbol, interval);
                    }
                    
                    log.info("캐시된 거래량 데이터 반환: {} - {}", symbol, interval);
                } catch (Exception e) {
                    log.warn("캐시된 거래량 데이터 변환 실패: {} - {}", symbol, e.getMessage());
                    cachedData = null;
                    metadata = null;
                }
            }
            
            if (cachedData != null) {
                CachedDataResponse<List<StockPriceDto>> response = new CachedDataResponse<>(cachedData, metadata);
                return ResponseEntity.ok(ApiResponse.success("거래량 데이터를 성공적으로 조회했습니다.", response));
            } else {
                // 캐시에 없으면 실시간 조회
                log.info("캐시에 없는 거래량 데이터 실시간 조회: {} - {}", symbol, interval);
                List<StockPriceDto> data = yahooFinanceApiService.getVolumeData(symbol, interval);
                
                if (data != null && !data.isEmpty()) {
                    // 조회한 데이터를 캐시에 저장 (2분 TTL)
                    metadata = new CacheMetadata("volume", symbol, interval);
                    redisTemplate.opsForValue().set(cacheKey, data, java.time.Duration.ofMinutes(2));
                    redisTemplate.opsForValue().set(metadataKey, metadata, java.time.Duration.ofMinutes(2));
                }
                
                CachedDataResponse<List<StockPriceDto>> response = new CachedDataResponse<>(data, metadata);
                return ResponseEntity.ok(ApiResponse.success("거래량 데이터를 성공적으로 조회했습니다.", response));
            }
        } catch (Exception e) {
            log.error("거래량 데이터 조회 실패: {} - {}", symbol, e.getMessage());
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiResponse.error("거래량 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."));
        }
    }

    // 통합 주식 데이터 조회 (캐시 우선)
    @GetMapping("/unified/{symbol}")
    public ResponseEntity<ApiResponse<Object>> getUnifiedStockData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval) {
        try {
            // Redis에서 캐시된 통합 데이터 조회
            String cacheKey = "unified:" + symbol + ":" + interval;
            Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
            
            if (cachedObject != null) {
                try {
                    // ObjectMapper를 사용해서 안전하게 역직렬화
                    UnifiedStockData cachedData = objectMapper.convertValue(cachedObject, UnifiedStockData.class);
                    log.info("캐시된 통합 주식 데이터 반환: {} - {}", symbol, interval);
                    return ResponseEntity.ok(ApiResponse.success("통합 주식 데이터를 성공적으로 조회했습니다.", cachedData));
                } catch (Exception e) {
                    log.warn("캐시된 통합 데이터 역직렬화 실패: {} - {}, 실시간 조회로 전환", symbol, e.getMessage());
                }
            }
            
            // 캐시에 없거나 역직렬화 실패 시 실시간 조회
            log.info("캐시에 없는 통합 주식 데이터 실시간 조회: {} - {}", symbol, interval);
            
            // 개별 데이터 조회 (각각 캐시 확인)
            List<StockPriceDto> stockData = getCachedOrFetchStockData(symbol, interval, "realtime");
            List<StockPriceDto> volumeData = getCachedOrFetchVolumeData(symbol, interval);
            StockSummaryDto summary = getCachedOrFetchSummary(symbol);

            UnifiedStockData response = new UnifiedStockData();
            response.setStockData(stockData);
            response.setVolumeData(volumeData);
            response.setSummary(summary);

            // 통합 데이터를 캐시에 저장 (2분 TTL)
            redisTemplate.opsForValue().set(cacheKey, response, java.time.Duration.ofMinutes(2));

            return ResponseEntity.ok(ApiResponse.success("통합 주식 데이터를 성공적으로 조회했습니다.", response));
        } catch (Exception e) {
            log.error("통합 주식 데이터 조회 실패: {} - {}", symbol, e.getMessage());
            return ResponseEntity.badRequest()
                .body(ApiResponse.error("통합 주식 데이터 조회에 실패했습니다: " + e.getMessage()));
        }
    }
    
    // 캐시된 주가 데이터 조회 또는 실시간 조회
    private List<StockPriceDto> getCachedOrFetchStockData(String symbol, String interval, String type) {
        String cacheKey = type + ":" + symbol + ":" + interval;
        Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
        
        if (cachedObject != null) {
            try {
                return objectMapper.convertValue(cachedObject, new com.fasterxml.jackson.core.type.TypeReference<List<StockPriceDto>>() {});
            } catch (Exception e) {
                log.warn("캐시된 주가 데이터 역직렬화 실패: {} - {}", cacheKey, e.getMessage());
            }
        }
        
        List<StockPriceDto> data = yahooFinanceApiService.getRealtimeStockData(symbol, interval);
        if (data != null && !data.isEmpty()) {
            redisTemplate.opsForValue().set(cacheKey, data, java.time.Duration.ofMinutes(2));
        }
        return data;
    }
    
    // 캐시된 거래량 데이터 조회 또는 실시간 조회
    private List<StockPriceDto> getCachedOrFetchVolumeData(String symbol, String interval) {
        String cacheKey = "volume:" + symbol + ":" + interval;
        Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
        
        if (cachedObject != null) {
            try {
                return objectMapper.convertValue(cachedObject, new com.fasterxml.jackson.core.type.TypeReference<List<StockPriceDto>>() {});
            } catch (Exception e) {
                log.warn("캐시된 거래량 데이터 역직렬화 실패: {} - {}", cacheKey, e.getMessage());
            }
        }
        
        List<StockPriceDto> data = yahooFinanceApiService.getVolumeData(symbol, interval);
        if (data != null && !data.isEmpty()) {
            redisTemplate.opsForValue().set(cacheKey, data, java.time.Duration.ofMinutes(2));
        }
        return data;
    }
    
    // 캐시된 요약 데이터 조회 또는 실시간 조회
    private StockSummaryDto getCachedOrFetchSummary(String symbol) {
        String cacheKey = "stock:" + symbol;
        Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
        
        if (cachedObject != null) {
            try {
                return objectMapper.convertValue(cachedObject, StockSummaryDto.class);
            } catch (Exception e) {
                log.warn("캐시된 요약 데이터 역직렬화 실패: {} - {}", cacheKey, e.getMessage());
            }
        }
        
        StockSummaryDto data = yahooFinanceApiService.getStockSummary(symbol);
        if (data != null) {
            redisTemplate.opsForValue().set(cacheKey, data, java.time.Duration.ofMinutes(2));
        }
        return data;
    }

}

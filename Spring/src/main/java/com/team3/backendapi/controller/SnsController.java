package com.team3.backendapi.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.team3.backendapi.dto.ApiResponse;
import com.team3.backendapi.dto.CacheMetadata;
import com.team3.backendapi.dto.CachedDataResponse;
import com.team3.backendapi.dto.sns.SnsPostDto;
import com.team3.backendapi.dto.sns.SnsResponseDto;
import com.team3.backendapi.service.sns.SnsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/sns")
@RequiredArgsConstructor
@Slf4j
@CrossOrigin(origins = "http://localhost:5173") // React 개발 서버 CORS 허용
public class SnsController {

    private final SnsService snsService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @GetMapping("/{symbol}")
    public Mono<ResponseEntity<ApiResponse<CachedDataResponse<SnsResponseDto>>>> getSnsData(@PathVariable String symbol) {
        log.info("SNS API 요청 받음: {}", symbol);
        
        // Redis에서 캐시된 Reddit 데이터 조회
        String cacheKey = "sns:" + symbol;
        String metadataKey = "metadata:sns:" + symbol;
        
        Object cachedObject = redisTemplate.opsForValue().get(cacheKey);
        Object metadataObject = redisTemplate.opsForValue().get(metadataKey);
        List<SnsPostDto> cachedRedditPosts = null;
        CacheMetadata metadata = null;
        
        if (cachedObject != null) {
            try {
                ObjectMapper objectMapper = new ObjectMapper();
                objectMapper.registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());
                cachedRedditPosts = objectMapper.convertValue(cachedObject, new TypeReference<List<SnsPostDto>>() {});
                
                if (metadataObject != null) {
                    metadata = objectMapper.convertValue(metadataObject, CacheMetadata.class);
                } else {
                    metadata = new CacheMetadata("sns", symbol, null);
                }
                
                log.info("캐시된 SNS 데이터 반환: {} - {}개 Reddit 포스트", symbol, cachedRedditPosts.size());
            } catch (Exception e) {
                log.warn("캐시된 SNS 데이터 변환 실패: {} - {}", symbol, e.getMessage());
                cachedRedditPosts = null;
                metadata = null;
            }
        }
        
        if (cachedRedditPosts != null) {
            // 캐시된 데이터 사용
            String stockName = getStockNameFromFile(symbol);
            List<SnsPostDto> dummyTweets = getDummyTweets(symbol, stockName);
            
            SnsResponseDto snsData = new SnsResponseDto(
                dummyTweets,
                cachedRedditPosts,
                stockName,
                symbol
            );
            
            final CacheMetadata finalMetadata = metadata;
            CachedDataResponse<SnsResponseDto> response = new CachedDataResponse<>(snsData, finalMetadata);
            return Mono.just(ResponseEntity.ok(ApiResponse.success("SNS 데이터를 성공적으로 조회했습니다.", response)));
        } else {
            // 캐시에 없으면 실시간 조회
            log.info("캐시에 없는 SNS 데이터 실시간 조회: {}", symbol);
            return snsService.getSnsData(symbol)
                    .doOnNext(data -> log.info("SNS 데이터 생성 완료: tweets={}, reddit={}", 
                        data.getTweets() != null ? data.getTweets().size() : 0,
                        data.getRedditPosts() != null ? data.getRedditPosts().size() : 0))
                    .map(snsData -> {
                        final CacheMetadata finalMetadata = new CacheMetadata("sns", symbol, null);
                        CachedDataResponse<SnsResponseDto> response = new CachedDataResponse<>(snsData, finalMetadata);
                        return ResponseEntity.ok(ApiResponse.success("SNS 데이터를 성공적으로 조회했습니다.", response));
                    })
                    .doOnNext(response -> log.info("SNS API 응답 전송 완료"))
                    .onErrorReturn(ResponseEntity.internalServerError().build());
        }
    }
    
    private String getStockNameFromFile(String symbol) {
        try {
            // sentiment_report.json 파일에서 주식 이름 조회
            String filePath = "data/raws/sentiment_report.json";
            File file = new File(filePath);
            
            if (!file.exists()) {
                log.warn("sentiment_report.json 파일을 찾을 수 없습니다: {}", filePath);
                return "알 수 없는 주식";
            }
            
            List<Map<String, Object>> data = objectMapper.readValue(file, new TypeReference<List<Map<String, Object>>>() {});
            
            for (Map<String, Object> item : data) {
                String stockCode = (String) item.get("stockCode");
                if (symbol.equals(stockCode)) {
                    return (String) item.get("stockName");
                }
            }
            
            log.warn("주식 코드 {}에 해당하는 이름을 찾을 수 없습니다", symbol);
            return "알 수 없는 주식";
            
        } catch (IOException e) {
            log.error("sentiment_report.json 파일 읽기 실패: {}", e.getMessage());
            return "알 수 없는 주식";
        }
    }
    
    private List<SnsPostDto> getDummyTweets(String symbol, String stockName) {
        // 기존 SnsService의 getDummyTweets 로직을 여기로 이동
        // 간단한 더미 데이터 반환
        return List.of(
            new SnsPostDto("1", "@StockNews", 
                stockName + " 관련 최신 뉴스가 업데이트되었습니다.", 
                "1시간 전", 500, 50, 0, "twitter", "https://twitter.com/StockNews/status/1234567890")
        );
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("SNS API is running");
    }
}

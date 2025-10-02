package com.team3.backendapi.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.team3.backendapi.dto.sns.SnsPostDto;
import com.team3.backendapi.service.sns.RedditApiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;

import java.io.File;
import java.io.IOException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

// @Service // SnsSchedulerService와 중복 방지를 위해 비활성화
@RequiredArgsConstructor
@Slf4j
public class ScheduledSnsDataService {
    
    private final RedditApiService redditApiService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
        
    // 5분마다 실행 (Reddit은 더 자주 업데이트될 필요 없음)
    @Scheduled(fixedRate = 300000)
    public void collectSnsData() {
        log.info("SNS 데이터 수집 시작");
        
        try {
            // sentiment_report.json에서 주식 목록 가져오기
            List<String> stockCodes = getStockCodesFromFile();
            
            for (String stockCode : stockCodes) {
                try {
                    String stockName = getStockNameFromFile(stockCode);
                    
                    // Reddit 데이터 수집 (Mono를 블로킹으로 변환)
                    List<SnsPostDto> redditPosts = redditApiService.getRedditPostsBySymbol(stockCode, stockName).block();
                    
                    if (redditPosts != null && !redditPosts.isEmpty()) {
                        // Redis에 캐시 저장 (10분 TTL)
                        String cacheKey = "sns:" + stockCode;
                        redisTemplate.opsForValue().set(cacheKey, redditPosts, Duration.ofMinutes(10));
                        
                        log.info("SNS 데이터 수집 완료: {} - {}개 Reddit 포스트", stockCode, redditPosts.size());
                    }
                } catch (Exception e) {
                    log.error("SNS 데이터 수집 실패: {} - {}", stockCode, e.getMessage());
                }
            }
            
            log.info("SNS 데이터 수집 완료 - 총 {}개 종목", stockCodes.size());
        } catch (Exception e) {
            log.error("SNS 데이터 수집 중 오류 발생: {}", e.getMessage());
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
    
    private List<String> getDefaultStockCodes() {
        // 기본 주식 코드들 (파일을 읽을 수 없을 때 사용)
        return List.of("005930", "000660", "035420", "207940", "006400");
    }
}

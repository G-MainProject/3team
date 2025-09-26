package com.team3.backendapi.service.sns;

import com.team3.backendapi.dto.CacheMetadata;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Map;

@Service // 활성화 - ScheduledSnsDataService와 역할 분리
@RequiredArgsConstructor
@Slf4j
public class SnsSchedulerService {

    private final RedditApiService redditApiService;
    private final RedisTemplate<String, Object> redisTemplate;
    
    // 인기 주식 심볼들
    private static final String[] POPULAR_SYMBOLS = {"005930", "000660", "035420", "207940", "006400"};
    
    // 주식 이름 매핑
    private static final Map<String, String> STOCK_NAMES = Map.of(
        "005930", "삼성전자",
        "000660", "SK하이닉스", 
        "035420", "NAVER",
        "207940", "삼성바이오로직스",
        "006400", "삼성SDI"
    );

    /**
     * 5분마다 인기 주식들의 SNS 데이터를 실시간 업데이트 (ScheduledSnsDataService와 중복 방지)
     */
    @Scheduled(fixedRate = 300000) // 5분 = 300,000ms (ScheduledSnsDataService와 동일)
    public void preloadSnsData() {
        log.info("인기 주식 SNS 데이터 업데이트 시작...");
        
        for (String symbol : POPULAR_SYMBOLS) {
            String stockName = STOCK_NAMES.get(symbol);
            if (stockName != null) {
                try {
                    // Reddit 데이터 실시간 업데이트 및 캐시 저장
                    redditApiService.getRedditPostsBySymbol(symbol, stockName)
                        .doOnSuccess(redditPosts -> {
                            if (redditPosts != null && !redditPosts.isEmpty()) {
                                // Redis에 캐시 저장 (10분 TTL)
                                String cacheKey = "sns:" + symbol;
                                String metadataKey = "metadata:sns:" + symbol;
                                CacheMetadata metadata = new CacheMetadata("sns", symbol, null);
                                
                                redisTemplate.opsForValue().set(cacheKey, redditPosts, Duration.ofMinutes(10));
                                redisTemplate.opsForValue().set(metadataKey, metadata, Duration.ofMinutes(10));
                                log.info("인기 주식 Reddit 데이터 업데이트 및 캐시 저장 완료: {} - {}개", stockName, redditPosts.size());
                            } else {
                                log.warn("인기 주식 Reddit 데이터가 비어있음: {}", stockName);
                            }
                        })
                        .doOnError(error -> log.error("인기 주식 Reddit 데이터 업데이트 실패: {} - {}", stockName, error.getMessage()))
                        .subscribe(
                            success -> {}, // 성공 시 추가 처리 없음
                            error -> log.error("Reddit API 구독 에러: {}", error.getMessage())
                        );
                } catch (Exception e) {
                    log.error("인기 주식 SNS 데이터 처리 중 오류: {} - {}", stockName, e.getMessage());
                }
            }
        }
        
        log.info("인기 주식 SNS 데이터 업데이트 완료");
    }

    /**
     * 1시간마다 캐시 정리 (만료된 데이터 제거)
     */
    @Scheduled(fixedRate = 3600000) // 1시간 = 3,600,000ms
    public void cleanupCache() {
        log.info("SNS 캐시 정리 시작...");
        // RedditApiService의 캐시 정리 로직이 필요
        log.info("SNS 캐시 정리 완료");
    }
}

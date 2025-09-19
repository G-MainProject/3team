package com.team3.backendapi.service.sns;

import com.team3.backendapi.dto.sns.SnsPostDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
@RequiredArgsConstructor
@Slf4j
public class SnsSchedulerService {

    private final RedditApiService redditApiService;
    
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
     * 1분마다 인기 주식들의 SNS 데이터를 실시간 업데이트
     */
    @Scheduled(fixedRate = 60000) // 1분 = 60,000ms
    public void preloadSnsData() {
        log.info("실시간 SNS 데이터 업데이트 시작...");
        
        for (String symbol : POPULAR_SYMBOLS) {
            String stockName = STOCK_NAMES.get(symbol);
            if (stockName != null) {
                // Reddit 데이터 실시간 업데이트 (캐시 무시)
                redditApiService.getRedditPostsBySymbol(symbol, stockName)
                    .doOnSuccess(redditPosts -> log.info("실시간 Reddit 데이터 업데이트 완료: {} - {}개", stockName, redditPosts.size()))
                    .doOnError(error -> log.error("실시간 Reddit 데이터 업데이트 실패: {} - {}", stockName, error.getMessage()))
                    .subscribe();
            }
        }
        
        log.info("실시간 SNS 데이터 업데이트 완료");
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

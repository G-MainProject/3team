package com.team3.backendapi.service.sns;

import com.team3.backendapi.dto.sns.SnsPostDto;
import com.team3.backendapi.dto.sns.SnsResponseDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class SnsService {

    private final TwitterApiService twitterApiService;
    private final RedditApiService redditApiService;

    private static final Map<String, String> STOCK_NAMES = new HashMap<>();
    
    static {
        STOCK_NAMES.put("005930", "삼성전자");
        STOCK_NAMES.put("000660", "SK하이닉스");
        STOCK_NAMES.put("035420", "NAVER");
        STOCK_NAMES.put("207940", "삼성바이오로직스");
        STOCK_NAMES.put("006400", "삼성SDI");
    }

    public Mono<SnsResponseDto> getSnsData(String symbol) {
        String stockName = STOCK_NAMES.getOrDefault(symbol, "알 수 없는 주식");
        
        log.info("SNS 데이터 요청 시작: {} ({})", stockName, symbol);

        // Twitter와 Reddit 데이터를 병렬로 가져오기
        Mono<java.util.List<SnsPostDto>> tweetsMono = twitterApiService.getTweetsBySymbol(symbol, stockName)
                .doOnNext(tweets -> log.info("Twitter 데이터 수집 완료: {}개", tweets.size()))
                .doOnError(error -> log.error("Twitter 데이터 수집 실패: {}", error.getMessage()));

        Mono<java.util.List<SnsPostDto>> redditMono = redditApiService.getRedditPostsBySymbol(symbol, stockName)
                .doOnNext(redditPosts -> log.info("Reddit 데이터 수집 완료: {}개", redditPosts.size()))
                .doOnError(error -> log.error("Reddit 데이터 수집 실패: {}", error.getMessage()));

        return Mono.zip(tweetsMono, redditMono)
                .map(tuple -> {
                    java.util.List<SnsPostDto> tweets = tuple.getT1();
                    java.util.List<SnsPostDto> redditPosts = tuple.getT2();
                    
                    log.info("SNS 데이터 조합 중: tweets={}개, reddit={}개", 
                        tweets.size(), redditPosts.size());
                    return new SnsResponseDto(tweets, redditPosts, stockName, symbol);
                })
                .doOnSuccess(response -> 
                    log.info("SNS 데이터 로드 완료: {} - Twitter: {}개, Reddit: {}개", 
                        stockName, response.getTweets().size(), response.getRedditPosts().size()))
                .doOnError(error -> 
                    log.error("SNS 데이터 로드 실패: {} - {}", symbol, error.getMessage()));
    }
}

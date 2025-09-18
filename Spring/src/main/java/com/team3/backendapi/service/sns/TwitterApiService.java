package com.team3.backendapi.service.sns;

import com.team3.backendapi.dto.sns.SnsPostDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Service
@Slf4j
public class TwitterApiService {

    private final WebClient webClient;
    
    // 캐시 저장소 (심볼 -> 캐시 데이터)
    private final ConcurrentHashMap<String, CacheData> cache = new ConcurrentHashMap<>();
    
    // 캐시 유효 시간 (15분)
    private static final int CACHE_DURATION_MINUTES = 15;
    
    public TwitterApiService(@Qualifier("twitterWebClient") WebClient webClient) {
        this.webClient = webClient;
    }
    
    @Value("${twitter.api.bearer-token:}")
    private String bearerToken;
    
    @Value("${twitter.api.base-url:https://api.twitter.com/2}")
    private String baseUrl;
    
    // 캐시 데이터 클래스
    private static class CacheData {
        private final List<SnsPostDto> tweets;
        private final LocalDateTime timestamp;
        
        public CacheData(List<SnsPostDto> tweets) {
            this.tweets = tweets;
            this.timestamp = LocalDateTime.now();
        }
        
        public List<SnsPostDto> getTweets() {
            return tweets;
        }
        
        public boolean isExpired() {
            return LocalDateTime.now().isAfter(timestamp.plusMinutes(CACHE_DURATION_MINUTES));
        }
    }

    public Mono<List<SnsPostDto>> getTweetsBySymbol(String symbol, String stockName) {
        // 캐시 확인
        CacheData cachedData = cache.get(symbol);
        if (cachedData != null && !cachedData.isExpired()) {
            log.info("캐시에서 Twitter 데이터를 반환합니다. (심볼: {})", symbol);
            return Mono.just(cachedData.getTweets());
        }

        if (bearerToken == null || bearerToken.isEmpty()) {
            log.warn("Twitter Bearer Token이 설정되지 않았습니다. 더미 데이터를 반환합니다.");
            List<SnsPostDto> dummyTweets = getDummyTweets(symbol, stockName);
            cache.put(symbol, new CacheData(dummyTweets));
            return Mono.just(dummyTweets);
        }

        // 실제 API 호출 시도
        String query = buildQuery(symbol, stockName);
        log.info("Twitter API 호출 시작: query={}", query);
        
        return webClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/tweets/search/recent")
                        .queryParam("query", query)
                        .queryParam("max_results", 5)
                        .queryParam("tweet.fields", "created_at,public_metrics,author_id")
                        .queryParam("user.fields", "username")
                        .queryParam("expansions", "author_id")
                        .build())
                .header("Authorization", "Bearer " + bearerToken)
                .retrieve()
                .bodyToMono(String.class)
                .doOnNext(response -> log.info("Twitter API 응답: {}", response))
                .map(this::parseTwitterResponse)
                .doOnNext(tweets -> {
                    log.info("파싱된 트윗 수: {}", tweets.size());
                    // API 성공 시 캐시에 저장
                    cache.put(symbol, new CacheData(tweets));
                })
                .onErrorResume(throwable -> {
                    log.error("Twitter API 호출 실패: {}", throwable.getMessage(), throwable);
                    // API 실패 시 더미 데이터 생성 및 캐시 저장
                    List<SnsPostDto> dummyTweets = getDummyTweets(symbol, stockName);
                    cache.put(symbol, new CacheData(dummyTweets));
                    return Mono.just(dummyTweets);
                });
    }

    private String buildQuery(String symbol, String stockName) {
        return String.format("(%s OR %s) -is:retweet lang:ko", symbol, stockName);
    }

    private List<SnsPostDto> parseTwitterResponse(String response) {
        try {
            // Jackson ObjectMapper를 사용하여 JSON 파싱
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            com.fasterxml.jackson.databind.JsonNode rootNode = mapper.readTree(response);
            
            List<SnsPostDto> tweets = new ArrayList<>();
            
            if (rootNode.has("data")) {
                com.fasterxml.jackson.databind.JsonNode dataArray = rootNode.get("data");
                com.fasterxml.jackson.databind.JsonNode usersArray = rootNode.has("includes") && rootNode.get("includes").has("users") 
                    ? rootNode.get("includes").get("users") : null;
                
                for (com.fasterxml.jackson.databind.JsonNode tweetNode : dataArray) {
                    String tweetId = tweetNode.get("id").asText();
                    String text = tweetNode.get("text").asText();
                    String authorId = tweetNode.get("author_id").asText();
                    String createdAt = tweetNode.get("created_at").asText();
                    
                    // 사용자 정보 찾기
                    String username = "@unknown";
                    if (usersArray != null) {
                        for (com.fasterxml.jackson.databind.JsonNode userNode : usersArray) {
                            if (userNode.get("id").asText().equals(authorId)) {
                                username = "@" + userNode.get("username").asText();
                                break;
                            }
                        }
                    }
                    
                    // 공개 메트릭스
                    int likes = 0, retweets = 0, replies = 0;
                    if (tweetNode.has("public_metrics")) {
                        com.fasterxml.jackson.databind.JsonNode metrics = tweetNode.get("public_metrics");
                        likes = metrics.has("like_count") ? metrics.get("like_count").asInt() : 0;
                        retweets = metrics.has("retweet_count") ? metrics.get("retweet_count").asInt() : 0;
                        replies = metrics.has("reply_count") ? metrics.get("reply_count").asInt() : 0;
                    }
                    
                    // 시간 포맷팅
                    String timeAgo = formatTimeAgo(createdAt);
                    
                    tweets.add(new SnsPostDto(tweetId, username, text, timeAgo, likes, retweets, replies, "twitter"));
                }
            }
            
            log.info("Twitter API에서 {}개의 트윗을 파싱했습니다.", tweets.size());
            return tweets;
            
        } catch (Exception e) {
            log.error("Twitter API 응답 파싱 실패: {}", e.getMessage());
            return new ArrayList<>();
        }
    }
    
    private String formatTimeAgo(String createdAt) {
        try {
            // Twitter API 시간 형식: "2024-01-15T14:30:00.000Z"
            java.time.Instant instant = java.time.Instant.parse(createdAt);
            java.time.Duration duration = java.time.Duration.between(instant, java.time.Instant.now());
            
            long hours = duration.toHours();
            if (hours < 1) {
                long minutes = duration.toMinutes();
                return minutes + "분 전";
            } else if (hours < 24) {
                return hours + "시간 전";
            } else {
                long days = duration.toDays();
                return days + "일 전";
            }
        } catch (Exception e) {
            return "방금 전";
        }
    }

    private List<SnsPostDto> getDummyTweets(String symbol, String stockName) {
        List<SnsPostDto> tweets = new ArrayList<>();
        
        // 심볼별 더미 데이터 생성
        switch (symbol) {
            case "005930":
                tweets.add(new SnsPostDto("1", "@SamsungNews", 
                    "삼성전자, 3분기 실적 발표... AI 반도체 수요 증가로 긍정적 전망", 
                    "2시간 전", 1240, 89, 0, "twitter"));
                tweets.add(new SnsPostDto("2", "@TechAnalyst", 
                    "삼성전자 메모리 반도체 기술력이 업계를 선도하고 있다. 특히 HBM 기술에서...", 
                    "4시간 전", 892, 156, 0, "twitter"));
                break;
            case "000660":
                tweets.add(new SnsPostDto("1", "@SKHynixNews", 
                    "SK하이닉스, HBM3E 메모리 대량 생산 시작... AI 서버 수요 급증으로 호재", 
                    "1시간 전", 1567, 123, 0, "twitter"));
                break;
            case "035420":
                tweets.add(new SnsPostDto("1", "@NaverTech", 
                    "네이버, AI 검색 기술 혁신으로 사용자 경험 대폭 개선", 
                    "2시간 전", 2100, 189, 0, "twitter"));
                break;
            default:
                tweets.add(new SnsPostDto("1", "@StockNews", 
                    stockName + " 관련 최신 뉴스가 업데이트되었습니다.", 
                    "1시간 전", 500, 50, 0, "twitter"));
        }
        
        return tweets;
    }
}

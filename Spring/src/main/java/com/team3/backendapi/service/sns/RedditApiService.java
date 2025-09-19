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
public class RedditApiService {

    private final WebClient webClient;
    
    // 캐시 저장소 (심볼 -> 캐시 데이터)
    private final ConcurrentHashMap<String, CacheData> cache = new ConcurrentHashMap<>();
    
    // 캐시 유효 시간 (1분) - 테스트용
    private static final int CACHE_DURATION_MINUTES = 1;
    
    // 환경 변수 직접 읽기
    private String clientId;
    private String clientSecret;
    
    public RedditApiService(@Qualifier("redditWebClient") WebClient webClient) {
        this.webClient = webClient;
        // 캐시 초기화
        cache.clear();
        
        // 하드코딩된 Reddit API 키 사용 (테스트용)
        clientId = "JIq0Fy3dFM8srHgo_UJadg";
        clientSecret = "u08v6NPMr-13DMZWKQqxny4i4iYYMg";
        log.info("Reddit API 키 하드코딩 사용: Client ID={}, Secret={}", 
            clientId.substring(0, 10) + "...", 
            clientSecret.substring(0, 10) + "...");
        
        log.info("Reddit API 서비스 초기화 - 캐시 클리어됨");
        log.info("Reddit API 초기화 - Client ID: '{}', Client Secret: '{}'", 
            clientId != null ? clientId.substring(0, Math.min(clientId.length(), 10)) + "..." : "null",
            clientSecret != null ? clientSecret.substring(0, Math.min(clientSecret.length(), 10)) + "..." : "null");
    }
    
    @Value("${reddit.api.user-agent:StockAnalysisBot/1.0}")
    private String userAgent;
    
    // 캐시 데이터 클래스
    private static class CacheData {
        private final List<SnsPostDto> posts;
        private final LocalDateTime timestamp;
        
        public CacheData(List<SnsPostDto> posts) {
            this.posts = posts;
            this.timestamp = LocalDateTime.now();
        }
        
        public List<SnsPostDto> getPosts() {
            return posts;
        }
        
        public boolean isExpired() {
            return LocalDateTime.now().isAfter(timestamp.plusMinutes(CACHE_DURATION_MINUTES));
        }
    }

    public Mono<List<SnsPostDto>> getRedditPostsBySymbol(String symbol, String stockName) {
        // 캐시 비활성화 (테스트용)
        log.info("Reddit API 호출 시작 - 캐시 무시");

        if (clientId == null || clientId.isEmpty() || clientSecret == null || clientSecret.isEmpty()) {
            log.warn("Reddit API 자격 증명이 설정되지 않았습니다. 더미 데이터를 반환합니다.");
            log.warn("Client ID: '{}', Client Secret: '{}'", clientId, clientSecret);
            List<SnsPostDto> dummyPosts = getDummyRedditPosts(symbol, stockName);
            cache.put(symbol, new CacheData(dummyPosts));
            return Mono.just(dummyPosts);
        }
        
        log.info("Reddit API 자격 증명 확인됨. 실제 API 호출을 시작합니다.");

        // Reddit API 호출
        String query = buildQuery(symbol, stockName);
        log.info("Reddit API 호출 시작: query={}", query);
        
        return getRedditAccessToken()
                .flatMap(accessToken -> 
                    webClient.get()
                            .uri(uriBuilder -> uriBuilder
                                    .path("/search.json")
                                    .queryParam("q", query)
                                    .queryParam("sort", "new")
                                    .queryParam("limit", 20)
                                    .queryParam("t", "week")
                                    .build())
                            .header("Authorization", "Bearer " + accessToken)
                            .header("User-Agent", userAgent)
                            .retrieve()
                            .bodyToMono(String.class)
                            .doOnNext(response -> log.info("Reddit API 응답: {}", response))
                            .map(this::parseRedditResponse)
                            .doOnNext(posts -> {
                                log.info("파싱된 Reddit 게시물 수: {}", posts.size());
                                // API 성공 시 캐시에 저장
                                cache.put(symbol, new CacheData(posts));
                            })
                            .onErrorResume(throwable -> {
                                log.error("Reddit API 호출 실패: {}", throwable.getMessage(), throwable);
                                // API 실패 시 더미 데이터 생성 및 캐시 저장
                                List<SnsPostDto> dummyPosts = getDummyRedditPosts(symbol, stockName);
                                cache.put(symbol, new CacheData(dummyPosts));
                                return Mono.just(dummyPosts);
                            })
                );
    }

    private Mono<String> getRedditAccessToken() {
        // Basic Authentication을 위한 Base64 인코딩
        String credentials = clientId + ":" + clientSecret;
        String encodedCredentials = java.util.Base64.getEncoder().encodeToString(credentials.getBytes());
        
        return webClient.post()
                .uri("/api/v1/access_token")
                .header("User-Agent", userAgent)
                .header("Authorization", "Basic " + encodedCredentials)
                .header("Content-Type", "application/x-www-form-urlencoded")
                .bodyValue("grant_type=client_credentials")
                .retrieve()
                .bodyToMono(String.class)
                .doOnNext(response -> log.info("Reddit 액세스 토큰 응답: {}", response))
                .map(response -> {
                    try {
                        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
                        com.fasterxml.jackson.databind.JsonNode rootNode = mapper.readTree(response);
                        return rootNode.get("access_token").asText();
                    } catch (Exception e) {
                        log.error("Reddit 액세스 토큰 파싱 실패: {}", e.getMessage());
                        throw new RuntimeException("액세스 토큰 획득 실패", e);
                    }
                });
    }

    private String buildQuery(String symbol, String stockName) {
        // 종목별 최적화된 검색 키워드
        String searchTerms;
        switch (symbol) {
            case "005930":
                searchTerms = "(005930 OR Samsung OR 삼성전자 OR Samsung Electronics)";
                break;
            case "000660":
                searchTerms = "(000660 OR SK Hynix OR SK하이닉스 OR SKHynix)";
                break;
            case "035420":
                searchTerms = "(035420 OR Naver OR 네이버 OR NAVER)";
                break;
            case "207940":
                searchTerms = "(207940 OR Samsung Biologics OR 삼성바이오로직스 OR SamsungBio)";
                break;
            case "006400":
                searchTerms = "(006400 OR Samsung SDI OR 삼성SDI OR SamsungSDI)";
                break;
            default:
                searchTerms = String.format("(%s OR %s)", symbol, stockName);
        }
        
        // 관련 서브레딧들
        String subreddits = "subreddit:stocks OR subreddit:investing OR subreddit:SecurityAnalysis OR subreddit:ValueInvesting OR subreddit:StockMarket OR subreddit:korea OR subreddit:KoreanInvesting";
        
        return String.format("%s (%s)", searchTerms, subreddits);
    }


    private List<SnsPostDto> parseRedditResponse(String response) {
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            com.fasterxml.jackson.databind.JsonNode rootNode = mapper.readTree(response);
            
            List<SnsPostDto> posts = new ArrayList<>();
            
            if (rootNode.has("data") && rootNode.get("data").has("children")) {
                com.fasterxml.jackson.databind.JsonNode children = rootNode.get("data").get("children");
                
                for (com.fasterxml.jackson.databind.JsonNode child : children) {
                    if (child.has("data")) {
                        com.fasterxml.jackson.databind.JsonNode data = child.get("data");
                        
                        String postId = data.get("id").asText();
                        String title = data.get("title").asText();
                        String selftext = data.has("selftext") ? data.get("selftext").asText() : "";
                        String content = title + (selftext.isEmpty() ? "" : "\n\n" + selftext);
                        
                        String author = "u/" + data.get("author").asText();
                        String subreddit = "r/" + data.get("subreddit").asText();
                        String authorWithSub = author + " (" + subreddit + ")";
                        
                        // Reddit 링크 생성
                        String permalink = data.has("permalink") ? data.get("permalink").asText() : "";
                        String redditUrl = "https://www.reddit.com" + permalink;
                        
                        // 점수 (upvotes - downvotes)
                        int score = data.has("score") ? data.get("score").asInt() : 0;
                        int numComments = data.has("num_comments") ? data.get("num_comments").asInt() : 0;
                        
                        // 시간 포맷팅
                        double createdUtc = data.has("created_utc") ? data.get("created_utc").asDouble() : 0;
                        String timeAgo = formatTimeAgo(createdUtc);
                        
                        posts.add(new SnsPostDto(postId, authorWithSub, content, timeAgo, score, 0, numComments, "reddit", redditUrl));
                    }
                }
            }
            
            log.info("Reddit API에서 {}개의 게시물을 파싱했습니다.", posts.size());
            return posts;
            
        } catch (Exception e) {
            log.error("Reddit API 응답 파싱 실패: {}", e.getMessage());
            return new ArrayList<>();
        }
    }
    
    private String formatTimeAgo(double createdUtc) {
        try {
            long currentTime = System.currentTimeMillis() / 1000;
            long postTime = (long) createdUtc;
            long diffSeconds = currentTime - postTime;
            
            if (diffSeconds < 3600) {
                return (diffSeconds / 60) + "분 전";
            } else if (diffSeconds < 86400) {
                return (diffSeconds / 3600) + "시간 전";
            } else {
                return (diffSeconds / 86400) + "일 전";
            }
        } catch (Exception e) {
            return "방금 전";
        }
    }

    private List<SnsPostDto> getDummyRedditPosts(String symbol, String stockName) {
        List<SnsPostDto> posts = new ArrayList<>();
        
        // 심볼별 더미 데이터 생성
        switch (symbol) {
            case "005930":
                posts.add(new SnsPostDto("1", "u/StockAnalyst (r/stocks)", 
                    "삼성전자 주가 분석: AI 반도체 수요 증가로 긍정적 전망\n\n최근 삼성전자의 AI 반도체 사업이 주목받고 있습니다...", 
                    "2시간 전", 45, 0, 12, "reddit", "https://www.reddit.com/r/stocks/"));
                posts.add(new SnsPostDto("2", "u/Investor123 (r/investing)", 
                    "삼성전자 투자 의견: 현재 시점에서의 매수/매도 전략", 
                    "4시간 전", 23, 0, 8, "reddit", "https://www.reddit.com/r/investing/"));
                break;
            case "000660":
                posts.add(new SnsPostDto("1", "u/MemoryExpert (r/SecurityAnalysis)", 
                    "SK하이닉스 HBM 기술력 분석: 삼성전자와의 경쟁 구도", 
                    "1시간 전", 67, 0, 15, "reddit", "https://www.reddit.com/r/SecurityAnalysis/"));
                break;
            case "035420":
                posts.add(new SnsPostDto("1", "u/TechInvestor (r/stocks)", 
                    "네이버 AI 기술 투자 전망: 검색 시장에서의 경쟁력", 
                    "3시간 전", 34, 0, 6, "reddit", "https://www.reddit.com/r/stocks/"));
                break;
            default:
                posts.add(new SnsPostDto("1", "u/StockNews (r/investing)", 
                    stockName + " 관련 최신 분석 및 투자 의견", 
                    "1시간 전", 15, 0, 3, "reddit", "https://www.reddit.com/r/investing/"));
        }
        
        return posts;
    }
}

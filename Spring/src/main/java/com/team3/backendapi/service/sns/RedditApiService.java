package com.team3.backendapi.service.sns;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.team3.backendapi.dto.sns.SnsPostDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.io.File;
import java.time.LocalDateTime;
import java.util.*;
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
                                    .queryParam("sort", "relevance")
                                    .queryParam("limit", 50)
                                    .queryParam("t", "month")
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
        // sentiment_report.json에서 실제 데이터를 읽어와서 검색 키워드 생성
        StringBuilder searchTerms = new StringBuilder();
        searchTerms.append("(").append(symbol).append(" OR ").append(stockName);
        
        // sentiment_report.json에서 해당 종목의 키워드 정보 가져오기
        try {
            List<String> keywords = getKeywordsFromSentimentReport(symbol);
            if (keywords != null && !keywords.isEmpty()) {
                for (String keyword : keywords) {
                    if (keyword != null && !keyword.trim().isEmpty()) {
                        searchTerms.append(" OR ").append(keyword.trim());
                    }
                }
            }
        } catch (Exception e) {
            log.warn("sentiment_report.json에서 키워드를 가져오는 중 오류 발생: {}", e.getMessage());
        }
        
        searchTerms.append(")");
        
        // 서브레딧 제한 없이 전체 Reddit에서 검색 (더 많은 결과를 위해)
        String finalQuery = searchTerms.toString();
        
        log.info("동적 검색 쿼리 생성: {} -> {}", symbol, finalQuery);
        return finalQuery;
    }
    
    // sentiment_report.json에서 해당 종목의 키워드 정보 가져오기
    private List<String> getKeywordsFromSentimentReport(String symbol) {
        try {
            // sentiment_report.json 파일 경로
            String filePath = "../data/raws/sentiment_report.json";
            File file = new File(filePath);
            
            if (!file.exists()) {
                log.warn("sentiment_report.json 파일을 찾을 수 없습니다: {}", filePath);
                return new ArrayList<>();
            }
            
            // JSON 파일 읽기
            ObjectMapper objectMapper = new ObjectMapper();
            List<Map<String, Object>> data = objectMapper.readValue(file, new TypeReference<List<Map<String, Object>>>() {});
            
            // 해당 종목 코드로 데이터 찾기
            for (Map<String, Object> item : data) {
                String stockCode = (String) item.get("stockCode");
                if (symbol.equals(stockCode)) {
                    Map<String, Object> keywordAnalysis = (Map<String, Object>) item.get("keywordAnalysis");
                    if (keywordAnalysis != null) {
                        Map<String, Object> wordCloud = (Map<String, Object>) keywordAnalysis.get("wordCloud");
                        if (wordCloud != null) {
                            List<String> keywords = new ArrayList<>();
                            // 상위 10개 키워드만 가져오기 (너무 많으면 검색이 비효율적)
                            wordCloud.entrySet().stream()
                                .sorted((e1, e2) -> {
                                    Object v1 = e1.getValue();
                                    Object v2 = e2.getValue();
                                    if (v1 instanceof Number && v2 instanceof Number) {
                                        double d1 = ((Number) v1).doubleValue();
                                        double d2 = ((Number) v2).doubleValue();
                                        return Double.compare(d2, d1); // 내림차순 정렬
                                    }
                                    return 0;
                                })
                                .limit(10)
                                .forEach(entry -> keywords.add(entry.getKey()));
                            
                            log.info("종목 {}의 키워드 {}개를 sentiment_report.json에서 가져왔습니다: {}", 
                                symbol, keywords.size(), keywords);
                            return keywords;
                        }
                    }
                    break;
                }
            }
            
            log.warn("종목 코드 {}에 해당하는 데이터를 sentiment_report.json에서 찾을 수 없습니다.", symbol);
            return new ArrayList<>();
            
        } catch (Exception e) {
            log.error("sentiment_report.json 파일 읽기 실패: {}", e.getMessage());
            return new ArrayList<>();
        }
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

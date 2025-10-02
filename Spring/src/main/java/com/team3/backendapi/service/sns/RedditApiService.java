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
        if (clientId == null || clientId.isEmpty() || clientSecret == null || clientSecret.isEmpty()) {
            log.warn("Reddit API 자격 증명이 설정되지 않았습니다. 더미 데이터를 반환합니다.");
            List<SnsPostDto> dummyPosts = getDummyRedditPosts(symbol, stockName);
            cache.put(symbol, new CacheData(dummyPosts));
            return Mono.just(dummyPosts);
        }

        // Reddit API 호출
        String query = buildQuery(symbol, stockName);
        
        return getRedditAccessToken()
                .flatMap(accessToken -> 
                    webClient.get()
                            .uri(uriBuilder -> uriBuilder
                                    .path("/search.json")
                                    .queryParam("q", query)
                                    .queryParam("sort", "relevance")
                                    .queryParam("limit", 10)
                                    .queryParam("t", "week")
                                    .build())
                            .header("Authorization", "Bearer " + accessToken)
                            .header("User-Agent", userAgent)
                            .retrieve()
                            .bodyToMono(String.class)
                            .map(this::parseRedditResponse)
                            .doOnNext(posts -> {
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
        // 주식 관련 서브레딧에서만 검색하도록 제한
        StringBuilder searchTerms = new StringBuilder();
        
        // 1. 기업명과 종목코드를 우선적으로 사용 (정확한 매칭)
        searchTerms.append("(").append(symbol).append(" OR \"").append(stockName).append("\"");
        
        // 2. JSON에서 영어 이름 가져오기 (Reddit에서 더 많이 사용될 수 있음)
        String englishName = getEnglishNameFromJson(symbol);
        if (englishName != null && !englishName.isEmpty()) {
            searchTerms.append(" OR \"").append(englishName).append("\"");
        }
        
        // 3. sentiment_report.json에서 구체적인 키워드만 선별적으로 사용
        try {
            List<String> keywords = getKeywordsFromSentimentReport(symbol);
            if (keywords != null && !keywords.isEmpty()) {
                // 구체적이고 특화된 키워드만 선별
                for (String keyword : keywords) {
                    if (keyword != null && !keyword.trim().isEmpty()) {
                        // 구체적이고 특화된 키워드만 사용 (일반적인 키워드 제외)
                        if (isSpecificKeyword(keyword)) {
                            searchTerms.append(" OR \"").append(keyword.trim()).append("\"");
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("sentiment_report.json에서 키워드를 가져오는 중 오류 발생: {}", e.getMessage());
        }
        
        searchTerms.append(")");
        
        // 주식 관련 서브레딧으로 제한
        String subreddits = "subreddit:stocks OR subreddit:investing OR subreddit:SecurityAnalysis OR subreddit:ValueInvesting OR subreddit:StockMarket OR subreddit:korea OR subreddit:KoreanInvesting";
        
        String finalQuery = String.format("%s (%s)", searchTerms.toString(), subreddits);
        
        return finalQuery;
    }
    
    // JSON에서 영어 이름 가져오기
    private String getEnglishNameFromJson(String symbol) {
        try {
            String filePath = "../data/raws/sentiment_report.json";
            File file = new File(filePath);
            
            if (!file.exists()) {
                log.warn("sentiment_report.json 파일을 찾을 수 없습니다: {}", filePath);
                return null;
            }
            
            ObjectMapper objectMapper = new ObjectMapper();
            List<Map<String, Object>> data = objectMapper.readValue(file, new TypeReference<List<Map<String, Object>>>() {});
            
            for (Map<String, Object> item : data) {
                String stockCode = (String) item.get("stockCode");
                if (symbol.equals(stockCode)) {
                    String englishName = (String) item.get("stockNameEn");
                    if (englishName != null && !englishName.trim().isEmpty()) {
                        return englishName;
                    }
                    break;
                }
            }
            
            log.warn("종목 코드 {}에 해당하는 영어 이름을 sentiment_report.json에서 찾을 수 없습니다.", symbol);
            return null;
            
        } catch (Exception e) {
            log.error("sentiment_report.json에서 영어 이름 읽기 실패: {}", e.getMessage());
            return null;
        }
    }
    
    // 구체적이고 특화된 키워드인지 확인 (일반적인 키워드 제외)
    private boolean isSpecificKeyword(String keyword) {
        // 일반적인 키워드들 (제외할 키워드)
        String[] genericKeywords = {
            "사업", "재해", "기업", "기술", "친환경", "주가", "투자", "선박", "종목", "수소", "국제", "평가",
            "LNG", "환경", "경제", "시장", "분석", "전망", "성장", "개발", "회사", "업체", "기관", "단체"
        };
        
        for (String generic : genericKeywords) {
            if (keyword.contains(generic)) {
                return false; // 일반적인 키워드는 제외
            }
        }
        
        // 구체적인 키워드들 (포함할 키워드)
        String[] specificKeywords = {
            "우진", "코오롱", "모빌리티", "화인", "베스틸", "주성", "코퍼레이션",
            "삼성", "SK", "하이닉스", "네이버", "LG", "현대", "기아", "카카오"
        };
        
        for (String specific : specificKeywords) {
            if (keyword.contains(specific)) {
                return true; // 구체적인 키워드는 포함
            }
        }
        
        // 길이가 3자 이상이고 구체적인 내용을 담고 있는 키워드
        return keyword.length() >= 3 && !keyword.matches(".*[0-9]+.*");
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
                        
                        String postId = data.has("id") ? data.get("id").asText() : "unknown";
                        String title = data.has("title") ? data.get("title").asText() : "제목 없음";
                        String selftext = data.has("selftext") ? data.get("selftext").asText() : "";
                        String content = title + (selftext.isEmpty() ? "" : "\n\n" + selftext);
                        
                        String author = data.has("author") ? "u/" + data.get("author").asText() : "u/unknown";
                        String subreddit = data.has("subreddit") ? "r/" + data.get("subreddit").asText() : "r/unknown";
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
            } else {
                log.warn("Reddit API 응답에 예상된 구조가 없습니다.");
            }
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

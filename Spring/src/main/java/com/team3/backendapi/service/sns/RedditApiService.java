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
        // 동적으로 검색 키워드 생성
        StringBuilder searchTerms = new StringBuilder();
        searchTerms.append("(").append(symbol).append(" OR ").append(stockName);
        
        // 주식명에서 영문명 추출 시도 (괄호 안의 영문명)
        String englishName = extractEnglishName(stockName);
        if (englishName != null && !englishName.isEmpty()) {
            searchTerms.append(" OR ").append(englishName);
        }
        
        // 주식명의 영문 변환 시도
        String romanizedName = romanizeKorean(stockName);
        if (romanizedName != null && !romanizedName.isEmpty() && !romanizedName.equals(stockName)) {
            searchTerms.append(" OR ").append(romanizedName);
        }
        
        searchTerms.append(")");
        
        // 관련 서브레딧들
        String subreddits = "subreddit:stocks OR subreddit:investing OR subreddit:SecurityAnalysis OR subreddit:ValueInvesting OR subreddit:StockMarket OR subreddit:korea OR subreddit:KoreanInvesting";
        
        String finalQuery = String.format("%s (%s)", searchTerms.toString(), subreddits);
        
        log.info("동적 검색 쿼리 생성: {} -> {}", symbol, finalQuery);
        return finalQuery;
    }
    
    // 주식명에서 영문명 추출 (예: "삼성전자(Samsung Electronics)" -> "Samsung Electronics")
    private String extractEnglishName(String stockName) {
        if (stockName == null) return null;
        
        int openParen = stockName.indexOf('(');
        int closeParen = stockName.indexOf(')');
        
        if (openParen != -1 && closeParen != -1 && closeParen > openParen) {
            return stockName.substring(openParen + 1, closeParen).trim();
        }
        
        return null;
    }
    
    // 한글을 로마자로 변환 (간단한 매핑)
    private String romanizeKorean(String korean) {
        if (korean == null) return null;
        
        // 간단한 한글-로마자 매핑 (주요 기업명)
        switch (korean) {
            case "삼성전자":
                return "Samsung Electronics";
            case "SK하이닉스":
                return "SK Hynix";
            case "네이버":
                return "Naver";
            case "삼성바이오로직스":
                return "Samsung Biologics";
            case "삼성SDI":
                return "Samsung SDI";
            case "우진":
                return "Woojin";
            case "LG전자":
                return "LG Electronics";
            case "현대차":
                return "Hyundai Motor";
            case "기아":
                return "Kia";
            case "카카오":
                return "Kakao";
            case "LG화학":
                return "LG Chem";
            case "POSCO":
                return "POSCO";
            case "한국전력":
                return "KEPCO";
            case "KB금융":
                return "KB Financial";
            case "신한지주":
                return "Shinhan Financial";
            case "하나금융":
                return "Hana Financial";
            case "LG에너지솔루션":
                return "LG Energy Solution";
            case "SK텔레콤":
                return "SK Telecom";
            case "KT":
                return "KT";
            case "LG":
                return "LG";
            case "CJ":
                return "CJ";
            case "롯데":
                return "Lotte";
            case "두산":
                return "Doosan";
            case "한화":
                return "Hanwha";
            case "GS":
                return "GS";
            case "현대중공업":
                return "Hyundai Heavy Industries";
            case "대한항공":
                return "Korean Air";
            case "아시아나항공":
                return "Asiana Airlines";
            case "한진":
                return "Hanjin";
            case "SK":
                return "SK";
            case "넷마블":
                return "Netmarble";
            case "NC소프트":
                return "NCsoft";
            case "크래프톤":
                return "Krafton";
            case "펄어비스":
                return "Pearl Abyss";
            case "위메이드":
                return "Wemade";
            case "컴투스":
                return "Com2uS";
            case "데브시스터즈":
                return "Devsisters";
            case "스마일게이트":
                return "Smilegate";
            case "넥슨":
                return "Nexon";
            case "에이치엠엠":
                return "HMM";
            case "팬오션":
                return "Pan Ocean";
            case "현대글로비스":
                return "Hyundai Glovis";
            case "CJ대한통운":
                return "CJ Logistics";
            case "한진해운":
                return "Hanjin Shipping";
            case "현대상선":
                return "Hyundai Merchant Marine";
            case "SK해운":
                return "SK Shipping";
            case "대한해운":
                return "Korea Line";
            case "팬오션글로벌":
                return "Pan Ocean Global";
            case "현대오일뱅크":
                return "Hyundai Oilbank";
            case "SK이노베이션":
                return "SK Innovation";
            case "GS칼텍스":
                return "GS Caltex";
            case "S-Oil":
                return "S-Oil";
            case "현대모비스":
                return "Hyundai Mobis";
            case "만도":
                return "Mando";
            case "한라":
                return "Halla";
            case "현대위아":
                return "Hyundai Wia";
            case "현대백화점":
                return "Hyundai Department Store";
            case "롯데쇼핑":
                return "Lotte Shopping";
            case "신세계":
                return "Shinsegae";
            case "이마트":
                return "E-Mart";
            case "GS리테일":
                return "GS Retail";
            case "BGF리테일":
                return "BGF Retail";
            case "현대홈쇼핑":
                return "Hyundai Home Shopping";
            case "CJ ENM":
                return "CJ ENM";
            case "SBS":
                return "SBS";
            case "MBC":
                return "MBC";
            case "KBS":
                return "KBS";
            case "JTBC":
                return "JTBC";
            case "tvN":
                return "tvN";
            case "OCN":
                return "OCN";
            case "채널A":
                return "Channel A";
            case "MBN":
                return "MBN";
            case "YTN":
                return "YTN";
            case "연합뉴스":
                return "Yonhap News";
            case "조선일보":
                return "Chosun Ilbo";
            case "동아일보":
                return "Dong-A Ilbo";
            case "한국경제신문":
                return "Hankyung";
            case "매일경제신문":
                return "Maeil Business";
            case "서울경제신문":
                return "Seoul Economic Daily";
            case "한겨레":
                return "Hankyoreh";
            case "경향신문":
                return "Kyunghyang";
            case "중앙일보":
                return "JoongAng Ilbo";
            case "한국일보":
                return "Hankook Ilbo";
            case "세계일보":
                return "Segye Ilbo";
            case "문화일보":
                return "Munhwa Ilbo";
            case "국민일보":
                return "Kookmin Ilbo";
            case "내일신문":
                return "Naeil";
            case "헤럴드경제":
                return "Herald Business";
            case "이데일리":
                return "Edaily";
            case "뉴스1":
                return "News1";
            case "뉴시스":
                return "Newsis";
            case "뉴스타파":
                return "Newstapa";
            case "프레시안":
                return "Pressian";
            case "오마이뉴스":
                return "OhmyNews";
            case "미디어오늘":
                return "Media Today";
            case "데일리안":
                return "Dailyan";
            case "노컷뉴스":
                return "NoCut News";
            case "시사IN":
                return "Sisa IN";
            case "주간조선":
                return "Weekly Chosun";
            case "주간동아":
                return "Weekly Dong-A";
            case "주간한국":
                return "Weekly Korea";
            case "주간경향":
                return "Weekly Kyunghyang";
            default:
                return null;
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

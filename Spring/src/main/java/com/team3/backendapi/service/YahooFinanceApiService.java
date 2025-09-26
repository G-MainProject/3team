package com.team3.backendapi.service;

import com.team3.backendapi.dto.StockPriceDto;
import com.team3.backendapi.dto.StockSummaryDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

@Service
@Slf4j
public class YahooFinanceApiService {

    @Autowired
    private RestTemplate restTemplate;

    // Yahoo Finance API 호출을 위한 헤더
    private HttpHeaders createYahooHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36");
        headers.set("Accept", "application/json");
        return headers;
    }

    // 실시간 주가 데이터 가져오기 (Yahoo Finance API 사용)
    public List<StockPriceDto> getRealtimeStockData(String symbol, String interval) {
        try {
            String yahooSymbol = getYahooSymbol(symbol);
            // 사전/사후거래 포함 (includePrePost=true)
            String url = "https://query1.finance.yahoo.com/v8/finance/chart/" + yahooSymbol + "?interval=" + interval + "&range=1d&includePrePost=true";
            
            HttpEntity<String> entity = new HttpEntity<>(createYahooHeaders());
            ResponseEntity<Map> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                log.info("Yahoo Finance API 응답 성공 (실시간 데이터): {}", symbol);
                log.info("Yahoo Finance API 응답 구조: {}", response.getBody().keySet());
                List<StockPriceDto> result = convertYahooDataToStockPriceDto(response.getBody(), interval);
                log.info("변환된 실시간 데이터 개수: {}", result.size());
                return result;
            }
        } catch (Exception e) {
            log.error("Yahoo Finance API 호출 실패 (실시간 데이터): {}", e.getMessage());
            // API 호출 실패 시 빈 리스트 반환 (에러 대신)
            return new ArrayList<>();
        }

        // API 응답이 없을 때 빈 리스트 반환
        return new ArrayList<>();
    }

    // 주식 요약 정보 가져오기 (Yahoo Finance API 사용)
    public StockSummaryDto getStockSummary(String symbol) {
        try {
            String yahooSymbol = getYahooSymbol(symbol);
            // 시가총액 정보를 포함한 다른 엔드포인트 사용
            String url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/" + yahooSymbol + "?modules=summaryDetail";
            
            HttpEntity<String> entity = new HttpEntity<>(createYahooHeaders());
            ResponseEntity<Map> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                log.info("Yahoo Finance Quote API 응답 성공: {}", symbol);
                StockSummaryDto summary = convertYahooQuoteDataToStockSummary(response.getBody(), symbol);
                
                if (summary != null) {
                    return summary;
                } else {
                    // quote API 실패 시 차트 API로 fallback
                    log.info("Quote API 실패, 차트 API로 fallback: {}", symbol);
                    return getStockSummaryFromChart(symbol);
                }
            }
        } catch (Exception e) {
            log.error("Yahoo Finance Quote API 호출 실패 (요약): {}", e.getMessage());
            // Quote API 실패 시 차트 API로 fallback
            return getStockSummaryFromChart(symbol);
        }

        // API 응답이 없을 때 null 반환
        return null;
    }
    
    // 차트 API를 사용한 주식 요약 정보 가져오기 (fallback)
    private StockSummaryDto getStockSummaryFromChart(String symbol) {
        try {
            String yahooSymbol = getYahooSymbol(symbol);
            String url = "https://query1.finance.yahoo.com/v8/finance/chart/" + yahooSymbol + "?interval=1m&range=1d";
            
            HttpEntity<String> entity = new HttpEntity<>(createYahooHeaders());
            ResponseEntity<Map> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return convertYahooDataToStockSummary(response.getBody(), symbol);
            }
        } catch (Exception e) {
            log.error("Yahoo Finance Chart API 호출 실패 (요약): {}", e.getMessage());
        }
        return null;
    }

    // 거래량 데이터 가져오기 (Yahoo Finance API 사용)
    public List<StockPriceDto> getVolumeData(String symbol, String interval) {
        try {
            String yahooSymbol = getYahooSymbol(symbol);
            String url = "https://query1.finance.yahoo.com/v8/finance/chart/" + yahooSymbol + "?interval=" + interval + "&range=1d";
            
            HttpEntity<String> entity = new HttpEntity<>(createYahooHeaders());
            ResponseEntity<Map> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                log.info("Yahoo Finance API 응답 성공 (거래량 데이터): {}", symbol);
                List<StockPriceDto> result = convertYahooDataToVolumeDto(response.getBody(), interval, symbol);
                log.info("변환된 거래량 데이터 개수: {}", result.size());
                return result;
            }
        } catch (Exception e) {
            log.error("Yahoo Finance API 호출 실패 (거래량): {}", e.getMessage());
            // API 호출 실패 시 빈 리스트 반환 (에러 대신)
            return new ArrayList<>();
        }

        // API 응답이 없을 때 빈 리스트 반환
        return new ArrayList<>();
    }

    // 한국 주식 심볼을 Yahoo Finance 심볼로 변환
    private String getYahooSymbol(String symbol) {
        // KOSPI는 .KS, KOSDAQ은 .KQ 사용
        // 주요 종목들을 KOSPI로 분류
        if (isKospiStock(symbol)) {
            return symbol + ".KS";
        } else {
            return symbol + ".KQ";
        }
    }
    
    // KOSPI 종목인지 확인 (설정 파일에서 관리)
    private boolean isKospiStock(String symbol) {
        // TODO: 설정 파일에서 KOSPI 종목 리스트를 읽어오도록 개선 필요
        // 현재는 기본적으로 KOSPI로 간주 (대부분의 주요 종목이 KOSPI)
        // 실제 운영에서는 종목 마스터 데이터베이스나 설정 파일에서 관리해야 함
        return true;
    }

    // Yahoo Finance API 응답을 StockPriceDto 리스트로 변환
    private List<StockPriceDto> convertYahooDataToStockPriceDto(Map<String, Object> yahooResponse, String interval) {
        List<StockPriceDto> result = new ArrayList<>();
        
        try {
            // 1단계: 기본 구조 검증
            if (yahooResponse == null || yahooResponse.isEmpty()) {
                log.warn("Yahoo Finance API 응답이 비어있습니다");
                return new ArrayList<>();
            }
            
            Map<String, Object> chart = (Map<String, Object>) yahooResponse.get("chart");
            if (chart == null) {
                log.warn("Chart 객체가 null입니다");
                return new ArrayList<>();
            }
            
            List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");
            if (results == null || results.isEmpty()) {
                log.warn("Results 배열이 비어있습니다");
                return new ArrayList<>();
            }
            
            log.info("Yahoo Finance 데이터 구조 검증 완료 - results 개수: {}", results.size());
            
            Map<String, Object> resultData = results.get(0);

            // 메타에서 타임존 확인 (없으면 Asia/Seoul 사용)
            ZoneId zoneId = ZoneId.of("Asia/Seoul");
            try {
                Map<String, Object> meta = (Map<String, Object>) resultData.get("meta");
                if (meta != null) {
                    Object tzObj = meta.get("timezone");
                    if (tzObj instanceof String) {
                        String tz = (String) tzObj;
                        if (tz != null && !tz.isBlank()) {
                            zoneId = ZoneId.of(tz);
                        }
                    }
                }
            } catch (Exception ignore) {}
            log.info("ResultData 키들: {}", resultData.keySet());
            
            // 안전한 타임스탬프 변환
            List<?> timestampsRaw = (List<?>) resultData.get("timestamp");
            List<Long> timestamps = new ArrayList<>();
            
            if (timestampsRaw != null) {
                for (Object ts : timestampsRaw) {
                    if (ts instanceof Long) {
                        timestamps.add((Long) ts);
                    } else if (ts instanceof Integer) {
                        timestamps.add(((Integer) ts).longValue());
                    } else if (ts instanceof Number) {
                        timestamps.add(((Number) ts).longValue());
                    }
                }
            }
            
            Map<String, Object> indicators = (Map<String, Object>) resultData.get("indicators");
            
            log.info("Timestamps 개수: {}", timestamps != null ? timestamps.size() : "null");
            log.info("Indicators 키들: {}", indicators != null ? indicators.keySet() : "null");
            
            if (timestamps == null || timestamps.isEmpty()) {
                log.warn("타임스탬프 데이터가 없습니다");
                return new ArrayList<>();
            }
            
            if (indicators == null) {
                log.warn("지표 데이터가 없습니다");
                return new ArrayList<>();
            }
            
            List<Map<String, Object>> quote = (List<Map<String, Object>>) indicators.get("quote");
            if (quote == null || quote.isEmpty()) {
                log.warn("Quote 데이터가 없습니다");
                return new ArrayList<>();
            }
            
            Map<String, Object> quoteData = quote.get(0);
            log.info("QuoteData 키들: {}", quoteData.keySet());
            
            List<Double> closes = (List<Double>) quoteData.get("close");
            List<?> volumes = (List<?>) quoteData.get("volume");
            
            log.info("Closes 개수: {}", closes != null ? closes.size() : "null");
            log.info("Volumes 개수: {}", volumes != null ? volumes.size() : "null");
            
            if (closes == null || closes.isEmpty()) {
                log.warn("종가 데이터가 없습니다");
                return new ArrayList<>();
            }
            
            // 2단계: 데이터 유효성 검증 및 변환
            int dataSize = Math.min(closes.size(), timestamps.size());
            int startIndex = Math.max(0, dataSize - 15);
            
            for (int i = startIndex; i < dataSize; i++) {
                Double closePrice = closes.get(i);
                Long timestamp = timestamps.get(i);
                
                // 가격 데이터 유효성 검증
                if (closePrice != null && closePrice > 0 && timestamp != null) {
                    LocalDateTime dateTime = LocalDateTime.ofInstant(
                        Instant.ofEpochSecond(timestamp), 
                        zoneId
                    );
                    
                    // 거래량 데이터 유효성 검증
                    int volume = 0;
                    if (volumes != null && i < volumes.size() && volumes.get(i) != null) {
                        Object volumeObj = volumes.get(i);
                        if (volumeObj instanceof Long) {
                            volume = ((Long) volumeObj).intValue();
                        } else if (volumeObj instanceof Integer) {
                            volume = (Integer) volumeObj;
                        } else if (volumeObj instanceof Number) {
                            volume = ((Number) volumeObj).intValue();
                        }
                        if (volume < 0) volume = 0; // 음수 거래량 방지
                    }
                    
                    result.add(new StockPriceDto(
                        dateTime.format(DateTimeFormatter.ofPattern("HH:mm")),
                        closePrice.intValue(),
                        volume
                    ));
                }
            }
            
            // 3단계: 결과 검증
            if (result.isEmpty()) {
                log.warn("유효한 데이터 포인트가 없습니다");
                return new ArrayList<>();
            }
            
            log.info("Yahoo Finance 데이터 변환 성공: {}개 데이터 포인트", result.size());
            
        } catch (Exception e) {
            log.error("Yahoo Finance 데이터 변환 실패: {}", e.getMessage());
            return new ArrayList<>();
        }
        
        return result;
    }

    // Yahoo Finance API 응답을 StockSummaryDto로 변환
    private StockSummaryDto convertYahooDataToStockSummary(Map<String, Object> yahooResponse, String symbol) {
        try {
            // 1단계: 기본 구조 검증
            if (yahooResponse == null || yahooResponse.isEmpty()) {
                log.warn("Yahoo Finance API 응답이 비어있습니다 (요약)");
                return null;
            }
            
            Map<String, Object> chart = (Map<String, Object>) yahooResponse.get("chart");
            if (chart == null) {
                log.warn("Chart 객체가 null입니다 (요약)");
                return null;
            }
            
            List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");
            if (results == null || results.isEmpty()) {
                log.warn("Results 배열이 비어있습니다 (요약)");
                return null;
            }
            
            Map<String, Object> resultData = results.get(0);
            log.info("Summary ResultData 키들: {}", resultData.keySet());
            
            Map<String, Object> meta = (Map<String, Object>) resultData.get("meta");
            if (meta == null) {
                log.warn("Meta 데이터가 없습니다 (요약)");
                return null;
            }
            
            log.info("Meta 키들: {}", meta.keySet());
            
            // 2단계: 필수 데이터 추출 및 검증
            Double currentPrice = (Double) meta.get("regularMarketPrice");
            Double previousClose = (Double) meta.get("previousClose");
            
            // 안전한 타입 변환
            Long volume = null;
            Object volumeObj = meta.get("regularMarketVolume");
            if (volumeObj instanceof Long) {
                volume = (Long) volumeObj;
            } else if (volumeObj instanceof Integer) {
                volume = ((Integer) volumeObj).longValue();
            } else if (volumeObj instanceof Number) {
                volume = ((Number) volumeObj).longValue();
            }
            
            Long marketCap = null;
            // 여러 가능한 시가총액 필드명 시도
            Object marketCapObj = meta.get("marketCap");
            log.info("marketCap 필드 값: {}", marketCapObj);
            
            if (marketCapObj == null) {
                marketCapObj = meta.get("market_cap");
                log.info("market_cap 필드 값: {}", marketCapObj);
            }
            if (marketCapObj == null) {
                marketCapObj = meta.get("totalMarketCap");
                log.info("totalMarketCap 필드 값: {}", marketCapObj);
            }
            if (marketCapObj == null) {
                marketCapObj = meta.get("marketCapLong");
                log.info("marketCapLong 필드 값: {}", marketCapObj);
            }
            
            if (marketCapObj instanceof Long) {
                marketCap = (Long) marketCapObj;
            } else if (marketCapObj instanceof Integer) {
                marketCap = ((Integer) marketCapObj).longValue();
            } else if (marketCapObj instanceof Number) {
                marketCap = ((Number) marketCapObj).longValue();
            }
            
            log.info("최종 시가총액 값: {}", marketCap);
            
            String name = (String) meta.get("longName");
            
            // 3단계: 필수 데이터 유효성 검증
            if (currentPrice == null || currentPrice <= 0) {
                log.warn("유효하지 않은 현재가: {}", currentPrice);
                return null;
            }
            
            if (previousClose == null || previousClose <= 0) {
                log.warn("유효하지 않은 전일종가: {}", previousClose);
                return null;
            }
            
            // 4단계: 데이터 변환 및 검증
            double change = currentPrice - previousClose;
            double changePercent = (change / previousClose) * 100;
            
            // 거래량과 시가총액 검증
            if (volume != null && volume < 0) volume = 0L;
            if (marketCap != null && marketCap < 0) marketCap = 0L;
            
            // 시가총액이 없으면 현재가와 거래량으로 추정 (대략적인 계산)
            if (marketCap == null || marketCap == 0) {
                // 거래량을 기반으로 발행주식수를 추정 (매우 대략적)
                if (volume != null && volume > 0) {
                    // 거래량의 100배를 발행주식수로 가정 (매우 대략적 추정)
                    long estimatedShares = volume * 100;
                    marketCap = (long) (currentPrice * estimatedShares);
                    log.info("시가총액 추정: 현재가 {} × 추정주식수 {} = {}", currentPrice, estimatedShares, marketCap);
                }
            }
            
            StockSummaryDto summary = new StockSummaryDto(
                symbol,
                name != null && !name.trim().isEmpty() ? name : "주식",
                currentPrice.intValue(),
                (int) change,
                Math.round(changePercent * 100.0) / 100.0,
                volume != null ? volume : 0,
                marketCap != null ? marketCap : 0
            );
            
            log.info("Yahoo Finance 요약 데이터 변환 성공: {} - {}", symbol, summary.getName());
            return summary;
            
        } catch (Exception e) {
            log.error("Yahoo Finance 요약 데이터 변환 실패: {} - {}", symbol, e.getMessage());
            return null;
        }
    }

    // Yahoo Finance API 응답을 거래량 데이터로 변환
    private List<StockPriceDto> convertYahooDataToVolumeDto(Map<String, Object> yahooResponse, String interval, String symbol) {
        List<StockPriceDto> result = new ArrayList<>();
        
        try {
            Map<String, Object> chart = (Map<String, Object>) yahooResponse.get("chart");
            if (chart == null) {
                return new ArrayList<>();
            }
            
            List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");
            if (results == null || results.isEmpty()) {
                return new ArrayList<>();
            }
            
            Map<String, Object> resultData = results.get(0);

            // 메타에서 타임존 확인 (없으면 Asia/Seoul 사용)
            ZoneId zoneId = ZoneId.of("Asia/Seoul");
            try {
                Map<String, Object> meta = (Map<String, Object>) resultData.get("meta");
                if (meta != null) {
                    Object tzObj = meta.get("timezone");
                    if (tzObj instanceof String) {
                        String tz = (String) tzObj;
                        if (tz != null && !tz.isBlank()) {
                            zoneId = ZoneId.of(tz);
                        }
                    }
                }
            } catch (Exception ignore) {}
            
            // 안전한 타임스탬프 변환
            List<?> timestampsRaw = (List<?>) resultData.get("timestamp");
            List<Long> timestamps = new ArrayList<>();
            
            if (timestampsRaw != null) {
                for (Object ts : timestampsRaw) {
                    if (ts instanceof Long) {
                        timestamps.add((Long) ts);
                    } else if (ts instanceof Integer) {
                        timestamps.add(((Integer) ts).longValue());
                    } else if (ts instanceof Number) {
                        timestamps.add(((Number) ts).longValue());
                    }
                }
            }
            
            Map<String, Object> indicators = (Map<String, Object>) resultData.get("indicators");
            
            if (indicators == null) {
                return new ArrayList<>();
            }
            
            List<Map<String, Object>> quote = (List<Map<String, Object>>) indicators.get("quote");
            if (quote == null || quote.isEmpty()) {
                return new ArrayList<>();
            }
            
            Map<String, Object> quoteData = quote.get(0);
            List<?> volumes = (List<?>) quoteData.get("volume");
            
            // volumes가 null인 경우 처리
            if (volumes == null) {
                return new ArrayList<>();
            }
            
            // 최근 15개 데이터 포인트 생성
            int startIndex = Math.max(0, volumes.size() - 15);
            
            for (int i = startIndex; i < volumes.size(); i++) {
                Object volumeObj = volumes.get(i);
                if (volumeObj != null) {
                    LocalDateTime dateTime = LocalDateTime.ofInstant(
                        Instant.ofEpochSecond(timestamps.get(i)), 
                        zoneId
                    );
                    
                    // 안전한 타입 변환
                    int volume = 0;
                    if (volumeObj instanceof Long) {
                        volume = ((Long) volumeObj).intValue();
                    } else if (volumeObj instanceof Integer) {
                        volume = (Integer) volumeObj;
                    } else if (volumeObj instanceof Number) {
                        volume = ((Number) volumeObj).intValue();
                    }
                    
                    result.add(new StockPriceDto(
                        dateTime.format(DateTimeFormatter.ofPattern("HH:mm")),
                        0, // 가격은 0으로 설정 (거래량만 필요)
                        volume
                    ));
                }
            }
            
        } catch (Exception e) {
            // 변환 실패 시 빈 배열 반환
        }
        
        // 데이터가 비어있으면 빈 리스트 반환
        if (result.isEmpty()) {
            return new ArrayList<>();
        }
        
        return result;
    }

    // Yahoo Finance QuoteSummary API 응답을 StockSummaryDto로 변환
    private StockSummaryDto convertYahooQuoteDataToStockSummary(Map<String, Object> yahooResponse, String symbol) {
        try {
            log.info("QuoteSummary API 응답 구조: {}", yahooResponse.keySet());
            
            Map<String, Object> quoteSummary = (Map<String, Object>) yahooResponse.get("quoteSummary");
            if (quoteSummary == null) {
                log.warn("QuoteSummary가 null입니다");
                return null;
            }
            
            Map<String, Object> result = (Map<String, Object>) quoteSummary.get("result");
            if (result == null || result.isEmpty()) {
                log.warn("QuoteSummary 결과가 비어있습니다");
                return null;
            }
            
            List<Map<String, Object>> resultList = (List<Map<String, Object>>) result.get("result");
            if (resultList == null || resultList.isEmpty()) {
                log.warn("QuoteSummary result 리스트가 비어있습니다");
                return null;
            }
            
            Map<String, Object> summaryDetail = resultList.get(0);
            log.info("SummaryDetail 키들: {}", summaryDetail.keySet());
            
            // 필수 데이터 추출
            Double currentPrice = (Double) summaryDetail.get("regularMarketPrice");
            Double previousClose = (Double) summaryDetail.get("previousClose");
            Long volume = (Long) summaryDetail.get("volume");
            Long marketCap = (Long) summaryDetail.get("marketCap");
            String name = (String) summaryDetail.get("longName");
            
            // 안전한 타입 변환
            if (volume == null) {
                Object volumeObj = summaryDetail.get("volume");
                if (volumeObj instanceof Integer) {
                    volume = ((Integer) volumeObj).longValue();
                } else if (volumeObj instanceof Number) {
                    volume = ((Number) volumeObj).longValue();
                }
            }
            
            if (marketCap == null) {
                Object marketCapObj = summaryDetail.get("marketCap");
                if (marketCapObj instanceof Integer) {
                    marketCap = ((Integer) marketCapObj).longValue();
                } else if (marketCapObj instanceof Number) {
                    marketCap = ((Number) marketCapObj).longValue();
                }
            }
            
            log.info("QuoteSummary API - 현재가: {}, 전일종가: {}, 거래량: {}, 시가총액: {}", 
                    currentPrice, previousClose, volume, marketCap);
            
            // 필수 데이터 검증
            if (currentPrice == null || currentPrice <= 0) {
                log.warn("유효하지 않은 현재가: {}", currentPrice);
                return null;
            }
            
            if (previousClose == null || previousClose <= 0) {
                log.warn("유효하지 않은 전일종가: {}", previousClose);
                return null;
            }
            
            // 데이터 변환
            double change = currentPrice - previousClose;
            double changePercent = (change / previousClose) * 100;
            
            // 음수 값 방지
            if (volume != null && volume < 0) volume = 0L;
            if (marketCap != null && marketCap < 0) marketCap = 0L;
            
            StockSummaryDto summary = new StockSummaryDto(
                symbol,
                name != null && !name.trim().isEmpty() ? name : "주식",
                currentPrice.intValue(),
                (int) change,
                Math.round(changePercent * 100.0) / 100.0,
                volume != null ? volume : 0,
                marketCap != null ? marketCap : 0
            );
            
            log.info("Yahoo Finance Quote 데이터 변환 성공: {} - {}", symbol, summary.getName());
            return summary;
            
        } catch (Exception e) {
            log.error("Yahoo Finance Quote 데이터 변환 실패: {} - {}", symbol, e.getMessage());
            return null;
        }
    }

    // 모의 데이터 생성 메서드들 제거됨 - 에러 처리로 대체

    // 간격 문자열을 분 단위로 변환
    private int getMinuteInterval(String interval) {
        switch (interval) {
            case "1m": return 1;
            case "5m": return 5;
            case "15m": return 15;
            case "30m": return 30;
            case "1h": return 60;
            default: return 1;
        }
    }

    // 모의 데이터 생성 메서드들 제거됨 - 에러 처리로 대체

}

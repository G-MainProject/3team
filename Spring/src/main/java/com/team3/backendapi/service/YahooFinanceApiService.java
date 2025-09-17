package com.team3.backendapi.service;

import com.team3.backendapi.dto.StockPriceDto;
import com.team3.backendapi.dto.StockSummaryDto;
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
            String url = "https://query1.finance.yahoo.com/v8/finance/chart/" + yahooSymbol + "?interval=" + interval + "&range=1d";
            
            HttpEntity<String> entity = new HttpEntity<>(createYahooHeaders());
            ResponseEntity<Map> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return convertYahooDataToStockPriceDto(response.getBody(), interval);
            }
        } catch (Exception e) {
            System.err.println("Yahoo Finance API 호출 실패: " + e.getMessage());
            e.printStackTrace();
        }

        // API 호출 실패 시 모의 데이터 반환 (fallback)
        return generateMockRealtimeData(interval);
    }

    // 주식 요약 정보 가져오기 (Yahoo Finance API 사용)
    public StockSummaryDto getStockSummary(String symbol) {
        try {
            String yahooSymbol = getYahooSymbol(symbol);
            String url = "https://query1.finance.yahoo.com/v8/finance/chart/" + yahooSymbol + "?interval=1m&range=1d";
            
            
            HttpEntity<String> entity = new HttpEntity<>(createYahooHeaders());
            ResponseEntity<Map> response = restTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                StockSummaryDto summary = convertYahooDataToStockSummary(response.getBody(), symbol);
                
                if (summary != null) {
                    return summary;
                } else {
                    return generateMockStockSummary(symbol);
                }
            }
        } catch (Exception e) {
            System.err.println("Yahoo Finance API 호출 실패 (요약): " + e.getMessage());
            e.printStackTrace();
        }

        // API 호출 실패 시 모의 데이터 반환 (fallback)
        return generateMockStockSummary(symbol);
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
                return convertYahooDataToVolumeDto(response.getBody(), interval);
            }
        } catch (Exception e) {
            System.err.println("Yahoo Finance API 호출 실패 (거래량): " + e.getMessage());
            e.printStackTrace();
        }

        // API 호출 실패 시 모의 데이터 반환 (fallback)
        return generateMockVolumeData(interval);
    }

    // 한국 주식 심볼을 Yahoo Finance 심볼로 변환
    private String getYahooSymbol(String symbol) {
        switch (symbol) {
            case "005930": return "005930.KQ"; // 삼성전자 (KOSPI)
            case "000660": return "000660.KQ"; // SK하이닉스 (KOSPI)
            case "035420": return "035420.KQ"; // NAVER (KOSPI)
            case "207940": return "207940.KQ"; // 삼성바이오로직스 (KOSPI)
            case "006400": return "006400.KQ"; // 삼성SDI (KOSPI)
            default: return symbol + ".KQ"; // KOSPI는 .KQ 사용
        }
    }

    // Yahoo Finance API 응답을 StockPriceDto 리스트로 변환
    private List<StockPriceDto> convertYahooDataToStockPriceDto(Map<String, Object> yahooResponse, String interval) {
        List<StockPriceDto> result = new ArrayList<>();
        
        try {
            Map<String, Object> chart = (Map<String, Object>) yahooResponse.get("chart");
            System.out.println("Chart 객체: " + (chart != null ? "존재" : "null"));
            
            if (chart != null) {
                List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");
                System.out.println("Results 배열 크기: " + (results != null ? results.size() : "null"));
                
                if (results != null && !results.isEmpty()) {
                    Map<String, Object> resultData = results.get(0);
                    
                    List<Long> timestamps = (List<Long>) resultData.get("timestamp");
                    
                    Map<String, Object> indicators = (Map<String, Object>) resultData.get("indicators");
                    
                    if (indicators != null) {
                        List<Map<String, Object>> quote = (List<Map<String, Object>>) indicators.get("quote");
                        
                        if (quote != null && !quote.isEmpty()) {
                            Map<String, Object> quoteData = quote.get(0);
                            
                            List<Double> closes = (List<Double>) quoteData.get("close");
                            List<Long> volumes = (List<Long>) quoteData.get("volume");
                            
                            
                            if (closes != null && timestamps != null) {
                                // 최근 15개 데이터 포인트 생성
                                int dataSize = Math.min(closes.size(), timestamps.size());
                                int startIndex = Math.max(0, dataSize - 15);
                                
                                
                                for (int i = startIndex; i < dataSize; i++) {
                                    if (closes.get(i) != null) {
                                        LocalDateTime dateTime = LocalDateTime.ofInstant(
                                            Instant.ofEpochSecond(timestamps.get(i)), 
                                            ZoneId.systemDefault()
                                        );
                                        
                                        result.add(new StockPriceDto(
                                            dateTime.format(DateTimeFormatter.ofPattern("HH:mm")),
                                            closes.get(i).intValue(),
                                            volumes != null && i < volumes.size() && volumes.get(i) != null ? 
                                                volumes.get(i).intValue() : 0
                                        ));
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("Yahoo Finance 데이터 변환 실패: " + e.getMessage());
            e.printStackTrace();
        }
        
        // 데이터가 비어있으면 모의 데이터 반환 (fallback)
        if (result.isEmpty()) {
            return generateMockRealtimeData(interval);
        }
        
        return result;
    }

    // Yahoo Finance API 응답을 StockSummaryDto로 변환
    private StockSummaryDto convertYahooDataToStockSummary(Map<String, Object> yahooResponse, String symbol) {
        try {
            Map<String, Object> chart = (Map<String, Object>) yahooResponse.get("chart");
            List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");
            
            if (results != null && !results.isEmpty()) {
                Map<String, Object> resultData = results.get(0);
                Map<String, Object> meta = (Map<String, Object>) resultData.get("meta");
                
                Double currentPrice = (Double) meta.get("regularMarketPrice");
                Double previousClose = (Double) meta.get("previousClose");
                Long volume = (Long) meta.get("regularMarketVolume");
                Long marketCap = (Long) meta.get("marketCap");
                String name = (String) meta.get("longName");
                
                if (currentPrice != null && previousClose != null) {
                    double change = currentPrice - previousClose;
                    double changePercent = (change / previousClose) * 100;
                    
                    
                    return new StockSummaryDto(
                        symbol,
                        name != null ? name : "주식",
                        currentPrice.intValue(),
                        (int) change,
                        Math.round(changePercent * 100.0) / 100.0,
                        volume != null ? volume : 0,
                        marketCap != null ? marketCap : 0
                    );
                }
            }
        } catch (Exception e) {
            System.err.println("Yahoo Finance 요약 데이터 변환 실패: " + e.getMessage());
            e.printStackTrace();
        }
        
        return null;
    }

    // Yahoo Finance API 응답을 거래량 데이터로 변환
    private List<StockPriceDto> convertYahooDataToVolumeDto(Map<String, Object> yahooResponse, String interval) {
        List<StockPriceDto> result = new ArrayList<>();
        
        try {
            Map<String, Object> chart = (Map<String, Object>) yahooResponse.get("chart");
            List<Map<String, Object>> results = (List<Map<String, Object>>) chart.get("result");
            
            if (results != null && !results.isEmpty()) {
                Map<String, Object> resultData = results.get(0);
                List<Long> timestamps = (List<Long>) resultData.get("timestamp");
                Map<String, Object> indicators = (Map<String, Object>) resultData.get("indicators");
                List<Map<String, Object>> quote = (List<Map<String, Object>>) indicators.get("quote");
                Map<String, Object> quoteData = quote.get(0);
                
                List<Long> volumes = (List<Long>) quoteData.get("volume");
                
                // 최근 15개 데이터 포인트 생성
                int startIndex = Math.max(0, volumes.size() - 15);
                for (int i = startIndex; i < volumes.size(); i++) {
                    if (volumes.get(i) != null) {
                        LocalDateTime dateTime = LocalDateTime.ofInstant(
                            Instant.ofEpochSecond(timestamps.get(i)), 
                            ZoneId.systemDefault()
                        );
                        
                        result.add(new StockPriceDto(
                            dateTime.format(DateTimeFormatter.ofPattern("HH:mm")),
                            0, // 가격은 0으로 설정 (거래량만 필요)
                            volumes.get(i).intValue()
                        ));
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("Yahoo Finance 거래량 데이터 변환 실패: " + e.getMessage());
            e.printStackTrace();
        }
        
        // 데이터가 비어있으면 모의 데이터 반환 (fallback)
        if (result.isEmpty()) {
            return generateMockVolumeData(interval);
        }
        
        return result;
    }

    // 모의 실시간 데이터 생성 (API 실패 시 fallback)
    private List<StockPriceDto> generateMockRealtimeData(String interval) {
        List<StockPriceDto> data = new ArrayList<>();
        Random random = new Random();
        LocalDateTime now = LocalDateTime.now();
        int basePrice = 78000; // 실제 삼성전자 주가 근처
        
        // 간격에 따른 분 단위 계산
        int minuteInterval = getMinuteInterval(interval);

        for (int i = 0; i < 15; i++) {
            LocalDateTime time = now.minusMinutes((14 - i) * minuteInterval);
            int price = basePrice + random.nextInt(2000) - 1000; // ±1000원 변동
            int volume = 1000000 + random.nextInt(2000000);

            data.add(new StockPriceDto(
                time.format(DateTimeFormatter.ofPattern("HH:mm")),
                price,
                volume
            ));
        }

        return data;
    }

    // 모의 거래량 데이터 생성 (API 실패 시 fallback)
    private List<StockPriceDto> generateMockVolumeData(String interval) {
        List<StockPriceDto> data = new ArrayList<>();
        Random random = new Random();
        LocalDateTime now = LocalDateTime.now();
        
        // 간격에 따른 분 단위 계산
        int minuteInterval = getMinuteInterval(interval);

        for (int i = 0; i < 15; i++) {
            LocalDateTime time = now.minusMinutes((14 - i) * minuteInterval);
            int volume = 800000 + random.nextInt(2400000);

            data.add(new StockPriceDto(
                time.format(DateTimeFormatter.ofPattern("HH:mm")),
                0, // 가격은 0으로 설정 (거래량만 필요)
                volume
            ));
        }

        return data;
    }

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

    // 모의 주식 요약 정보 생성 (API 실패 시 fallback)
    private StockSummaryDto generateMockStockSummary(String symbol) {
        Random random = new Random();
        
        // 심볼별 기본 가격 설정
        int basePrice = getBasePriceForSymbol(symbol);
        int currentPrice = basePrice + random.nextInt(2000) - 1000;
        int change = random.nextInt(2000) - 1000;
        double changePercent = (double) change / (currentPrice - change) * 100;
        long volume = 1000000 + random.nextInt(2000000);
        long marketCap = currentPrice * 1000000000L; // 10억 주 가정

        return new StockSummaryDto(
            symbol,
            getStockName(symbol),
            currentPrice,
            change,
            changePercent,
            volume,
            marketCap
        );
    }
    
    // 심볼별 기본 가격 반환
    private int getBasePriceForSymbol(String symbol) {
        switch (symbol) {
            case "005930": return 78000; // 삼성전자
            case "000660": return 120000; // SK하이닉스
            case "035420": return 200000; // NAVER
            case "207940": return 800000; // 삼성바이오로직스
            case "006400": return 400000; // 삼성SDI
            default: return 50000;
        }
    }
    
    // 심볼을 회사명으로 변환
    private String getStockName(String symbol) {
        switch (symbol) {
            case "005930": return "삼성전자";
            case "000660": return "SK하이닉스";
            case "035420": return "NAVER";
            case "207940": return "삼성바이오로직스";
            case "006400": return "삼성SDI";
            default: return "주식";
        }
    }

}

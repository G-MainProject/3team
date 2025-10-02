package com.team3.backendapi.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class StockDataService {
    
    private final ObjectMapper objectMapper;
    
    public String getStockName(String symbol) {
        try {
            // sentiment_report.json 파일 경로
            String filePath = "data/raws/sentiment_report.json";
            File file = new File(filePath);
            
            if (!file.exists()) {
                log.warn("sentiment_report.json 파일을 찾을 수 없습니다: {}", filePath);
                return "알 수 없는 주식";
            }
            
            // JSON 파일 읽기
            List<Map<String, Object>> data = objectMapper.readValue(file, new TypeReference<List<Map<String, Object>>>() {});
            
            // 해당 종목코드로 주식명 찾기
            for (Map<String, Object> item : data) {
                String stockCode = (String) item.get("stockCode");
                if (symbol.equals(stockCode)) {
                    String stockName = (String) item.get("stockName");
                    log.info("주식명 매핑 성공: {} -> {}", symbol, stockName);
                    return stockName != null ? stockName : "알 수 없는 주식";
                }
            }
            
            log.warn("종목코드 {}에 해당하는 주식명을 찾을 수 없습니다", symbol);
            return "알 수 없는 주식";
            
        } catch (IOException e) {
            log.error("sentiment_report.json 파일 읽기 실패: {}", e.getMessage());
            return "알 수 없는 주식";
        }
    }
}

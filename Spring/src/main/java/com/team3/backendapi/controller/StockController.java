package com.team3.backendapi.controller;

import com.team3.backendapi.dto.ApiResponse;
import com.team3.backendapi.dto.StockPriceDto;
import com.team3.backendapi.dto.StockSummaryDto;
import com.team3.backendapi.service.YahooFinanceApiService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/stock")
@CrossOrigin(origins = "http://localhost:3000")
public class StockController {

    @Autowired
    private YahooFinanceApiService yahooFinanceApiService;

    // 실시간 주가 데이터 조회
    @GetMapping("/realtime/{symbol}")
    public ResponseEntity<ApiResponse<List<StockPriceDto>>> getRealtimeStockData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval) {
        try {
            List<StockPriceDto> data = yahooFinanceApiService.getRealtimeStockData(symbol, interval);
            return ResponseEntity.ok(ApiResponse.success("실시간 주가 데이터를 성공적으로 조회했습니다.", data));
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                .body(ApiResponse.error("실시간 주가 데이터 조회에 실패했습니다: " + e.getMessage()));
        }
    }

    // 주식 요약 정보 조회
    @GetMapping("/summary/{symbol}")
    public ResponseEntity<ApiResponse<StockSummaryDto>> getStockSummary(
            @PathVariable String symbol) {
        try {
            StockSummaryDto summary = yahooFinanceApiService.getStockSummary(symbol);
            return ResponseEntity.ok(ApiResponse.success("주식 요약 정보를 성공적으로 조회했습니다.", summary));
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                .body(ApiResponse.error("주식 요약 정보 조회에 실패했습니다: " + e.getMessage()));
        }
    }

    // 거래량 데이터 조회
    @GetMapping("/volume/{symbol}")
    public ResponseEntity<ApiResponse<List<StockPriceDto>>> getVolumeData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval) {
        try {
            List<StockPriceDto> data = yahooFinanceApiService.getVolumeData(symbol, interval);
            return ResponseEntity.ok(ApiResponse.success("거래량 데이터를 성공적으로 조회했습니다.", data));
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                .body(ApiResponse.error("거래량 데이터 조회에 실패했습니다: " + e.getMessage()));
        }
    }

    // 통합 주식 데이터 조회 (주가 + 거래량)
    @GetMapping("/unified/{symbol}")
    public ResponseEntity<ApiResponse<Object>> getUnifiedStockData(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval) {
        try {
            List<StockPriceDto> stockData = yahooFinanceApiService.getRealtimeStockData(symbol, interval);
            List<StockPriceDto> volumeData = yahooFinanceApiService.getVolumeData(symbol, interval);
            StockSummaryDto summary = yahooFinanceApiService.getStockSummary(symbol);

            UnifiedStockData response = new UnifiedStockData();
            response.setStockData(stockData);
            response.setVolumeData(volumeData);
            response.setSummary(summary);

            return ResponseEntity.ok(ApiResponse.success("통합 주식 데이터를 성공적으로 조회했습니다.", response));
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                .body(ApiResponse.error("통합 주식 데이터 조회에 실패했습니다: " + e.getMessage()));
        }
    }

    // 통합 데이터 응답 클래스
    public static class UnifiedStockData {
        private List<StockPriceDto> stockData;
        private List<StockPriceDto> volumeData;
        private StockSummaryDto summary;

        public List<StockPriceDto> getStockData() {
            return stockData;
        }

        public void setStockData(List<StockPriceDto> stockData) {
            this.stockData = stockData;
        }

        public List<StockPriceDto> getVolumeData() {
            return volumeData;
        }

        public void setVolumeData(List<StockPriceDto> volumeData) {
            this.volumeData = volumeData;
        }

        public StockSummaryDto getSummary() {
            return summary;
        }

        public void setSummary(StockSummaryDto summary) {
            this.summary = summary;
        }
    }
}

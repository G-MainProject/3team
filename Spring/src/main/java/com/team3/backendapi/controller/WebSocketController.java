package com.team3.backendapi.controller;

import com.team3.backendapi.dto.UnifiedStockData;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

@Controller
@RequiredArgsConstructor
@Slf4j
public class WebSocketController {

    private final SimpMessagingTemplate messagingTemplate;

    /**
     * 특정 종목의 실시간 데이터를 모든 구독자에게 브로드캐스트
     */
    public void broadcastStockData(String symbol, UnifiedStockData data) {
        try {
            String destination = "/topic/stock/" + symbol;
            messagingTemplate.convertAndSend(destination, data);
            log.info("📡 WebSocket 브로드캐스트: {} - {}", symbol, destination);
        } catch (Exception e) {
            log.error("❌ WebSocket 브로드캐스트 실패: {} - {}", symbol, e.getMessage());
        }
    }

    /**
     * 모든 종목의 실시간 데이터를 모든 구독자에게 브로드캐스트
     */
    public void broadcastAllStockData(String symbol, UnifiedStockData data) {
        try {
            String destination = "/topic/stock/all";
            messagingTemplate.convertAndSend(destination, data);
            log.info("📡 WebSocket 전체 브로드캐스트: {} - {}", symbol, destination);
        } catch (Exception e) {
            log.error("❌ WebSocket 전체 브로드캐스트 실패: {} - {}", symbol, e.getMessage());
        }
    }
}

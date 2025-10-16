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

    public void broadcastStockData(String symbol, UnifiedStockData data) {
        try {
            String destination = "/topic/stock/" + symbol;
            messagingTemplate.convertAndSend(destination, data);
        } catch (Exception e) {
            log.error("WebSocket broadcast failed for {}: {}", symbol, e.getMessage());
        }
    }

    public void broadcastAllStockData(String symbol, UnifiedStockData data) {
        try {
            String destination = "/topic/stock/all";
            messagingTemplate.convertAndSend(destination, data);
        } catch (Exception e) {
            log.error("WebSocket broadcast all failed for {}: {}", symbol, e.getMessage());
        }
    }
}

package com.team3.backendapi.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CacheMetadata {
    private LocalDateTime lastUpdated;
    private String dataType; // "stock", "realtime", "volume"
    private String symbol;
    private String interval;
    
    public CacheMetadata(String dataType, String symbol, String interval) {
        this.dataType = dataType;
        this.symbol = symbol;
        this.interval = interval;
        this.lastUpdated = LocalDateTime.now();
    }
}

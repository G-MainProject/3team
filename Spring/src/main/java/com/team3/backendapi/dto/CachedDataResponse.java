package com.team3.backendapi.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CachedDataResponse<T> {
    private T data;
    private CacheMetadata metadata;
    
    public CachedDataResponse(T data, String dataType, String symbol, String interval) {
        this.data = data;
        this.metadata = new CacheMetadata(dataType, symbol, interval);
    }
}

package com.team3.backendapi.dto;

import lombok.Data;
import java.util.List;

@Data
public class UnifiedStockData {
    private List<StockPriceDto> stockData;
    private List<StockPriceDto> volumeData;
    private StockSummaryDto summary;
}

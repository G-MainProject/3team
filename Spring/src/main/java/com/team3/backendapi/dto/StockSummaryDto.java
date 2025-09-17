package com.team3.backendapi.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class StockSummaryDto {
    private String symbol;
    private String name;
    private int currentPrice;
    private int change;
    private double changePercent;
    private long volume;
    private long marketCap;
    private int high;
    private int low;
    private int open;
    private int close;

    public StockSummaryDto() {}

    public StockSummaryDto(String symbol, String name, int currentPrice, int change, 
                          double changePercent, long volume, long marketCap) {
        this.symbol = symbol;
        this.name = name;
        this.currentPrice = currentPrice;
        this.change = change;
        this.changePercent = changePercent;
        this.volume = volume;
        this.marketCap = marketCap;
    }

    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getCurrentPrice() {
        return currentPrice;
    }

    public void setCurrentPrice(int currentPrice) {
        this.currentPrice = currentPrice;
    }

    public int getChange() {
        return change;
    }

    public void setChange(int change) {
        this.change = change;
    }

    public double getChangePercent() {
        return changePercent;
    }

    public void setChangePercent(double changePercent) {
        this.changePercent = changePercent;
    }

    public long getVolume() {
        return volume;
    }

    public void setVolume(long volume) {
        this.volume = volume;
    }

    public long getMarketCap() {
        return marketCap;
    }

    public void setMarketCap(long marketCap) {
        this.marketCap = marketCap;
    }

    public int getHigh() {
        return high;
    }

    public void setHigh(int high) {
        this.high = high;
    }

    public int getLow() {
        return low;
    }

    public void setLow(int low) {
        this.low = low;
    }

    public int getOpen() {
        return open;
    }

    public void setOpen(int open) {
        this.open = open;
    }

    public int getClose() {
        return close;
    }

    public void setClose(int close) {
        this.close = close;
    }
}

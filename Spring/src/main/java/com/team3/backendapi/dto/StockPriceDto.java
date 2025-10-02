package com.team3.backendapi.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;

public class StockPriceDto {
    private String time;
    private int price;
    private int volume;
    private LocalDateTime timestamp;

    public StockPriceDto() {}

    public StockPriceDto(String time, int price, int volume) {
        this.time = time;
        this.price = price;
        this.volume = volume;
        this.timestamp = LocalDateTime.now();
    }

    public String getTime() {
        return time;
    }

    public void setTime(String time) {
        this.time = time;
    }

    public int getPrice() {
        return price;
    }

    public void setPrice(int price) {
        this.price = price;
    }

    public int getVolume() {
        return volume;
    }

    public void setVolume(int volume) {
        this.volume = volume;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }
}

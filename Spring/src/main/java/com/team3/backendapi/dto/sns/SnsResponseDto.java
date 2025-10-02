package com.team3.backendapi.dto.sns;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SnsResponseDto {
    private List<SnsPostDto> tweets;
    private List<SnsPostDto> redditPosts;
    private String stockName;
    private String symbol;
    private LocalDateTime lastUpdate;
    
    // 기존 생성자와 호환성을 위한 생성자
    public SnsResponseDto(List<SnsPostDto> tweets, List<SnsPostDto> redditPosts, String stockName, String symbol) {
        this.tweets = tweets;
        this.redditPosts = redditPosts;
        this.stockName = stockName;
        this.symbol = symbol;
        this.lastUpdate = LocalDateTime.now();
    }
}

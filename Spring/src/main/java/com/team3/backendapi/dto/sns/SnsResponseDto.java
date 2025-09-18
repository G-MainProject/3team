package com.team3.backendapi.dto.sns;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SnsResponseDto {
    private List<SnsPostDto> tweets;
    private List<SnsPostDto> redditPosts;
    private String stockName;
    private String symbol;
}

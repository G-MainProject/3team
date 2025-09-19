package com.team3.backendapi.dto.sns;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SnsPostDto {
    private String id;
    private String author;
    private String content;
    private String time;
    private int likes;
    private int retweets;
    private int replies;
    private String platform; // "twitter" or "reddit"
    private String url; // 게시물 링크
}

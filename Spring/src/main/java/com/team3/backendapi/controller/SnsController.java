package com.team3.backendapi.controller;

import com.team3.backendapi.dto.sns.SnsResponseDto;
import com.team3.backendapi.service.sns.SnsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/sns")
@RequiredArgsConstructor
@Slf4j
@CrossOrigin(origins = "http://localhost:5173") // React 개발 서버 CORS 허용
public class SnsController {

    private final SnsService snsService;

    @GetMapping("/{symbol}")
    public Mono<ResponseEntity<SnsResponseDto>> getSnsData(@PathVariable String symbol) {
        log.info("SNS API 요청 받음: {}", symbol);
        
        return snsService.getSnsData(symbol)
                .doOnNext(data -> log.info("SNS 데이터 생성 완료: tweets={}, reddit={}", 
                    data.getTweets() != null ? data.getTweets().size() : 0,
                    data.getRedditPosts() != null ? data.getRedditPosts().size() : 0))
                .map(ResponseEntity::ok)
                .doOnNext(response -> log.info("SNS API 응답 전송 완료"))
                .onErrorReturn(ResponseEntity.internalServerError().build());
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("SNS API is running");
    }
}

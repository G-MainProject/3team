package com.team3.backendapi.controller;

import com.team3.backendapi.dto.ApiResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/data")
public class DataController {

    // 임시 데이터 저장소
    private List<Map<String, Object>> dataList = new ArrayList<>();
    private Long nextId = 1L;

    public DataController() {
        // 샘플 데이터 추가
        addSampleData("감정 분석 데이터", "긍정", 85.5);
        addSampleData("키워드 분석 데이터", "AI, 머신러닝", 92.3);
        addSampleData("예측 모델 데이터", "주가 상승", 78.9);
    }

    private void addSampleData(String title, String content, Double score) {
        Map<String, Object> data = new HashMap<>();
        data.put("id", nextId++);
        data.put("title", title);
        data.put("content", content);
        data.put("score", score);
        data.put("createdAt", LocalDateTime.now());
        data.put("type", "analysis");
        dataList.add(data);
    }

    // 모든 데이터 조회
    @GetMapping
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> getAllData() {
        return ResponseEntity.ok(ApiResponse.success("데이터 목록을 조회했습니다.", dataList));
    }

    // 특정 데이터 조회
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getDataById(@PathVariable Long id) {
        Map<String, Object> data = dataList.stream()
                .filter(d -> d.get("id").equals(id))
                .findFirst()
                .orElse(null);
        
        if (data == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("데이터를 찾을 수 없습니다."));
        }
        
        return ResponseEntity.ok(ApiResponse.success("데이터를 조회했습니다.", data));
    }

    // 새 데이터 생성
    @PostMapping
    public ResponseEntity<ApiResponse<Map<String, Object>>> createData(@RequestBody Map<String, Object> dataRequest) {
        Map<String, Object> newData = new HashMap<>();
        newData.put("id", nextId++);
        newData.put("title", dataRequest.get("title"));
        newData.put("content", dataRequest.get("content"));
        newData.put("score", dataRequest.get("score"));
        newData.put("type", dataRequest.getOrDefault("type", "analysis"));
        newData.put("createdAt", LocalDateTime.now());
        
        dataList.add(newData);
        
        return ResponseEntity.ok(ApiResponse.success("데이터가 생성되었습니다.", newData));
    }

    // 데이터 통계 조회
    @GetMapping("/stats")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getDataStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalCount", dataList.size());
        stats.put("averageScore", dataList.stream()
                .mapToDouble(d -> (Double) d.get("score"))
                .average()
                .orElse(0.0));
        stats.put("maxScore", dataList.stream()
                .mapToDouble(d -> (Double) d.get("score"))
                .max()
                .orElse(0.0));
        stats.put("minScore", dataList.stream()
                .mapToDouble(d -> (Double) d.get("score"))
                .min()
                .orElse(0.0));
        
        return ResponseEntity.ok(ApiResponse.success("데이터 통계를 조회했습니다.", stats));
    }

    // 데이터 검색
    @GetMapping("/search")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> searchData(@RequestParam String keyword) {
        List<Map<String, Object>> results = dataList.stream()
                .filter(data -> 
                    data.get("title").toString().toLowerCase().contains(keyword.toLowerCase()) ||
                    data.get("content").toString().toLowerCase().contains(keyword.toLowerCase())
                )
                .toList();
        
        return ResponseEntity.ok(ApiResponse.success("검색 결과를 조회했습니다.", results));
    }
}

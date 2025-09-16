package com.team3.backendapi.controller;

import com.team3.backendapi.dto.ApiResponse;
import com.team3.backendapi.entity.User;
import com.team3.backendapi.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/admin")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173"})
@RequiredArgsConstructor
public class AdminController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    // 비밀번호 테스트 (개발용)
    @PostMapping("/test-password")
    public ResponseEntity<ApiResponse<Map<String, Object>>> testPassword(
            @RequestParam String username,
            @RequestParam String password) {
        
        try {
            User user = userRepository.findByEmailOrUsername(username)
                    .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
            
            Map<String, Object> result = new HashMap<>();
            result.put("username", user.getUsername());
            result.put("email", user.getEmail());
            result.put("storedPassword", user.getPassword());
            result.put("isBCrypt", user.getPassword().startsWith("$2a$"));
            
            // BCrypt 비교
            boolean bcryptMatch = passwordEncoder.matches(password, user.getPassword());
            result.put("bcryptMatch", bcryptMatch);
            
            // 평문 비교
            boolean plainMatch = password.equals(user.getPassword());
            result.put("plainMatch", plainMatch);
            
            return ResponseEntity.ok(ApiResponse.<Map<String, Object>>builder()
                    .success(true)
                    .message("비밀번호 테스트 완료")
                    .data(result)
                    .build());
                    
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.<Map<String, Object>>builder()
                            .success(false)
                            .message("테스트 실패: " + e.getMessage())
                            .build());
        }
    }

    // 비밀번호 재설정 (개발용)
    @PostMapping("/reset-password")
    public ResponseEntity<ApiResponse<String>> resetPassword(
            @RequestParam String username,
            @RequestParam String newPassword) {
        
        try {
            User user = userRepository.findByEmailOrUsername(username)
                    .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
            
            // 새 비밀번호 암호화
            String encodedPassword = passwordEncoder.encode(newPassword);
            user.setPassword(encodedPassword);
            userRepository.save(user);
            
            return ResponseEntity.ok(ApiResponse.<String>builder()
                    .success(true)
                    .message("비밀번호가 재설정되었습니다.")
                    .data("새 비밀번호: " + newPassword)
                    .build());
                    
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.<String>builder()
                            .success(false)
                            .message("비밀번호 재설정 실패: " + e.getMessage())
                            .build());
        }
    }
}

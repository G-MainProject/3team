package com.team3.backendapi.dto;

import com.team3.backendapi.entity.User;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

public class UserDto {
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateRequest {
        private String email;
        private String name;
        private User.Gender gender;
        private LocalDate birthDate;
        private String username;
        private String password;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateRequest {
        private String email;
        private String name;
        private User.Gender gender;
        private LocalDate birthDate;
        private String username;
        private String password;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private Long id;
        private String email;
        private String name;
        private User.Gender gender;
        private LocalDate birthDate;
        private String username;
        private User.UserRole role;
        private Boolean isActive;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class LoginRequest {
        private String emailOrUsername;
        private String password;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class LoginResponse {
        private Long id;
        private String email;
        private String name;
        private String username;
        private User.Gender gender;
        private LocalDate birthDate;
        private User.UserRole role;
        private String token; // JWT 토큰 (나중에 구현)
    }
}

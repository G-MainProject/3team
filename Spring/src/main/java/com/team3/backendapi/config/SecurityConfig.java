package com.team3.backendapi.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable()) // CSRF 비활성화 (개발용)
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/api/auth/**").permitAll() // 인증 관련 엔드포인트 허용
                .requestMatchers("/api/health").permitAll() // 헬스 체크 허용
                .requestMatchers("/api/users/**").permitAll() // 사용자 관리 API 허용
                .requestMatchers("/api/data/**").permitAll() // 데이터 분석 API 허용
                .requestMatchers("/h2-console/**").permitAll() // H2 콘솔 허용
                .requestMatchers("/static/**", "/assets/**", "/*.js", "/*.css", "/*.png", "/*.jpg", "/*.jpeg", "/*.gif", "/*.svg", "/*.ico").permitAll() // 정적 리소스 허용
                .requestMatchers("/", "/index.html", "/login", "/login-form", "/register", "/dashboard", "/api-test", "/users", "/data").permitAll() // 모든 페이지 허용
                .anyRequest().permitAll() // 나머지 모든 요청 허용 (개발용)
            )
            .headers(headers -> headers
                .frameOptions().disable() // H2 콘솔을 위한 설정
            );
        
        return http.build();
    }
}

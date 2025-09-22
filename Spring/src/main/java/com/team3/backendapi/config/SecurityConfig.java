package com.team3.backendapi.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;

import static org.springframework.security.config.Customizer.withDefaults;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .cors(withDefaults()) // CORS 활성화
            .csrf(csrf -> csrf.disable()) // CSRF 비활성화 (개발용)
            .httpBasic(httpBasic -> httpBasic.disable()) // HTTP Basic 인증 비활성화
            .formLogin(formLogin -> formLogin.disable()) // 폼 로그인 비활성화
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/api/auth/**").permitAll() // 인증 관련 엔드포인트 허용
                .requestMatchers("/api/stock/**").permitAll() // 주식 API 허용
                .requestMatchers("/api/sns/**").permitAll() // SNS API 허용
                .requestMatchers("/api/health").permitAll() // 헬스 체크 허용
                .requestMatchers("/api/users/**").permitAll() // 사용자 관리 API 허용
                .requestMatchers("/api/data/**").permitAll() // 데이터 분석 API 허용
                .requestMatchers("/h2-console/**").permitAll() // H2 콘솔 허용
                .requestMatchers("/static/**", "/assets/**", "/*.js", "/*.css", "/*.png", "/*.jpg", "/*.jpeg", "/*.gif", "/*.svg", "/*.ico").permitAll() // 정적 리소스 허용
                .requestMatchers("/", "/index.html", "/login", "/login-form", "/register", "/dashboard", "/api-test", "/users", "/data").permitAll() // 모든 페이지 허용
                .anyRequest().permitAll() // 나머지 모든 요청 허용 (개발용)
            )
            .headers(headers -> headers
                .frameOptions(frameOptions -> frameOptions.disable()) // H2 콘솔을 위한 설정
            );
        
        return http.build();
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(Arrays.asList("http://localhost:3000", "http://localhost:5173", "https://*.ngrok-free.app"));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("*"));
        configuration.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration); // 모든 경로에 대해 CORS 설정 적용
        return source;
    }
}
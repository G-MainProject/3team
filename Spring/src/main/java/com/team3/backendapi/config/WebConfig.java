package com.team3.backendapi.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.ViewControllerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // React 빌드 파일 서빙
        registry.addResourceHandler("/static/**")
                .addResourceLocations("classpath:/static/");
        
        // React 정적 파일들 서빙 (CSS, JS, 이미지 등)
        registry.addResourceHandler("/assets/**")
                .addResourceLocations("classpath:/static/assets/");
        
        registry.addResourceHandler("/*.js", "/*.css", "/*.png", "/*.jpg", "/*.jpeg", "/*.gif", "/*.svg", "/*.woff2", "/*.mp4")
                .addResourceLocations("classpath:/static/");
    }

    @Override
    public void addViewControllers(ViewControllerRegistry registry) {
        // SPA 라우팅을 위한 설정 - API가 아닌 모든 경로를 index.html로 리다이렉트
        // 이렇게 하면 React Router가 클라이언트 사이드에서 라우팅을 처리할 수 있습니다
        registry.addViewController("/{path:[^.]*}")
                .setViewName("forward:/index.html");
    }
}
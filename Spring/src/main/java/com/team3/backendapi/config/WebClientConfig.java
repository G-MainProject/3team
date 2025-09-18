package com.team3.backendapi.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebClientConfig {

    @Value("${twitter.api.base-url:https://api.twitter.com/2}")
    private String twitterBaseUrl;
    
    @Value("${reddit.api.base-url:https://oauth.reddit.com}")
    private String redditBaseUrl;

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
                .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(1024 * 1024)) // 1MB
                .build();
    }
    
    @Bean("twitterWebClient")
    public WebClient twitterWebClient() {
        return WebClient.builder()
                .baseUrl(twitterBaseUrl)
                .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(1024 * 1024))
                .build();
    }
    
    @Bean("redditWebClient")
    public WebClient redditWebClient() {
        return WebClient.builder()
                .baseUrl(redditBaseUrl)
                .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(1024 * 1024))
                .build();
    }
}

package com.example.targetapi.config;

import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.web.client.RestTemplate;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Slf4j
@Configuration
public class ApiCallRunner {

    @Bean
    public CommandLineRunner initializeApiCalls() {
        return args -> {
            // 서버가 완전히 시작된 후 API 호출을 시작하기 위해 잠시 대기
            log.info("Waiting for server to fully start before making test API calls...");
            Thread.sleep(10000);
            log.info("Starting initial API calls for dashboard data...");
            
            ExecutorService executorService = Executors.newFixedThreadPool(4);
            
            // API 호출 시 자기 자신의 IP를 사용 (도커 컨테이너 내에서는 서비스 이름 사용)
            String baseUrl = "http://localhost:8080";
            
            // 컨테이너 환경인지 확인
            if (System.getenv("DOCKER_CONTAINER") != null) {
                baseUrl = "http://127.0.0.1:8080"; // 컨테이너 내부에서 자기 자신 호출
            }
            
            final String apiUrl = baseUrl;
            
            // 헬스 체크 API 반복 호출
            executorService.submit(() -> {
                RestTemplate restTemplate = new RestTemplate();
                
                for (int i = 0; i < 10; i++) {
                    try {
                        restTemplate.getForEntity(apiUrl + "/api/health", String.class);
                        log.info("Health check API call #{}", i+1);
                        Thread.sleep(1000);
                    } catch (Exception e) {
                        log.error("Error calling health API: {}", e.getMessage());
                    }
                }
            });
            
            // 에러 API 몇 번 호출
            executorService.submit(() -> {
                RestTemplate restTemplate = new RestTemplate();
                
                for (int i = 0; i < 5; i++) {
                    try {
                        restTemplate.getForEntity(apiUrl + "/api/error", String.class);
                        log.info("Error API call #{}", i+1);
                    } catch (Exception e) {
                        log.info("Error API called successfully with error response");
                    }
                    try {
                        Thread.sleep(2000);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                    }
                }
            });
            
            // 랜덤 에러 API 몇 번 호출
            executorService.submit(() -> {
                RestTemplate restTemplate = new RestTemplate();
                
                for (int i = 0; i < 15; i++) {
                    try {
                        restTemplate.getForEntity(apiUrl + "/api/random-error", String.class);
                        log.info("Random Error API call #{}", i+1);
                    } catch (Exception e) {
                        log.info("Random Error API called with error response");
                    }
                    try {
                        Thread.sleep(1500);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                    }
                }
            });
            
            // Slow API 2번 호출
            executorService.submit(() -> {
                RestTemplate restTemplate = new RestTemplate();
                
                for (int i = 0; i < 2; i++) {
                    try {
                        restTemplate.getForEntity(apiUrl + "/api/slow", String.class);
                        log.info("Slow API call #{} completed", i+1);
                    } catch (Exception e) {
                        log.error("Error calling slow API: {}", e.getMessage());
                    }
                }
            });
            
            executorService.shutdown();
            try {
                executorService.awaitTermination(5, TimeUnit.MINUTES);
                log.info("All initial API calls completed");
            } catch (InterruptedException e) {
                log.error("API calls interrupted", e);
                Thread.currentThread().interrupt();
            }
        };
    }
} 
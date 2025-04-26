package com.example.targetapi.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;
import java.util.Random;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@RestController
@RequestMapping("/api")
public class SlowApiController {

    private final Random random = new Random();

    @GetMapping("/slow")
    public String slowApi() throws InterruptedException {
        log.info("Slow API called");
        // 10초 지연
        Thread.sleep(10000);
        log.info("Slow API completed");
        return "Completed after 10 seconds";
    }
    
    @GetMapping("/error")
    public ResponseEntity<String> errorApi() {
        log.error("Error API called - Simulating an error");
        return ResponseEntity.internalServerError().body("Simulated error occurred");
    }
    
    @GetMapping("/random-error")
    public ResponseEntity<String> randomErrorApi() {
        if (random.nextInt(10) < 3) {  // 30% 확률로 에러 발생
            log.error("Random Error API called - Error occurred");
            return ResponseEntity.internalServerError().body("Random error occurred");
        }
        log.info("Random Error API called - Success");
        return ResponseEntity.ok("Random error API completed successfully");
    }
    
    @GetMapping("/health")
    public String health() {
        return "OK";
    }
} 
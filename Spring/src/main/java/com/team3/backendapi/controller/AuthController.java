package com.team3.backendapi.controller;

import com.team3.backendapi.dto.ApiResponse;
import com.team3.backendapi.dto.UserDto;
import com.team3.backendapi.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173"})
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    // 로그인
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<UserDto.LoginResponse>> login(@RequestBody UserDto.LoginRequest request) {
        try {
            UserDto.LoginResponse response = userService.login(request);
            return ResponseEntity.ok(ApiResponse.<UserDto.LoginResponse>builder()
                    .success(true)
                    .message("로그인이 성공적으로 완료되었습니다.")
                    .data(response)
                    .build());
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(ApiResponse.<UserDto.LoginResponse>builder()
                            .success(false)
                            .message(e.getMessage())
                            .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<UserDto.LoginResponse>builder()
                            .success(false)
                            .message("로그인 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 회원가입
    @PostMapping("/register")
    public ResponseEntity<ApiResponse<UserDto.Response>> register(@RequestBody UserDto.CreateRequest request) {
        try {
            UserDto.Response user = userService.createUser(request);
            return ResponseEntity.status(HttpStatus.CREATED)
                    .body(ApiResponse.<UserDto.Response>builder()
                            .success(true)
                            .message("회원가입이 성공적으로 완료되었습니다.")
                            .data(user)
                            .build());
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(ApiResponse.<UserDto.Response>builder()
                            .success(false)
                            .message(e.getMessage())
                            .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<UserDto.Response>builder()
                            .success(false)
                            .message("회원가입 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 이메일 중복 확인
    @GetMapping("/check-email")
    public ResponseEntity<ApiResponse<Boolean>> checkEmail(@RequestParam String email) {
        try {
            boolean exists = userService.getUserByEmail(email) != null;
            return ResponseEntity.ok(ApiResponse.<Boolean>builder()
                    .success(true)
                    .message(exists ? "이미 사용 중인 이메일입니다." : "사용 가능한 이메일입니다.")
                    .data(exists)
                    .build());
        } catch (RuntimeException e) {
            // 사용자를 찾을 수 없으면 사용 가능한 이메일
            return ResponseEntity.ok(ApiResponse.<Boolean>builder()
                    .success(true)
                    .message("사용 가능한 이메일입니다.")
                    .data(false)
                    .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<Boolean>builder()
                            .success(false)
                            .message("이메일 확인 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 아이디 중복 확인
    @GetMapping("/check-username")
    public ResponseEntity<ApiResponse<Boolean>> checkUsername(@RequestParam String username) {
        try {
            boolean exists = userService.getUserByUsername(username) != null;
            return ResponseEntity.ok(ApiResponse.<Boolean>builder()
                    .success(true)
                    .message(exists ? "이미 사용 중인 아이디입니다." : "사용 가능한 아이디입니다.")
                    .data(exists)
                    .build());
        } catch (RuntimeException e) {
            // 사용자를 찾을 수 없으면 사용 가능한 아이디
            return ResponseEntity.ok(ApiResponse.<Boolean>builder()
                    .success(true)
                    .message("사용 가능한 아이디입니다.")
                    .data(false)
                    .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<Boolean>builder()
                            .success(false)
                            .message("아이디 확인 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }
}

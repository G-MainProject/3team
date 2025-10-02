package com.team3.backendapi.controller;

import com.team3.backendapi.dto.ApiResponse;
import com.team3.backendapi.dto.UserDto;
import com.team3.backendapi.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = {"http://localhost:3000", "http://localhost:5173"})
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    // 모든 사용자 조회
    @GetMapping
    public ResponseEntity<ApiResponse<List<UserDto.Response>>> getAllUsers() {
        try {
            List<UserDto.Response> users = userService.getAllUsers();
            return ResponseEntity.ok(ApiResponse.<List<UserDto.Response>>builder()
                    .success(true)
                    .message("사용자 목록을 성공적으로 조회했습니다.")
                    .data(users)
                    .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<List<UserDto.Response>>builder()
                            .success(false)
                            .message("사용자 목록 조회 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 활성 사용자만 조회
    @GetMapping("/active")
    public ResponseEntity<ApiResponse<List<UserDto.Response>>> getActiveUsers() {
        try {
            List<UserDto.Response> users = userService.getActiveUsers();
            return ResponseEntity.ok(ApiResponse.<List<UserDto.Response>>builder()
                    .success(true)
                    .message("활성 사용자 목록을 성공적으로 조회했습니다.")
                    .data(users)
                    .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<List<UserDto.Response>>builder()
                            .success(false)
                            .message("활성 사용자 목록 조회 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 사용자 검색 (이름으로)
    @GetMapping("/search")
    public ResponseEntity<ApiResponse<List<UserDto.Response>>> searchUsers(@RequestParam String name) {
        try {
            List<UserDto.Response> users = userService.searchUsersByName(name);
            return ResponseEntity.ok(ApiResponse.<List<UserDto.Response>>builder()
                    .success(true)
                    .message("사용자 검색을 성공적으로 완료했습니다.")
                    .data(users)
                    .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<List<UserDto.Response>>builder()
                            .success(false)
                            .message("사용자 검색 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 사용자 ID로 조회
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<UserDto.Response>> getUserById(@PathVariable Long id) {
        try {
            UserDto.Response user = userService.getUserById(id);
            return ResponseEntity.ok(ApiResponse.<UserDto.Response>builder()
                    .success(true)
                    .message("사용자 정보를 성공적으로 조회했습니다.")
                    .data(user)
                    .build());
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(ApiResponse.<UserDto.Response>builder()
                            .success(false)
                            .message(e.getMessage())
                            .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<UserDto.Response>builder()
                            .success(false)
                            .message("사용자 조회 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 사용자 생성
    @PostMapping
    public ResponseEntity<ApiResponse<UserDto.Response>> createUser(@RequestBody UserDto.CreateRequest request) {
        try {
            UserDto.Response user = userService.createUser(request);
            return ResponseEntity.status(HttpStatus.CREATED)
                    .body(ApiResponse.<UserDto.Response>builder()
                            .success(true)
                            .message("사용자가 성공적으로 생성되었습니다.")
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
                            .message("사용자 생성 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 사용자 수정
    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<UserDto.Response>> updateUser(@PathVariable Long id, @RequestBody UserDto.UpdateRequest request) {
        try {
            UserDto.Response user = userService.updateUser(id, request);
            return ResponseEntity.ok(ApiResponse.<UserDto.Response>builder()
                    .success(true)
                    .message("사용자가 성공적으로 수정되었습니다.")
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
                            .message("사용자 수정 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 사용자 삭제 (소프트 삭제)
    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<String>> deleteUser(@PathVariable Long id) {
        try {
            userService.deleteUser(id);
            return ResponseEntity.ok(ApiResponse.<String>builder()
                    .success(true)
                    .message("사용자가 성공적으로 삭제되었습니다.")
                    .data("사용자 ID: " + id)
                    .build());
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(ApiResponse.<String>builder()
                            .success(false)
                            .message(e.getMessage())
                            .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<String>builder()
                            .success(false)
                            .message("사용자 삭제 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }

    // 사용자 활성화
    @PostMapping("/{id}/activate")
    public ResponseEntity<ApiResponse<String>> activateUser(@PathVariable Long id) {
        try {
            userService.activateUser(id);
            return ResponseEntity.ok(ApiResponse.<String>builder()
                    .success(true)
                    .message("사용자가 성공적으로 활성화되었습니다.")
                    .data("사용자 ID: " + id)
                    .build());
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(ApiResponse.<String>builder()
                            .success(false)
                            .message(e.getMessage())
                            .build());
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.<String>builder()
                            .success(false)
                            .message("사용자 활성화 중 오류가 발생했습니다: " + e.getMessage())
                            .build());
        }
    }
}
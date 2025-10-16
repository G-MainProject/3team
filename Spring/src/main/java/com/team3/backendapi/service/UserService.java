package com.team3.backendapi.service;

import com.team3.backendapi.dto.UserDto;
import com.team3.backendapi.entity.User;
import com.team3.backendapi.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional
public class UserService {
    
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    
    // 사용자 생성
    public UserDto.Response createUser(UserDto.CreateRequest request) {
        // 이메일 중복 확인
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("이미 존재하는 이메일입니다.");
        }
        
        // 아이디 중복 확인
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("이미 존재하는 아이디입니다.");
        }
        
        // 비밀번호 암호화
        String encodedPassword = passwordEncoder.encode(request.getPassword());
        
        // 사용자 생성
        User user = User.builder()
                .email(request.getEmail())
                .name(request.getName())
                .gender(request.getGender())
                .birthDate(request.getBirthDate())
                .username(request.getUsername())
                .password(encodedPassword)
                .role(User.UserRole.USER)
                .isActive(true)
                .consentAgreed(Boolean.TRUE.equals(request.getConsentAgreed()))
                .consentAgreedAt(Boolean.TRUE.equals(request.getConsentAgreed()) ? java.time.LocalDateTime.now() : null)
                .build();
        
        User savedUser = userRepository.save(user);
        return convertToResponse(savedUser);
    }
    
    // 사용자 조회 (ID로)
    @Transactional(readOnly = true)
    public UserDto.Response getUserById(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        return convertToResponse(user);
    }
    
    // 사용자 조회 (이메일로)
    @Transactional(readOnly = true)
    public UserDto.Response getUserByEmail(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        return convertToResponse(user);
    }
    
    // 사용자 조회 (아이디로)
    @Transactional(readOnly = true)
    public UserDto.Response getUserByUsername(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        return convertToResponse(user);
    }
    
    // 모든 사용자 조회
    @Transactional(readOnly = true)
    public List<UserDto.Response> getAllUsers() {
        return userRepository.findAll().stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
    }
    
    // 활성 사용자만 조회
    @Transactional(readOnly = true)
    public List<UserDto.Response> getActiveUsers() {
        return userRepository.findByIsActiveTrue().stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
    }
    
    // 사용자 검색 (이름으로)
    @Transactional(readOnly = true)
    public List<UserDto.Response> searchUsersByName(String name) {
        return userRepository.findByNameContaining(name).stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
    }
    
    // 사용자 수정
    public UserDto.Response updateUser(Long id, UserDto.UpdateRequest request) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        
        // 이메일 중복 확인 (자신 제외)
        if (!user.getEmail().equals(request.getEmail()) && 
            userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("이미 존재하는 이메일입니다.");
        }
        
        // 아이디 중복 확인 (자신 제외)
        if (!user.getUsername().equals(request.getUsername()) && 
            userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("이미 존재하는 아이디입니다.");
        }
        
        // 사용자 정보 업데이트
        user.setEmail(request.getEmail());
        user.setName(request.getName());
        user.setGender(request.getGender());
        user.setBirthDate(request.getBirthDate());
        user.setUsername(request.getUsername());
        
        // 비밀번호가 제공된 경우에만 업데이트
        if (request.getPassword() != null && !request.getPassword().isEmpty()) {
            user.setPassword(passwordEncoder.encode(request.getPassword()));
        }
        
        // 수신 동의 변경 처리
        if (request.getConsentAgreed() != null) {
            boolean newConsent = Boolean.TRUE.equals(request.getConsentAgreed());
            boolean prevConsent = Boolean.TRUE.equals(user.getConsentAgreed());
            if (newConsent && !prevConsent) {
                user.setConsentAgreed(true);
                user.setConsentAgreedAt(java.time.LocalDateTime.now());
            } else if (!newConsent && prevConsent) {
                user.setConsentAgreed(false);
                user.setConsentAgreedAt(null);
            }
        }
        
        User updatedUser = userRepository.save(user);
        return convertToResponse(updatedUser);
    }
    
    // 사용자 삭제 (소프트 삭제)
    public void deleteUser(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        
        user.setIsActive(false);
        userRepository.save(user);
    }
    
    // 사용자 활성화
    public void activateUser(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        
        user.setIsActive(true);
        userRepository.save(user);
    }
    
    // 로그인
    @Transactional(readOnly = true)
    public UserDto.LoginResponse login(UserDto.LoginRequest request) {
        
        // 이메일 또는 아이디로 사용자 찾기
        User user = userRepository.findByEmailOrUsername(request.getEmailOrUsername())
                .orElseThrow(() -> {
                    return new RuntimeException("사용자를 찾을 수 없습니다.");
                });
        
        
        // 비밀번호 확인 (하이브리드 방식: BCrypt 또는 평문 비교)
        boolean passwordMatches;
        
        // BCrypt로 암호화된 비밀번호인지 확인 (BCrypt 해시는 $2a$로 시작)
        if (user.getPassword().startsWith("$2a$")) {
            // BCrypt로 암호화된 비밀번호와 비교
            passwordMatches = passwordEncoder.matches(request.getPassword(), user.getPassword());
        } else {
            // 평문 비밀번호와 비교 (기존 사용자용)
            passwordMatches = request.getPassword().equals(user.getPassword());
        }
        
        
        if (!passwordMatches) {
            throw new RuntimeException("비밀번호가 일치하지 않습니다.");
        }
        
        // 활성 사용자 확인
        if (!user.getIsActive()) {
            throw new RuntimeException("비활성화된 사용자입니다.");
        }
        
        return UserDto.LoginResponse.builder()
                .id(user.getId())
                .email(user.getEmail())
                .name(user.getName())
                .username(user.getUsername())
                .gender(user.getGender())
                .birthDate(user.getBirthDate())
                .role(user.getRole())
                .token("dummy-token") // 나중에 JWT 토큰으로 교체
                .build();
    }
    
    // 패스워드 확인
    public boolean verifyPassword(UserDto.LoginRequest request) {
        User user = userRepository.findByEmailOrUsername(request.getEmailOrUsername())
                .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
        
        boolean passwordMatches;
        
        // BCrypt로 암호화된 비밀번호인지 확인 (BCrypt 해시는 $2a$로 시작)
        if (user.getPassword().startsWith("$2a$")) {
            // BCrypt로 암호화된 비밀번호와 비교
            passwordMatches = passwordEncoder.matches(request.getPassword(), user.getPassword());
        } else {
            // 평문 비밀번호와 비교 (기존 사용자용)
            passwordMatches = request.getPassword().equals(user.getPassword());
        }
        
        return passwordMatches;
    }
    
    // Entity를 Response DTO로 변환
    private UserDto.Response convertToResponse(User user) {
        return UserDto.Response.builder()
                .id(user.getId())
                .email(user.getEmail())
                .name(user.getName())
                .gender(user.getGender())
                .birthDate(user.getBirthDate())
                .username(user.getUsername())
                .role(user.getRole())
                .isActive(user.getIsActive())
                .createdAt(user.getCreatedAt())
                .updatedAt(user.getUpdatedAt())
                .consentAgreed(user.getConsentAgreed())
                .consentAgreedAt(user.getConsentAgreedAt())
                .build();
    }
}

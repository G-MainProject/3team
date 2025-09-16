package com.team3.backendapi.repository;

import com.team3.backendapi.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    // 이메일로 사용자 찾기
    Optional<User> findByEmail(String email);
    
    // 아이디로 사용자 찾기
    Optional<User> findByUsername(String username);
    
    // 이메일 또는 아이디로 사용자 찾기
    @Query("SELECT u FROM User u WHERE u.email = :emailOrUsername OR u.username = :emailOrUsername")
    Optional<User> findByEmailOrUsername(@Param("emailOrUsername") String emailOrUsername);
    
    // 활성 사용자만 조회
    List<User> findByIsActiveTrue();
    
    // 성별로 사용자 조회
    List<User> findByGender(User.Gender gender);
    
    // 생년월일 범위로 사용자 조회
    List<User> findByBirthDateBetween(LocalDate startDate, LocalDate endDate);
    
    // 이름으로 사용자 검색 (부분 일치)
    @Query("SELECT u FROM User u WHERE u.name LIKE %:name% AND u.isActive = true")
    List<User> findByNameContaining(@Param("name") String name);
    
    // 이메일로 사용자 존재 여부 확인
    boolean existsByEmail(String email);
    
    // 아이디로 사용자 존재 여부 확인
    boolean existsByUsername(String username);
    
    // 활성 사용자 수 조회
    @Query("SELECT COUNT(u) FROM User u WHERE u.isActive = true")
    long countActiveUsers();
}

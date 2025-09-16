import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Login.module.css';
import logoH from '../../assets/images/logoH.png';
import naver from '../../assets/images/naver.svg';
import google from '../../assets/images/google.svg';
import kakao from '../../assets/images/kakao.svg';
import HomeNav from '../../component/Nav/HomeNav';
import apiService from '../../services/api';
import Footer from '../../component/Footer/Footer';
import { useAuth } from '../../contexts/AuthContext';


export default function Login() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [formData, setFormData] = useState(() => {
        // 초기 폼 데이터를 localStorage에서 읽어오기
        try {
            const savedId = localStorage.getItem('savedId');
            return {
                emailOrUsername: savedId || '',
                password: ''
            };
        } catch {
            return {
                emailOrUsername: '',
                password: ''
            };
        }
    });
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(() => {
        // 초기 상태를 localStorage에서 읽어오기
        try {
            return localStorage.getItem('savedId') !== null;
        } catch {
            return false;
        }
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);


    const handleChange = (e) => {
        const newValue = e.target.value;
        setFormData({
            ...formData,
            [e.target.name]: newValue
        });
        
        // 아이디 입력 시 체크박스가 체크되어 있으면 즉시 저장
        if (e.target.name === 'emailOrUsername' && rememberMe && newValue.trim()) {
            localStorage.setItem('savedId', newValue);
        }
    };

    const togglePassword = () => {
        setShowPassword((prev) => !prev);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);

        // 아이디 저장 여부에 따라 localStorage 업데이트
        if (rememberMe && formData.emailOrUsername.trim()) {
            localStorage.setItem('savedId', formData.emailOrUsername);
        } else {
            localStorage.removeItem('savedId');
        }

        try {
            const response = await apiService.post('/auth/login', formData);
            
            if (response.success) {
                setSuccess(true);
                // AuthContext를 통해 로그인 상태 관리
                login(response.data);
                
                setTimeout(() => {
                    navigate('/dashboard');
                }, 1500);
            } else {
                setError(response.message || '로그인에 실패했습니다.');
            }
        } catch (err) {
            setError(err.response?.data?.message || '로그인 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.loginContainer}>
            <HomeNav />
            <div className={styles.loginContent}>
                <form className={styles.loginForm} onSubmit={handleSubmit}>
                    <div className={styles.loginLogo}>
                        <img src={logoH} alt="3Team Logo" />
                    </div>

                    <p>로그인</p>

                    <div className={styles.loginFormGroup}>
                        <input
                            type="text"
                            id="emailOrUsername"
                            name="emailOrUsername"
                            className={styles.emailOrUsername}
                            placeholder="이메일 또는 아이디"
                            value={formData.emailOrUsername}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className={styles.loginFormGroup}>
                        <input
                            type={showPassword ? 'text' : 'password'}
                            id="password"
                            name="password"
                            className={styles.password}
                            placeholder="비밀번호"
                            value={formData.password}
                            onChange={handleChange}
                            required
                        />
                        <i
                            className={`fa ${showPassword ? 'fa-eye-slash' : 'fa-eye'} fa-lg`}
                            onClick={togglePassword}
                            style={{ cursor: 'pointer' }}
                        />
                    </div>

                    <div className={`${styles.loginFormGroup} ${styles.loginCheck}`}>
                        <input
                            type="checkbox"
                            id="remember-check"
                            checked={rememberMe}
                            onChange={(e) => {
                                const isChecked = e.target.checked;
                                setRememberMe(isChecked);
                                
                                // 체크박스 상태에 따라 즉시 localStorage 업데이트
                                if (isChecked && formData.emailOrUsername.trim()) {
                                    localStorage.setItem('savedId', formData.emailOrUsername);
                                } else {
                                    localStorage.removeItem('savedId');
                                }
                            }}
                        />
                        <label htmlFor="remember-check" style={{ cursor: 'pointer' }}>아이디 저장하기</label>
                    </div>

                    {error && (
                        <div className={styles.errorMessage}>
                            ❌ {error}
                        </div>
                    )}
                    
                    {success && (
                        <div className={styles.successMessage}>
                            ✅ 로그인 성공! 대시보드로 이동합니다...
                        </div>
                    )}

                    <div className={styles.loginFormGroup}>
                        <button type="submit" className={styles.loginButton} disabled={loading || success}>
                            {loading ? '로그인 중...' : success ? '로그인 성공!' : '로그인'}
                        </button>
                    </div>

                    <div className={`${styles.loginFormGroup} ${styles.loginMenu}`}>
                        <button type="button" className="regist-button" onClick={() => navigate('/signup')}>
                            가입하기
                        </button>
                        <a href="#">비밀번호를 잊어버리셨나요?</a>
                    </div>

                    <div className={`${styles.loginFormGroup} ${styles.etc}`}>또는</div>

                    <div className={`${styles.loginFormGroup} ${styles.loginFormGroupContainer}`}>
                        <button type="button" className={styles.kLogin}>
                            <img src={kakao} alt="kakao" />
                            카카오로 시작하기
                        </button>
                        <button type="button" className={styles.nLogin}>
                            <img src={naver} alt="naver" />
                            네이버로 시작하기
                        </button>
                        <button type="button" className={styles.gLogin}>
                            <img src={google} alt="google" />
                            Google로 시작하기
                        </button>
                    </div>

                    <div className={styles.loginInfo}>
                        <p>테스트 계정:</p>
                        <p>관리자: admin / admin</p>
                    </div>
                </form>
            </div>
            <Footer />
        </div>
    );
}
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './HomeNav.css';
import logo from '../../assets/images/logo.png';
import { useAuth } from '../../contexts/AuthContext';

export default function HomeNav() {
    const { user, isAuthenticated, logout } = useAuth();
    const [isMenuOpen] = useState(false);
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        alert('로그아웃 되었습니다.');
        navigate('/');
    };

    return (
        <nav className={`home-nav-container ${isMenuOpen ? 'open' : ''}`}>
            <div className="home-nav-wrapper">
                <div className="home-nav-logo">
                    <Link to="/"><img src={logo} alt="로고" className="home-logo-image" /></Link>
                </div>
                <div className="home-nav-actions">
                    {isAuthenticated() ? (
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button className="home-logout-button" onClick={handleLogout}>
                                로그아웃
                            </button>
                            <button className="home-dashboard-button" onClick={() => navigate('/dashboard')}>
                                대시보드
                            </button>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button className="home-login-button" onClick={() => navigate('/login')}>
                                로그인                        
                            </button>
                            <button className="home-signup-button" onClick={() => navigate('/signup')}>
                                회원가입                        
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    );
}

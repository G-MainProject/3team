import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LeftNav.css';
import logo from '../../assets/images/logo.png';
import banner1 from '../../assets/images/banner1.png';
import { useAuth } from '../../contexts/AuthContext';

export default function Nav() {
    const navigate = useNavigate();
    const { logout } = useAuth();

    const handleLogout = () => {
        logout();
        alert('로그아웃 되었습니다.');
        // Dashboard에서 로그아웃 시 홈페이지로 이동
        window.location.href = '/';
    };
    return (
        <div className='left-nav-container'>
            <div className='left-nav-wrapper'>
                <button className='left-nav-logo' onClick={() => navigate('/dashboard')}><img src={logo} alt="logoWOC" /></button>
                <div className='left-nav-menu'>
                    <button className='left-nav-item' onClick={() => navigate('/stock-analysis')}>
                        <i className="fas fa-chart-line"></i>
                        주식 분석
                    </button>
                    <button className='left-nav-item' onClick={() => navigate('/ai-insights')}>
                        <i className="fas fa-search"></i>
                        AI 인사이트
                    </button>
                </div>
                <div className='left-nav-bottom'>
                    <a href="#" className='left-nav-banner'>
                        <img src={banner1} alt="Upgrade to PRO Account" />
                    </a>
                    <button className='left-nav-logout' onClick={handleLogout}>
                        <span>로그아웃</span>
                        <i className="fas fa-arrow-right-from-bracket"></i>
                    </button>
                </div>
            </div>
        </div>
    );
}
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
                <a href="/" className='left-nav-logo'><img src={logo} alt="logoWOC" /></a>
                <div className='left-nav-menu'>
                    <button className='left-nav-item'>
                        <i className="fas fa-chart-line"></i>
                        주식 정보
                    </button>
                    <button className='left-nav-item'>
                        <i className="fas fa-file-invoice-dollar"></i>
                        재무제표
                    </button>
                    <button className='left-nav-item'>
                        <i className="fas fa-newspaper"></i>
                        뉴스 분석
                    </button>
                    <button className='left-nav-item'>
                        <i className="fas fa-robot"></i>
                        AI 분석
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
import React from 'react';
import './Nav.css';
import logo from '../../assets/images/logo.png';
import banner1 from '../../assets/images/banner1.png';

export default function Nav() {
    return (
        <div className='nav'>
            <div className='nav-wrapper'>
                <a href="/" className='nav-logo'><img src={logo} alt="logoWOC" /></a>
                <div className='nav-menu'>
                    <button className='nav-item'>
                        <i className="fas fa-chart-line"></i>
                        주식 정보
                    </button>
                    <button className='nav-item'>
                        <i className="fas fa-chart-area"></i>
                        일별 주가 차트
                    </button>
                    <button className='nav-item'>
                        <i className="fas fa-file-invoice-dollar"></i>
                        재무제표
                    </button>
                    <button className='nav-item'>
                        <i className="fas fa-newspaper"></i>
                        뉴스 분석
                    </button>
                    <button className='nav-item'>
                        <i className="fas fa-robot"></i>
                        AI 분석
                    </button>
                </div>
                <div className='nav-bottom'>
                    <a href="#" className='nav-banner'>
                        <img src={banner1} alt="Upgrade to PRO Account" />
                    </a>
                    <button className='nav-logout'>
                        <span>로그아웃</span>
                        <i className="fas fa-arrow-right-from-bracket"></i>
                    </button>
                </div>
            </div>
        </div>
    );
}
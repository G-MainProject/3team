import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './HomeNav.css';
import logo from '../../assets/images/logo.png';

export default function HomeNav() {
    const [isMenuOpen] = useState(false);
    const navigate = useNavigate();

    return (
        <nav className={`home-nav-container ${isMenuOpen ? 'open' : ''}`}>
            <div className="home-nav-wrapper">
                <div className="home-nav-logo">
                    <Link to="/"><img src={logo} alt="로고" className="home-logo-image" /></Link>
                </div>
                <div className="home-nav-download">
                    <button className="home-login-button" onClick={() => navigate('/login')}>
                        로그인                        
					</button>
                </div>
            </div>
        </nav>
    );
}

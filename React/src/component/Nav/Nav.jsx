import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Nav.css';
import logo from '../../assets/images/logo.png';

export default function Nav() {
    const [isMenuOpen] = useState(false);
    const navigate = useNavigate();

    return (
        <nav className={`nav-container ${isMenuOpen ? 'open' : ''}`}>
            <div className="nav-wrapper">
                <div className="nav-logo">
                    <Link to="/login"><img src={logo} alt="로고" className="logo-image" /></Link>
                </div>
                <div className="nav-download">
                    <button className="login-button" onClick={() => navigate('/login')}>
                        로그인                        
					</button>
                </div>
            </div>
        </nav>
    );
}

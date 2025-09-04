import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Nav.css';
import logo from '../../assets/images/logo.png';

export default function Nav() {
    const [isMenuOpen] = useState(false);

    return (
        <nav className={`nav-container ${isMenuOpen ? 'open' : ''}`}>
            <div className="nav-wrapper">
                <div className="nav-logo">
                    <Link to="/"><img src={logo} alt="로고" className="logo-image" /></Link>
                </div>
                <div className="nav-download">
                    <button className="login-button">
                        로그인                        
					</button>
                </div>
            </div>
        </nav>
    );
}

import React from 'react';
import './Login.css';
import logoS from '../../assets/images/logoS.png';

export default function Login() {
    return (
        <div className='login-container'>
            <div className='login-card'>
                <img src={logoS} alt="logoS" />
                <p className='login-card-title'>로그인</p>
                <input type="text" placeholder='ID' />
                <input type="password" placeholder='Password' />
                <button>Login</button>
                <div className='login-card-footer'>
                    <p>Don't have an account? <span>Sign up</span></p>
                </div>
            </div>
        </div>
    );
}

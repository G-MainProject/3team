import React from 'react'
import './Footer.css'
import logo from '../../assets/images/logo.png';

const Footer = () => {
  return (
    <div className='footer-container'>
      <div className='footer-content'>
        <div className='footer-paper'>
          <div className='footer-header'>
            <h3>더 많은 정보가 필요하신가요?</h3>
            <p>더 자세한 분석과 인사이트를 확인해보세요</p>
          </div>
          
          <div className='footer-links'>
            
            <div className='footer-section'>
              <h4>데이터 소스</h4>
              <ul>
                <li><a href="#">DART API</a></li>
                <li><a href="#">Naver News API</a></li>
                <li><a href="#">Gemini API</a></li>
                <li><a href="#">X API</a></li>
                <li><a href="#">Threads API</a></li>
              </ul>
            </div>
            
            <div className='footer-section'>
              <h4>지원</h4>
              <ul>
                <li><a href="#">도움말</a></li>
                <li><a href="#">문의하기</a></li>
                <li><a href="#">피드백</a></li>
                <li><a href="#">업데이트</a></li>
              </ul>
            </div>
          </div>		  
          
          <div className='footer-bottom'>
            <div className='footer-logo'>
				<img src={logo} alt="logo" />
             	<p>: 오늘의 매수/매도 인사이트</p>
            </div>
            <div className='footer-copyright'>
             	 <p>&copy; 2024 SIGNALKR. All rights reserved.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Footer
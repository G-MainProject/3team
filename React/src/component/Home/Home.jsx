import React, { useRef, useState } from 'react';
// import { useNavigate } from 'react-router-dom';
import './Home.css';
import signalVideo from '../../assets/images/signal.mp4';
import brity from '../../assets/images/brity.png';
import ocr from '../../assets/images/ocr.jpg';
import emotion from '../../assets/images/emotion.jpg';

export default function Home() {
    const [activeIdx, setActiveIdx] = useState(0);
    const aboutRef = useRef(null);
    function goToAboutSection() {
        if (aboutRef.current) {
            aboutRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    const navItems = [
        { label: 'SIGNAL', onClick: () => setActiveIdx(0) },
        { label: 'ABOUT', onClick: () => { setActiveIdx(1); goToAboutSection(); } },
        { label: 'START', onClick: () => setActiveIdx(2) },
    ];

    return (
        <div className="home-container">
            <ul
                className='home-nav'
                onMouseLeave={() => setActiveIdx(0)}
            >
                {navItems.map((item, idx) => (
                    <li key={idx}>
                        <button
                            className={activeIdx === idx ? 'home-nav-on' : ''}
                            onMouseEnter={() => setActiveIdx(idx)}
                            onClick={item.onClick}
                        >
                            {item.label}
                        </button>
                    </li>
                ))}
            </ul>

            <div className='signal'>
                <p className="signal-main">
                    NOISE 속에서 <br/>
                    진짜 SIGNAL을 찾다 <br />
                </p>
                <p className="signal-sub">
                    우리는 수많은 정보와 소음 속에서<br />
                    진짜 가치와 의미를 발견합니다.<br />
                    신뢰할 수 있는 데이터와 분석으로<br />
                    당신의 선택에 확실한 신호를 제공합니다.<br />
                    지금, 우리와 함께 새로운 가능성을 찾아보세요.
                </p>
            </div>
            
            <div className='signal2'>
                <video className='signal-video' autoPlay loop muted>
                    <source src={signalVideo} type='video/mp4' />
                </video>
            </div>

			<div className="signal3" ref={aboutRef}>
                <div className="signal-header">
                    <p>ABOUT</p>
                </div>
                <div className="signal-card-wrapper">
                    <div className="signal-card">
                        <img src={brity} alt="brity" />
                        <p className="signal-card-title">Brity RPA</p>
                        <p className="signal-card-content">
                            증권사 사이트에서 재무제표·공시를 자동으로 수집해 1차 데이터셋을 만듭니다.
                            SIGNAL에서 제공하는 표준 필드로 매핑하며, 수집 로그와 예외는 대시보드에서
                            즉시 확인할 수 있습니다.
                        </p>
                    </div>
                    <div className="signal-card">
                        <img src={ocr} alt="ocr" />
                        <p className="signal-card-title">AI OCR</p>
                        <p className="signal-card-content">
                            RPA가 수집한 페이지 전체를 자동으로 스캔해 텍스트를 추출하고 표·주석까지 함께
                            인식합니다. 추출값을 1차 데이터셋과 자동 대조해 누락·오류를 표시하고, 클릭 한 번으로
                            교정·승인할 수 있습니다. 최종 값과 원본 스냅샷은 함께 보관됩니다.
                        </p>
                    </div>
                    <div className="signal-card">
                        <img src={emotion} alt="emotion" />
                        <p className="signal-card-title">NLP 감성·이슈 트래커</p>
                        <p className="signal-card-content">
                            뉴스와 댓글을 실시간으로 모니터링해 종목·이슈별 감성 점수와 핵심 키워드를
                            보여줍니다. 분위기가 급격히 바뀌면 알림을 보내고, 히트맵/타임라인으로 흐름을
                            한눈에 파악할 수 있습니다.
                        </p>
                    </div>
                </div>
			</div>
        </div>
    );
}

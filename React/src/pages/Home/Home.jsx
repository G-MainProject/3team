import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Home.css';
import signalVideo from '../../assets/images/signal.mp4';
import brity from '../../assets/images/brity.png';
import ocr from '../../assets/images/ocr.jpg';
import emotion from '../../assets/images/emotion.jpg';

export default function Home() {
    const [activeIdx, setActiveIdx] = useState(-1);
    const [isScrolling, setIsScrolling] = useState(false);
    const [lastScrollY, setLastScrollY] = useState(0);
    const aboutRef = useRef(null);
    const signalRef = useRef(null);
    const startRef = useRef(null);
    const navigate = useNavigate();
    
    function goToAboutSection() {
        setIsScrolling(true);
        setActiveIdx(1);
        if (aboutRef.current) {
            aboutRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        // 스크롤 완료 후 자동 감지 재개
        setTimeout(() => {
            setIsScrolling(false);
        }, 1000);
    }
    
    function goToTop() {
        setIsScrolling(true);
        setActiveIdx(0);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        // 스크롤 완료 후 자동 감지 재개
        setTimeout(() => {
            setIsScrolling(false);
        }, 1000);
    }
    
    function goToStartSection() {
        setIsScrolling(true);
        setActiveIdx(2);
        if (startRef.current) {
            startRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        // 스크롤 완료 후 자동 감지 재개
        setTimeout(() => {
            setIsScrolling(false);
        }, 1000);
    }
    
    useEffect(() => {
        // 페이지 로드 시 스크롤을 최상단으로 설정
        window.scrollTo(0, 0);
        setActiveIdx(0);
    }, []);

    useEffect(() => {
        const handleScroll = () => {
            const currentScrollY = window.scrollY;
            setLastScrollY(currentScrollY);
        };

        window.addEventListener('scroll', handleScroll, { passive: true });

        return () => {
            window.removeEventListener('scroll', handleScroll);
        };
    }, []);

    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            if (isScrolling) return;
            
            entries.forEach(entry => {
                const sectionId = entry.target.dataset.section;
                
                if (entry.isIntersecting) {
                    if (sectionId === 'about') {
                        setActiveIdx(1);
                    } else if (sectionId === 'start') {
                        setActiveIdx(2);
                        // START 섹션에 도달하면 자동으로 하단까지 스크롤 (아래로 스크롤할 때만)
                        const currentScrollY = window.scrollY;
                        const isScrollingDown = currentScrollY > lastScrollY;
                        
                        if (startRef.current && isScrollingDown) {
                            setIsScrolling(true);
                            startRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
                            setTimeout(() => {
                                setIsScrolling(false);
                            }, 1000);
                        }
                    } else if (sectionId === 'signal') {
                        setActiveIdx(0);
                    }
                }
            });
        }, { 
            threshold: 0.1, // 섹션이 10% 이상 보일 때 감지
            rootMargin: '0px 0px 0px 0px' // 마진 없이 정확한 감지
        });

        // 각 섹션 관찰 시작
        if (signalRef.current) {
            signalRef.current.dataset.section = 'signal';
            observer.observe(signalRef.current);
        }
        if (aboutRef.current) {
            aboutRef.current.dataset.section = 'about';
            observer.observe(aboutRef.current);
        }
        if (startRef.current) {
            startRef.current.dataset.section = 'start';
            observer.observe(startRef.current);
        }

        return () => {
            observer.disconnect();
        };
    }, [isScrolling, lastScrollY]);
    const navItems = [
        { label: 'SIGNAL', onClick: () => { setActiveIdx(0); goToTop(); } },
        { label: 'ABOUT', onClick: () => { setActiveIdx(1); goToAboutSection(); } },
        { label: 'START', onClick: () => { setActiveIdx(2); goToStartSection(); } },
    ];

    return (
        <div className="home-container">
            <ul
                className='home-nav'
                style={{ pointerEvents: isScrolling ? 'none' : 'auto' }}
                onMouseLeave={() => {
                    // 마우스가 나가면 현재 스크롤 위치에 맞는 버튼으로 복원
                    if (!isScrolling) {
                        if (aboutRef.current && startRef.current) {
                            const aboutRect = aboutRef.current.getBoundingClientRect();
                            const startRect = startRef.current.getBoundingClientRect();
                            
                            // Intersection Observer와 동일한 로직
                            if (aboutRect.top <= window.innerHeight * 0.2 && aboutRect.bottom >= window.innerHeight * 0.2) {
                                setActiveIdx(1);
                            } else if (startRect.top <= window.innerHeight * 0.8) {
                                setActiveIdx(2);
                            } else {
                                setActiveIdx(0);
                            }
                        }
                    }
                }}
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

            <div className='signal' ref={signalRef}>
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

            <div className="signal4" ref={startRef}>
                <div className="signal4-container">
                    {/* <p>Signal: 오늘의 매수/매도 인사이트</p> */}
                    <button onClick={() => navigate('/dashboard')}>
                        <span className="button-text">SIGNAL 시작하기</span>
                        <i className="fas fa-play button-icon"></i>
                    </button>
                 </div>
             </div>
        </div>
    );
}

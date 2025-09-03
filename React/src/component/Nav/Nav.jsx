import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import html2canvas from 'html2canvas';
import './Nav.css';
import ENG_LOGO from '../../assets/ENG_LOGO.png';

export default function Nav() {
	const [isMenuOpen, setIsMenuOpen] = useState(false);

	useEffect(() => {
		const handleResize = () => {
			// 창 너비가 1024px보다 커지면 메뉴를 닫습니다.
			if (window.innerWidth > 1024) {
				setIsMenuOpen(false);
			}
		};

		// resize 이벤트 리스너 추가
		window.addEventListener('resize', handleResize);

		// 컴포넌트가 언마운트될 때 이벤트 리스너 제거
		return () => {
			window.removeEventListener('resize', handleResize);
		};
	}, []); // 빈 배열을 전달하여 컴포넌트가 마운트될 때 한 번만 실행되도록 설정

	const toggleMenu = () => {
		setIsMenuOpen(!isMenuOpen);
	};

	const Downloadhandler = () => {
		// document.body는 현재 보여지는 웹페이지 전체를 의미
		html2canvas(document.body).then((canvas) => {
			// 캔버스를 이미지 데이터(URL)로 변환
			const imageData = canvas.toDataURL('image/png');

			// 임시 링크(a 태그)를 생성
			const link = document.createElement('a');
			link.href = imageData; // 이미지 데이터 URL을 링크의 href로 설정
			link.download = '보고서.png'; // 다운로드될 파일의 이름을 지정

			// 링크를 문서에 추가하고 클릭 이벤트를 발생시켜 다운로드를 실행
			document.body.appendChild(link);
			link.click();

			// 다운로드 후 임시 링크를 문서에서 제거
			document.body.removeChild(link);
		});
	};

	return (
		<nav className={`nav-container ${isMenuOpen ? 'open' : ''}`}>
			<div className="nav-wrapper">
				{/* 1. 로고 영역 */}
				<div className="nav-logo">
					<Link to="/"><img src={ENG_LOGO} alt="로고" className="logo-image" /></Link>
				</div>

				{/* 2. 메뉴 영역 (가운데 정렬) */}
				<ul className="nav-menu">
					<li><Link to="/team">회사 소개</Link></li>
					<li><Link to="/notice">공지사항</Link></li>
					<li><a href="https://support.toss.im" target="_blank" rel="noopener noreferrer">고객센터</a></li>
					<li><a href="https://support.toss.im/faq" target="_blank" rel="noopener noreferrer">자주 묻는 질문</a></li>
					<li><Link to="/tosscert">토스인증서</Link></li>
					<li><Link to="/career">채용</Link></li>
				</ul>

				{/* 3. 다운로드 버튼 영역 */}
				<div className="nav-download">
					<button onClick={Downloadhandler} className="download-button">
						보고서 다운로드
					</button>
				</div>

				{/* 모바일 화면에서 보여질 햄버거 메뉴 아이콘 */}
				<div className={`nav-mobile-icon ${isMenuOpen ? 'open' : ''}`} onClick={toggleMenu}>
					<span></span>
					<span></span>
					<span></span>
				</div>
			</div>
			<div className="nav-mobile-menu">
				<ul>
					<li><Link to="/team">회사 소개</Link></li>
					<li><Link to="/notice">공지사항</Link></li>
					<li><a href="https://support.toss.im" target="_blank" rel="noopener noreferrer">고객센터</a></li>
					<li><a href="https://support.toss.im/faq" target="_blank" rel="noopener noreferrer">자주 묻는 질문</a></li>
					<li><Link to="/tosscert">토스인증서</Link></li>
					<li><Link to="/career">채용</Link></li>
				</ul>
				<button onClick={Downloadhandler} className="mobile-download-button">보고서 다운로드</button>
			</div>
		</nav>
	);
}

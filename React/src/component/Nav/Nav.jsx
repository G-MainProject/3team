import React from 'react';
import { Link } from 'react-router-dom';
import html2canvas from 'html2canvas';
import './Nav.css';

export default function Nav() {
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
		<nav className="nav-container">
			<div className="nav-wrapper">
				{/* 1. 로고 영역 */}
				<div className="nav-logo">
					<Link to="/">Logo</Link>
				</div>

				{/* 2. 메뉴 영역 (가운데 정렬) */}
				<ul className="nav-menu">
					<li>
						<Link to="/product">알림</Link>
					</li>
					<li>
						<Link to="/company">프로필</Link>
					</li>
					<li>
						<Link to="/support">고객지원</Link>
					</li>
				</ul>

				{/* 3. 다운로드 버튼 영역 */}
				<div className="nav-download">
					<button onClick={Downloadhandler} className="download-button">
						보고서 다운로드
					</button>
				</div>

				{/* 모바일 화면에서 보여질 햄버거 메뉴 아이콘 */}
				<div className="nav-mobile-icon">
					<span></span>
					<span></span>
					<span></span>
				</div>
			</div>
		</nav>
	);
}

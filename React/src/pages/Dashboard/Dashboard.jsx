import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import RightNav from '../../component/Nav/RightNav';
import Footer from '../../component/Footer/Footer';
import Chart from '../../component/Chart/Chart';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import MyWordCloud from '../../component/WordCloud/MyWordCloud';

export default function Dashboard() {
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	useEffect(() => {
		const dashboardMain = document.querySelector('.dashboard-main');

		const handleScroll = () => {
			if (!dashboardMain) return;

			const scrollTop = dashboardMain.scrollTop;
			const scrollHeight = dashboardMain.scrollHeight;
			const clientHeight = dashboardMain.clientHeight;

			const scrollPercentage = (scrollTop + clientHeight) / scrollHeight;

			if (scrollPercentage > 0.99) {
				if (!showFooterButtonRef.current) {
					setButtonAnimation('');
					setShowFooterButton(true);
					showFooterButtonRef.current = true;
				}
				setShowFooter(true);
			} else {
				if (showFooterButtonRef.current) {
					setButtonAnimation('hiding');

					const button = document.querySelector('.footer-scroll-button');
					if (button) {
						const handleAnimationEnd = () => {
							setShowFooterButton(false);
							setButtonAnimation('');
							showFooterButtonRef.current = false;
							button.removeEventListener('animationend', handleAnimationEnd);
						};
						button.addEventListener('animationend', handleAnimationEnd);
					} else {
						setShowFooterButton(false);
						setButtonAnimation('');
						showFooterButtonRef.current = false;
					}
				}
				setShowFooter(false);
			}
		};

		if (dashboardMain) {
			dashboardMain.addEventListener('scroll', handleScroll);
			return () => dashboardMain.removeEventListener('scroll', handleScroll);
		}
	}, [allowScrollToFooter]);

	// 전체 페이지 스크롤 제한
	useEffect(() => {
		const handlePageScroll = (e) => {
			const dashboardMain = document.querySelector('.dashboard-main');
			if (!dashboardMain) return;

			const scrollTop = dashboardMain.scrollTop;
			const scrollHeight = dashboardMain.scrollHeight;
			const clientHeight = dashboardMain.clientHeight;
			const scrollPercentage = (scrollTop + clientHeight) / scrollHeight;

			// Footer 영역에 있을 때 위로 스크롤 제한
			if (isInFooter && e.deltaY < 0) {
				e.preventDefault();
				return;
			}

			// Dashboard에서 Footer로 가는 것을 제한
			if (!allowScrollToFooter && scrollPercentage >= 1.0 && e.deltaY > 0) {
				e.preventDefault();
				dashboardMain.scrollTo({
					top: dashboardMain.scrollHeight - clientHeight,
					behavior: 'smooth',
				});
			}
		};

		window.addEventListener('wheel', handlePageScroll, { passive: false });
		return () => window.removeEventListener('wheel', handlePageScroll);
	}, [allowScrollToFooter, isInFooter]);

	const handleButtonClick = () => {
		if (isInFooter) {
			// Footer에서 Dashboard로 이동 - fadeOut 애니메이션 적용
			setButtonAnimation('fade-out');

			// 애니메이션 완료 후 상태 변경
			setTimeout(() => {
				setAllowScrollToFooter(false);
				setIsInFooter(false);

				const dashboardMain = document.querySelector('.dashboard-main');
				if (dashboardMain) {
					dashboardMain.scrollTo({
						top: 0,
						behavior: 'smooth',
					});
				}
			}, 300); // fadeOut 애니메이션 시간과 동일
		} else {
			// Dashboard에서 Footer로 이동
			setAllowScrollToFooter(false);
			setIsInFooter(true);

			if (footerRef.current) {
				footerRef.current.scrollIntoView({
					behavior: 'smooth',
					block: 'start',
				});
			}
		}
	};

	return (
		<div className="dashboard-container">
			<div className="dashboard-content">
				<LeftNav />
				<div className="dashboard-main">
					<div className="dashboard-grid">
						<TopNav />

						{/* 주식 정보 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>주식 정보</h2>
									<p>실시간 주가 및 주요 지표</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="stock-info-section">
								{/* KPI 차트들 */}
								<div className="kpi-charts-grid">
									<div className="kpi-chart-item">
										<h3>실시간 주가 차트</h3>
										<div className="kpi-chart-placeholder">
											{/* <p>실시간 지표</p> */}
											<Chart />
										</div>
									</div>
									<div className="kpi-chart-item">
										<h3>일별 주가 차트</h3>
										<div className="kpi-chart-placeholder">
											{/* <p>최근 30일간의 일일 변동률 추이</p> */}
											<Chart />
										</div>
									</div>
									<div className="kpi-chart-item">
										<h3>거래량 추이</h3>
										<div className="kpi-chart-placeholder">
											{/* <p>거래량과 주가 변동의 상관관계</p> */}
											<Chart />
										</div>
									</div>
								</div>

								{/* 주식 정보 카드들 */}
								<div className="stock-cards">
									<div className="stock-card">
										<h3>현재가</h3>
										<p className="stock-value">₩50,000</p>
									</div>
									<div className="stock-card">
										<h3>전일 대비</h3>
										<p className="stock-value positive">+2.5%</p>
									</div>
									<div className="stock-card">
										<h3>거래량</h3>
										<p className="stock-value">1,234,567</p>
									</div>
									<div className="stock-card">
										<h3>시가총액</h3>
										<p className="stock-value">₩1.2조</p>
									</div>
								</div>
							</div>
						</div>

						{/* 재무제표 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>재무제표 분석</h2>
									<p>DART API 기반 종합 재무 분석</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="financial-section">
								{/* 주요 재무 지표 카드들 */}
								<div className="financial-cards">
									<div className="financial-card">
										<h3>매출액</h3>
										<p className="financial-value">₩1,000억</p>
										<span className="financial-change positive">+12.5%</span>
									</div>
									<div className="financial-card">
										<h3>영업이익</h3>
										<p className="financial-value">₩200억</p>
										<span className="financial-change positive">+8.3%</span>
									</div>
									<div className="financial-card">
										<h3>당기순이익</h3>
										<p className="financial-value">₩150억</p>
										<span className="financial-change positive">+15.2%</span>
									</div>
								</div>

								{/* 재무제표 차트 */}
								<div className="financial-chart-container">
									<h3>연도별 재무 성과</h3>
									<div className="financial-chart-placeholder">
										<p>매출액/영업이익/순이익 추이 차트</p>
									</div>
								</div>

								{/* 재무 비율 분석 */}
								<div className="financial-ratios">
									<div className="ratio-item">
										<span className="ratio-label">ROE</span>
										<span className="ratio-value positive">15.2%</span>
									</div>
									<div className="ratio-item">
										<span className="ratio-label">ROA</span>
										<span className="ratio-value positive">8.7%</span>
									</div>
									<div className="ratio-item">
										<span className="ratio-label">부채비율</span>
										<span className="ratio-value neutral">45.3%</span>
									</div>
									<div className="ratio-item">
										<span className="ratio-label">유동비율</span>
										<span className="ratio-value positive">1.8</span>
									</div>
								</div>
							</div>
						</div>

						<RightNav />
					</div>

					<div className="dashboard-grid2">
						{/* 뉴스 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>뉴스 기사</h2>
									<p>최신 관련 뉴스 및 시장 동향</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="news-section">
								<div className="news-list">
									<div className="news-item">
										<h4>삼성전자, 3분기 실적 발표</h4>
										<p>삼성전자가 3분기 실적을 발표하며...</p>
										<span className="news-date">2024-01-15</span>
									</div>
									<div className="news-item">
										<h4>반도체 업계 전망 긍정적</h4>
										<p>AI 반도체 수요 증가로 업계 전망이...</p>
										<span className="news-date">2024-01-14</span>
									</div>
									<div className="news-item">
										<h4>글로벌 경제 불확실성 지속</h4>
										<p>글로벌 경제 불확실성이 지속되며...</p>
										<span className="news-date">2024-01-13</span>
									</div>
								</div>
							</div>
						</div>

						{/* 감성 분석 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>뉴스 감성 분석</h2>
									<p>뉴스 기사의 감정 분석 결과</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="sentiment-section">
								<CircleGraph
									data={[
										{ name: '긍정', value: 45 },
										{ name: '부정', value: 30 },
										{ name: '중립', value: 25 },
									]}
									colors={['#34a853', '#ea4335', '#fbbc04']}
								/>
							</div>
						</div>

						{/* 워드 클라우드 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>핵심 키워드</h2>
									<p>뉴스에서 자주 언급되는 주요 키워드</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="wordcloud-section">
								<div className="wordcloud-container">
									<div className="wordcloud-placeholder">
										<div className="word-item large">AI</div>
										<div className="word-item medium">반도체</div>
										<div className="word-item small">투자</div>
										<div className="word-item medium">성장</div>
										<div className="word-item small">기술</div>
										<div className="word-item large">삼성전자</div>
										<div className="word-item small">시장</div>
										<div className="word-item medium">혁신</div>
									</div>
								</div>
							</div>
						</div>

						{/* AI 분석 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>AI 분석 및 예측</h2>
									<p>Gemini AI 기반 종합 분석 및 투자 권고</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="ai-analysis-section">
								<div className="ai-analysis-container">
									<div className="ai-analysis-content">
										<h3>종합 분석</h3>
										<p>
											현재 시장 상황을 종합적으로 분석한 결과, 삼성전자는 AI
											반도체 수요 증가와 글로벌 공급망 안정화로 인해
											중장기적으로 긍정적인 전망을 보이고 있습니다. 특히 메모리
											반도체 분야에서의 기술적 우위와 시스템 반도체 확장 전략이
											수익성 개선에 기여할 것으로 예상됩니다.
										</p>
									</div>
									<div className="ai-prediction">
										<h3>투자 권고사항</h3>
										<div className="prediction-item">
											<span className="prediction-label">단기 (1-3개월):</span>
											<span className="prediction-value positive">매수</span>
										</div>
										<div className="prediction-item">
											<span className="prediction-label">중기 (3-6개월):</span>
											<span className="prediction-value positive">
												강력 매수
											</span>
										</div>
										<div className="prediction-item">
											<span className="prediction-label">장기 (6개월+):</span>
											<span className="prediction-value negative">매도</span>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Footer/Dashboard 이동 버튼 */}
			{showFooterButton && (
				<button
					className={`footer-scroll-button ${buttonAnimation} ${
						isInFooter ? 'in-footer' : ''
					}`}
					onClick={handleButtonClick}
				>
					<i
						className={`fa-solid ${
							isInFooter ? 'fa-arrow-up' : 'fa-arrow-down'
						}`}
					></i>
					<span>{isInFooter ? 'Dashboard로 이동' : 'Footer로 이동'}</span>
				</button>
			)}

			{/* Footer */}
			{showFooter && (
				<div ref={footerRef}>
					<Footer />
				</div>
			)}
		</div>
	);
}

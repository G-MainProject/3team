import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import './AIInsights.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import MyWordCloud from '../../component/WordCloud/MyWordCloud';
import { getStockSummary } from '../../services/yahooFinanceApi';

const CircleGraphData = [
	{ name: '긍정', value: 45 },
	{ name: '부정', value: 30 },
	{ name: '중립', value: 25 },
];

const wordCloudData = [
	{ text: 'AI', value: 64 },
	{ text: '반도체', value: 45 },
	{ text: '투자', value: 80 },
	{ text: '성장', value: 70 },
	{ text: '기술', value: 55 },
	{ text: '삼성전자', value: 72 },
	{ text: '시장', value: 88 },
	{ text: '혁신', value: 40 },
];

export default function AIInsights({ selectedSymbol, onSymbolChange }) {
	const location = useLocation();
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	// URL state에서 전달받은 심볼 처리
	useEffect(() => {
		if (location.state?.selectedSymbol && onSymbolChange) {
			onSymbolChange(location.state.selectedSymbol);
		}
	}, [location.state?.selectedSymbol, onSymbolChange]);

	// TopNav용 주식 데이터 상태
	const [topNavStocks, setTopNavStocks] = useState([]);
	const [topNavLoading, setTopNavLoading] = useState(true);
	
	// 주요 주식 심볼 목록
	const stockSymbols = useMemo(() => [
		{ symbol: '005930', name: '삼성전자' },
		{ symbol: '000660', name: 'SK하이닉스' },
		{ symbol: '035420', name: 'NAVER' },
		{ symbol: '207940', name: '삼성바이오로직스' },
		{ symbol: '006400', name: '삼성SDI' }
	], []);


	// TopNav용 주식 데이터 로드
	useEffect(() => {
		const loadTopNavData = async () => {
			try {
				setTopNavLoading(true);
				
				// 모든 주식의 요약 정보를 병렬로 가져오기
				const stockDataPromises = stockSymbols.map(async (stock) => {
					try {
						const summary = await getStockSummary(stock.symbol);
						if (summary) {
							return {
								...stock,
								currentPrice: summary.currentPrice,
								change: summary.change,
								changePercent: summary.changePercent,
								volume: summary.volume,
								marketCap: summary.marketCap
							};
						} else {
							return {
								...stock,
								currentPrice: 50000,
								change: 0,
								changePercent: 0,
								volume: 0,
								marketCap: 0
							};
						}
					} catch (error) {
						console.error(`${stock.name} 데이터 가져오기 실패:`, error);
						return {
							...stock,
							currentPrice: 50000,
							change: 0,
							changePercent: 0,
							volume: 0,
							marketCap: 0
						};
					}
				});

				const allStockData = await Promise.all(stockDataPromises);
				
				// 변동폭 순으로 정렬 (절댓값 기준)
				const sortedStocks = allStockData.sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent));
				
				setTopNavStocks(sortedStocks);
				
				// 초기 로드 시 변동폭 순위 1위로 selectedSymbol 설정
				const topStock = sortedStocks[0];
				if (topStock && onSymbolChange) {
					onSymbolChange(topStock.symbol);
				}
				
				setTopNavLoading(false);
			} catch (error) {
				console.error('TopNav 주식 데이터 로드 실패:', error);
				setTopNavLoading(false);
			}
		};

		// 초기 로드
		loadTopNavData();
		
		// 1분마다 업데이트
		const interval = setInterval(loadTopNavData, 60000);
		return () => clearInterval(interval);
	}, [onSymbolChange, stockSymbols]);

	useEffect(() => {
		const dashboardMain = document.querySelector('.ai-insights-main');

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
			const dashboardMain = document.querySelector('.ai-insights-main');
			if (!dashboardMain) return;

			const scrollTop = dashboardMain.scrollTop;
			const scrollHeight = dashboardMain.scrollHeight;
			const clientHeight = dashboardMain.clientHeight;

			// 스크롤이 맨 아래에 도달했는지 확인 (반올림 오차 허용)
			const isAtBottom = Math.round(scrollTop + clientHeight) >= scrollHeight;

			// Footer 영역에 있을 때 위로 스크롤 제한
			if (isInFooter && e.deltaY < 0) {
				e.preventDefault();
				return;
			}

			// Dashboard에서 Footer로 가는 것을 제한
			if (!allowScrollToFooter && isAtBottom && e.deltaY > 0) {
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

				const dashboardMain = document.querySelector('.ai-insights-main');
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
		<div className="ai-insights-container">
			<div className="ai-insights-content">
				<LeftNav />
				<div className="ai-insights-main">
					<div className="ai-insights-grid">
						<TopNav 
							selectedSymbol={selectedSymbol}
							onSymbolChange={onSymbolChange}
							topNavStocks={topNavStocks}
							topNavLoading={topNavLoading}
							onStockSelect={onSymbolChange}
						/>

					</div>

					<div className="ai-insights-grid2">
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
									data={CircleGraphData}
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
										<MyWordCloud data={wordCloudData} />
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

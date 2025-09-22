import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import styles from './AIInsights.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import MyWordCloud from '../../component/WordCloud/MyWordCloud';
import { getStockSummary } from '../../services/yahooFinanceApi';

// 뉴스 감성 분석 데이터 (각 뉴스는 하나의 감성만 가짐)
const newsSentimentData = [
	'positive', 'positive', 'negative', 'positive', 'neutral', 'negative',
	'positive', 'negative', 'positive', 'neutral', 'positive', 'negative',
	'positive', 'neutral', 'neutral', 'positive', 'neutral', 'positive',
	'negative', 'positive', 'neutral', 'positive', 'negative', 'positive',
	'neutral', 'positive', 'negative', 'positive', 'neutral', 'positive',
	'negative', 'positive', 'neutral', 'positive', 'negative', 'positive',
	'neutral', 'positive', 'negative', 'positive'
];

// 뉴스 감성 분포 계산
const calculateSentimentRatio = (sentimentData) => {
	const total = sentimentData.length;
	const positiveCount = sentimentData.filter(sentiment => sentiment === 'positive').length;
	const negativeCount = sentimentData.filter(sentiment => sentiment === 'negative').length;
	const neutralCount = sentimentData.filter(sentiment => sentiment === 'neutral').length;
	
	return [
		{ name: '긍정', value: Math.round((positiveCount / total) * 100) },
		{ name: '부정', value: Math.round((negativeCount / total) * 100) },
		{ name: '중립', value: Math.round((neutralCount / total) * 100) },
	];
};

const CircleGraphData = calculateSentimentRatio(newsSentimentData);

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
		const dashboardMain = document.querySelector(`.${styles['ai-insights-main']}`);

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
			const dashboardMain = document.querySelector(`.${styles['ai-insights-main']}`);
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

				const dashboardMain = document.querySelector(`.${styles['ai-insights-main']}`);
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
		<div className={styles['ai-insights-container']}>
			<div className={styles['ai-insights-content']}>
				<LeftNav />
				<div className={styles['ai-insights-main']}>
					<div className={styles['ai-insights-grid']}>
						<TopNav 
							selectedSymbol={selectedSymbol}
							onSymbolChange={onSymbolChange}
							topNavStocks={topNavStocks}
							topNavLoading={topNavLoading}
							onStockSelect={onSymbolChange}
						/>

					</div>

					<div className={styles['ai-insights-grid2']}>
						{/* 뉴스 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>뉴스 기사</h2>
									<p>최신 관련 뉴스 및 시장 동향</p>
								</div>
							</div>
							<div className={styles['news-section']}>
								<div className={styles['news-list']}>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자, 3분기 실적 발표</h4>
											<p>삼성전자가 3분기 실적을 발표하며...</p>
											<span className={styles['news-date']}>2024-01-15</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 업계 전망 긍정적</h4>
											<p>AI 반도체 수요 증가로 업계 전망이...</p>
											<span className={styles['news-date']}>2024-01-14</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>글로벌 경제 불확실성 지속</h4>
											<p>글로벌 경제 불확실성이 지속되며...</p>
											<span className={styles['news-date']}>2024-01-13</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자 메모리 반도체 수요 급증</h4>
											<p>AI 서버 수요 증가로 메모리 반도체 시장이...</p>
											<span className={styles['news-date']}>2024-01-12</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 공급망 안정화 논의</h4>
											<p>정부와 업계가 반도체 공급망 안정화를 논의...</p>
											<span className={styles['news-date']}>2024-01-11</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>경기 둔화 우려 확산</h4>
											<p>글로벌 경기 둔화 우려가 반도체 업계에...</p>
											<span className={styles['news-date']}>2024-01-10</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자 HBM3 기술 선도</h4>
											<p>삼성전자가 HBM3 기술에서 경쟁 우위를...</p>
											<span className={styles['news-date']}>2024-01-09</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 장비 수출 제한 우려</h4>
											<p>미국의 반도체 장비 수출 제한이 업계에...</p>
											<span className={styles['news-date']}>2024-01-08</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>AI 반도체 투자 확대</h4>
											<p>삼성전자가 AI 반도체 분야 투자를 대폭...</p>
											<span className={styles['news-date']}>2024-01-07</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 시장 전망 보고서 발표</h4>
											<p>업계 단체가 2024년 반도체 시장 전망을...</p>
											<span className={styles['news-date']}>2024-01-06</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자 5G 기술 혁신</h4>
											<p>삼성전자가 5G 기술에서 새로운 돌파구를...</p>
											<span className={styles['news-date']}>2024-01-05</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 원자재 가격 상승</h4>
											<p>반도체 제조에 필요한 원자재 가격이 급등...</p>
											<span className={styles['news-date']}>2024-01-04</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>AI 칩셋 수주 증가</h4>
											<p>삼성전자가 AI 칩셋 분야에서 대규모 수주를...</p>
											<span className={styles['news-date']}>2024-01-03</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 업계 컨퍼런스 개최</h4>
											<p>글로벌 반도체 업계 컨퍼런스가 서울에서...</p>
											<span className={styles['news-date']}>2024-01-02</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>경쟁사 기술 추격</h4>
											<p>경쟁사들이 삼성전자 기술을 빠르게 따라잡고...</p>
											<span className={styles['news-date']}>2024-01-01</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>메모리 반도체 가격 상승</h4>
											<p>DDR5 메모리 반도체 가격이 급등하며...</p>
											<span className={styles['news-date']}>2023-12-31</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 설비 투자 계획</h4>
											<p>삼성전자가 내년 반도체 설비 투자 계획을...</p>
											<span className={styles['news-date']}>2023-12-30</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>자율주행 반도체 개발</h4>
											<p>삼성전자가 자율주행용 반도체 개발에 성공...</p>
											<span className={styles['news-date']}>2023-12-29</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>글로벌 경기 둔화 우려</h4>
											<p>글로벌 경기 둔화로 반도체 수요 감소 우려...</p>
											<span className={styles['news-date']}>2023-12-28</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>양자컴퓨팅 반도체 연구</h4>
											<p>삼성전자가 양자컴퓨팅 반도체 연구에 투자...</p>
											<span className={styles['news-date']}>2023-12-27</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 공급망 재편</h4>
											<p>글로벌 반도체 공급망이 재편되며...</p>
											<span className={styles['news-date']}>2023-12-26</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>차세대 메모리 기술</h4>
											<p>삼성전자가 차세대 메모리 기술 개발에 성공...</p>
											<span className={styles['news-date']}>2023-12-25</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>환경 규제 강화</h4>
											<p>반도체 업계에 환경 규제가 강화되며...</p>
											<span className={styles['news-date']}>2023-12-24</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>AI 서버용 반도체 수요 급증</h4>
											<p>AI 서버 수요 증가로 전용 반도체 수요가...</p>
											<span className={styles['news-date']}>2023-12-23</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 인력 부족</h4>
											<p>반도체 업계에서 고급 인력 부족 현상이...</p>
											<span className={styles['news-date']}>2023-12-22</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자 R&D 투자 확대</h4>
											<p>삼성전자가 R&D 투자를 대폭 확대한다고...</p>
											<span className={styles['news-date']}>2023-12-21</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>글로벌 경쟁 심화</h4>
											<p>중국 반도체 업체들의 급성장으로 경쟁이...</p>
											<span className={styles['news-date']}>2023-12-20</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>메모리 반도체 수출 증가</h4>
											<p>삼성전자 메모리 반도체 수출이 전년 대비...</p>
											<span className={styles['news-date']}>2023-12-19</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 공정 기술 발전</h4>
											<p>반도체 공정 기술이 지속적으로 발전하며...</p>
											<span className={styles['news-date']}>2023-12-18</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자 파트너십 확대</h4>
											<p>삼성전자가 글로벌 기업들과 파트너십을...</p>
											<span className={styles['news-date']}>2023-12-17</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 장비 수급 불안</h4>
											<p>반도체 제조 장비 수급이 불안정해지며...</p>
											<span className={styles['news-date']}>2023-12-16</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>AI 칩 설계 기술 혁신</h4>
											<p>삼성전자가 AI 칩 설계 기술에서 혁신을...</p>
											<span className={styles['news-date']}>2023-12-15</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 시장 규모 변화</h4>
											<p>글로벌 반도체 시장 규모가 예상과 다르게...</p>
											<span className={styles['news-date']}>2023-12-14</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>삼성전자 특허 출원 증가</h4>
											<p>삼성전자의 반도체 관련 특허 출원이 급증...</p>
											<span className={styles['news-date']}>2023-12-13</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['negative']}`}>
										<div className={styles['news-content']}>
											<h4>글로벌 공급망 불안정</h4>
											<p>글로벌 공급망 불안정으로 반도체 생산에...</p>
											<span className={styles['news-date']}>2023-12-12</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>부정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['positive']}`}>
										<div className={styles['news-content']}>
											<h4>메모리 반도체 기술 선도</h4>
											<p>삼성전자가 메모리 반도체 기술에서 세계 선도...</p>
											<span className={styles['news-date']}>2023-12-11</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>긍정</span>
											</div>
										</div>
									</div>
									<div className={`${styles['news-item']} ${styles['neutral']}`}>
										<div className={styles['news-content']}>
											<h4>반도체 업계 동향 분석</h4>
											<p>전문가들이 반도체 업계 동향을 분석한 결과...</p>
											<span className={styles['news-date']}>2023-12-10</span>
										</div>
										<div className={styles['sentiment-legend']}>
											<div className={styles['sentiment-item']}>
												<span className={styles['sentiment-label']}>중립</span>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>

						{/* 감성 분석 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>뉴스 감성 분석</h2>
									<p>뉴스 기사의 감정 분석 결과</p>
								</div>
							</div>
							<div className={styles['sentiment-section']}>
								<CircleGraph
									data={CircleGraphData}
									colors={['#34a853', '#ea4335', '#fbbc04']}
								/>
							</div>
						</div>

						{/* 워드 클라우드 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>핵심 키워드</h2>
									<p>뉴스에서 자주 언급되는 주요 키워드</p>
								</div>
							</div>
							<div className={styles['wordcloud-section']}>
								<div className={styles['wordcloud-container']}>
									<div className={styles['wordcloud-placeholder']}>
										<MyWordCloud data={wordCloudData} />
									</div>
								</div>
							</div>
						</div>

						{/* AI 분석 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>AI 분석 및 예측</h2>
									<p>Gemini AI 기반 종합 분석 및 투자 권고</p>
								</div>
							</div>
							<div className={styles['ai-analysis-section']}>
								<div className={styles['ai-analysis-container']}>
									<div className={styles['ai-analysis-content']}>
										<h3>종합 분석</h3>
										<p>
											현재 시장 상황을 종합적으로 분석한 결과, 삼성전자는 AI
											반도체 수요 증가와 글로벌 공급망 안정화로 인해
											중장기적으로 긍정적인 전망을 보이고 있습니다. 특히 메모리
											반도체 분야에서의 기술적 우위와 시스템 반도체 확장 전략이
											수익성 개선에 기여할 것으로 예상됩니다.
										</p>
									</div>
									<div className={styles['ai-prediction']}>
										<h3>투자 권고사항</h3>
										<div className={styles['prediction-item']}>
											<span className={styles['prediction-label']}>단기 (1-3개월):</span>
											<span className={`${styles['prediction-value']} ${styles['positive']}`}>매수</span>
										</div>
										<div className={styles['prediction-item']}>
											<span className={styles['prediction-label']}>중기 (3-6개월):</span>
											<span className={`${styles['prediction-value']} ${styles['positive']}`}>
												강력 매수
											</span>
										</div>
										<div className={styles['prediction-item']}>
											<span className={styles['prediction-label']}>장기 (6개월+):</span>
											<span className={`${styles['prediction-value']} ${styles['negative']}`}>매도</span>
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

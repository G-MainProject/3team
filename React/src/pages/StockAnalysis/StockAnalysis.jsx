import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import styles from './StockAnalysis.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import UnifiedStockChart from '../../component/UnifiedStockChart/UnifiedStockChart';
import Chart from '../../component/Chart/Chart';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import { getStockSummary } from '../../services/yahooFinanceApi';

const financialData = [
	{
		year: '2017',
		revenue: 2395800000000,
		operatingProfit: 536000000000,
		netProfit: 421900000000,
	},
	{
		year: '2018',
		revenue: 2437700000000,
		operatingProfit: 589000000000,
		netProfit: 443000000000,
	},
	{
		year: '2019',
		revenue: 2304000000000,
		operatingProfit: 277700000000,
		netProfit: 217400000000,
	},
	{
		year: '2020',
		revenue: 2368000000000,
		operatingProfit: 359900000000,
		netProfit: 264100000000,
	},
	{
		year: '2021',
		revenue: 2796000000000,
		operatingProfit: 512800000000,
		netProfit: 399100000000,
	},
	{
		year: '2022',
		revenue: 3022300000000,
		operatingProfit: 433800000000,
		netProfit: 556500000000,
	},
	{
		year: '2023',
		revenue: 2589400000000,
		operatingProfit: 65700000000,
		netProfit: 154900000000,
	},
];

const financialChartSeries = [
	{ key: 'revenue', name: '매출액', color: '#3b82f6' },
	{ key: 'operatingProfit', name: '영업이익', color: '#10b981' },
	{ key: 'netProfit', name: '순이익', color: '#ef4444' },
];

export default function StockAnalysis({ selectedSymbol, onSymbolChange }) {
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

	// TopNav 주식 데이터 로드
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
		const dashboardMain = document.querySelector(`.${styles['stock-analysis-main']}`);

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
			const dashboardMain = document.querySelector(`.${styles['stock-analysis-main']}`);
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

				const dashboardMain = document.querySelector(`.${styles['stock-analysis-main']}`);
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
		<div className={styles['stock-analysis-container']}>
			<div className={styles['stock-analysis-content']}>
				<LeftNav />
				<div className={styles['stock-analysis-main']}>
					<div className={styles['stock-analysis-grid']}>
						<TopNav 
							selectedSymbol={selectedSymbol}
							onSymbolChange={onSymbolChange}
							topNavStocks={topNavStocks}
							topNavLoading={topNavLoading}
							onStockSelect={onSymbolChange}
						/>
					</div>

					<div className={styles['stock-analysis-grid2']}>
						{/* 리포트 기준 주가 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>리포트 기준 주가</h2>
									<p>2024년 1월 15일 14:30 기준 주가 및 지표</p>
								</div>
								<button className={styles['detail-button']}>
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className={styles['stock-info-section']}>
								{/* 정적 차트 컨테이너 */}
								<div className={styles['unified-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>기준 시점 주가 및 거래량</h3>
										<div className={styles['analysis-timestamp']}>
											<span className={styles['timestamp-label']}>분석 시점:</span>
											<span className={styles['timestamp-value']}>2024-01-15 14:30</span>
										</div>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<UnifiedStockChart
											stockData={[
												{ time: '09:00', price: 49800, open: 50000, high: 50200, low: 49700, close: 49800 },
												{ time: '09:30', price: 50100, open: 49800, high: 50300, low: 49600, close: 50100 },
												{ time: '10:00', price: 50000, open: 50100, high: 50400, low: 49900, close: 50000 },
												{ time: '10:30', price: 50200, open: 50000, high: 50500, low: 49800, close: 50200 },
												{ time: '11:00', price: 50150, open: 50200, high: 50400, low: 50000, close: 50150 },
												{ time: '11:30', price: 50300, open: 50150, high: 50500, low: 50000, close: 50300 },
												{ time: '12:00', price: 50250, open: 50300, high: 50400, low: 50100, close: 50250 },
												{ time: '12:30', price: 50400, open: 50250, high: 50600, low: 50100, close: 50400 },
												{ time: '13:00', price: 50350, open: 50400, high: 50500, low: 50200, close: 50350 },
												{ time: '13:30', price: 50500, open: 50350, high: 50700, low: 50200, close: 50500 },
												{ time: '14:00', price: 50450, open: 50500, high: 50600, low: 50300, close: 50450 },
												{ time: '14:30', price: 50600, open: 50450, high: 50800, low: 50300, close: 50600 }
											]}
											volumeData={[
												{ time: '09:00', volume: 1200000 },
												{ time: '09:30', volume: 1500000 },
												{ time: '10:00', volume: 1800000 },
												{ time: '10:30', volume: 1600000 },
												{ time: '11:00', volume: 1400000 },
												{ time: '11:30', volume: 1700000 },
												{ time: '12:00', volume: 1900000 },
												{ time: '12:30', volume: 1300000 },
												{ time: '13:00', volume: 2100000 },
												{ time: '13:30', volume: 1800000 },
												{ time: '14:00', volume: 2000000 },
												{ time: '14:30', volume: 2500000 }
											]}
											simpleMode={false}
										/>
									</div>
								</div>

								{/* 분석 기준 시점 정보 카드들 */}
								<div className={styles['stock-cards']}>
									<div className={styles['stock-card']}>
										<h3>기준가</h3>
										<p className={styles['stock-value']}>
											₩50,600
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>전일 대비</h3>
										<p className={`${styles['stock-value']} ${styles['positive']}`}>
											+1.2%
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>거래량</h3>
										<p className={styles['stock-value']}>
											2,500,000
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>시가총액</h3>
										<p className={styles['stock-value']}>
											₩378.2조
										</p>
									</div>
								</div>
							</div>
						</div>

						{/* 재무제표 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>재무제표 분석</h2>
									<p>DART API 기반 종합 재무 분석</p>
								</div>
								<button className={styles['detail-button']}>
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className={styles['financial-section']}>
								{/* 주요 재무 지표 카드들 */}
								<div className={styles['financial-cards']}>
									<div className={styles['financial-card']}>
										<h3>매출액</h3>
										<p className={styles['financial-value']}>₩1,000억</p>
										<span className={`${styles['financial-change']} ${styles['positive']}`}>+12.5%</span>
									</div>
									<div className={styles['financial-card']}>
										<h3>영업이익</h3>
										<p className={styles['financial-value']}>₩200억</p>
										<span className={`${styles['financial-change']} ${styles['positive']}`}>+8.3%</span>
									</div>
									<div className={styles['financial-card']}>
										<h3>당기순이익</h3>
										<p className={styles['financial-value']}>₩150억</p>
										<span className={`${styles['financial-change']} ${styles['positive']}`}>+15.2%</span>
									</div>
								</div>

								{/* 재무제표 차트 */}
								<div className={styles['financial-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>연도별 재무 성과 (단위 : 10억원)</h3>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<Chart
											data={financialData}
											series={financialChartSeries}
											xAxisKey="year"
											yAxisUnit="원"
											xAxisUnit="년"
											yAxisFormatType="billions"
										/>
									</div>
								</div>

								{/* 재무 비율 분석 */}
								<div className={styles['financial-ratios']}>
									<div className={styles['ratio-item']}>
										<h4>부채비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>25.2%</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+1.2%p</span>
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>유동비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>1.8</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+0.1</span>
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>당좌비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>1.2</span>
											<span className={`${styles['ratio-change']} ${styles['negative']}`}>-0.1</span>
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>자기자본비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>79.8%</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+0.3%p</span>
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

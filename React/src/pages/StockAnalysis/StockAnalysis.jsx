import React, { useState, useEffect, useRef, useMemo } from 'react';
import styles from './StockAnalysis.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import UnifiedStockChart from '../../component/UnifiedStockChart/UnifiedStockChart';
import Chart from '../../component/Chart/Chart';
import { useStock } from '../../hooks/useStock';

// 더 현실적인 재무 데이터
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

// 정적 리포트 주가 데이터 (고정)
const generateRealisticStockData = () => {
	const times = ['09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30'];
	const volumes = [1200000, 1500000, 1800000, 1600000, 1400000, 1700000, 1900000, 1300000, 2100000, 1800000, 2000000, 2500000];
	
	// 고정된 가격 패턴 (약간의 상승 트렌드)
	const pricePattern = [49800, 50100, 50000, 50200, 50150, 50300, 50250, 50400, 50350, 50500, 50450, 50600];
	
	return times.map((time, index) => {
		const price = pricePattern[index];
		const open = index === 0 ? price : pricePattern[index - 1];
		const high = Math.round(price + 200 + (index * 10));
		const low = Math.round(price - 150 - (index * 5));
		const close = price;
		
		return {
			time,
			price,
			open,
			high,
			low,
			close,
			volume: volumes[index]
		};
	});
};

// 정적 리포트 기술적지표 데이터 (고정)
const generateTechnicalIndicators = () => {
	// 고정된 기술적지표 값들
	return {
		rsi: 65.2,
		macd: { macd: 150, signal: 140, histogram: 10 },
		bollinger: { upper: 51200, middle: 50000, lower: 48800 },
		obv: [1200000, 1350000, 1530000, 1690000, 1830000, 2000000, 2190000, 2320000, 2530000, 2710000, 2910000, 3160000]
	};
};

const financialChartSeries = [
	{ key: 'revenue', name: '매출액', color: '#3b82f6' },
	{ key: 'operatingProfit', name: '영업이익', color: '#10b981' },
	{ key: 'netProfit', name: '순이익', color: '#ef4444' },
];

export default function StockAnalysis() {
    const { selectedStock, loading: stockLoading } = useStock();
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	// 정적 리포트 데이터 (고정)
	const stockData = generateRealisticStockData();
	const technicalIndicators = generateTechnicalIndicators();

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

    if (stockLoading || !selectedStock) {
        return <div>Loading...</div>; // or a spinner component
    }

	return (
		<div className={styles['stock-analysis-container']}>
			<div className={styles['stock-analysis-content']}>
				<LeftNav />
				<div className={styles['stock-analysis-main']}>
					<div className={styles['stock-analysis-grid']}>
						<TopNav />
					</div>

					<div className={styles['stock-analysis-grid2']}>
						{/* 리포트 기준 주가 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>{selectedStock.stockName}/{selectedStock.stockCode}/KOSPI</h2>
									<p>{selectedStock.analysisDate} 기준 주가 및 지표</p>
								</div>
							</div>
							<div className={styles['stock-info-section']}>
								{/* 정적 차트 컨테이너 */}
								<div className={styles['unified-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>기준 시점 주가 및 거래량</h3>
										<div className={styles['analysis-timestamp']}>
											<span className={styles['timestamp-label']}>분석 시점:</span>
											<span className={styles['timestamp-value']}>{selectedStock.analysisDate}</span>
										</div>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<UnifiedStockChart
											stockData={stockData}
											volumeData={stockData.map(d => ({ time: d.time, volume: d.volume }))}
											simpleMode={false}
										/>
									</div>
								</div>

								{/* 분석 기준 시점 정보 카드들 */}
								<div className={styles['stock-cards']}>
									<div className={styles['stock-card']}>
										<h3>기준가</h3>
										<p className={styles['stock-value']}>
											₩{stockData[stockData.length - 1]?.price?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>전일 대비</h3>
										<p className={`${styles['stock-value']} ${styles['positive']}`}>
											{stockData.length > 1 ? 
												`${((stockData[stockData.length - 1].price - stockData[0].price) / stockData[0].price * 100).toFixed(1)}%` : 
												'+0.0%'
											}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>거래량</h3>
										<p className={styles['stock-value']}>
											{stockData[stockData.length - 1]?.volume?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>시가총액</h3>
										<p className={styles['stock-value']}>
											₩{((stockData[stockData.length - 1]?.price || 0) * 74700000000 / 1000000000000).toFixed(1)}조
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

								{/* 주요 재무 지표 (PER, PBR, ROE, ROA) */}
								<div className={styles['financial-ratios']}>
									<div className={styles['ratio-item']}>
										<h4>PER</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>12.5</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+0.8</span>
										</div>
										<p className={styles['ratio-description']}>주가수익비율</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>PBR</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>1.2</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+0.1</span>
										</div>
										<p className={styles['ratio-description']}>주가순자산비율</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>ROE</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>15.8%</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+2.1%p</span>
										</div>
										<p className={styles['ratio-description']}>자기자본이익률</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>ROA</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>8.4%</span>
											<span className={`${styles['ratio-change']} ${styles['positive']}`}>+1.2%p</span>
										</div>
										<p className={styles['ratio-description']}>총자산이익률</p>
									</div>
								</div>

								{/* 기존 재무 비율 분석 */}
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

						{/* 기술적지표 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>기술적지표 분석</h2>
									<p>RSI, OBV, MACD, 볼린저밴드 기반 기술적 분석</p>
								</div>
							</div>
							<div className={styles['technical-section']}>
								{/* 기술적지표 카드들 */}
								<div className={styles['technical-cards']}>
									<div className={styles['technical-card']}>
										<h3>RSI</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>{technicalIndicators.rsi}</p>
											<span className={`${styles['technical-signal']} ${
												technicalIndicators.rsi > 70 ? styles['negative'] : 
												technicalIndicators.rsi < 30 ? styles['positive'] : 
												styles['neutral']
											}`}>
												{technicalIndicators.rsi > 70 ? '과매수' : 
												 technicalIndicators.rsi < 30 ? '과매도' : '중립'}
											</span>
										</div>
										<p className={styles['technical-description']}>상대강도지수</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>OBV</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{technicalIndicators.obv[technicalIndicators.obv.length - 1] > 0 ? '+' : ''}
												{(technicalIndicators.obv[technicalIndicators.obv.length - 1] / 1000000).toFixed(1)}M
											</p>
											<span className={`${styles['technical-signal']} ${
												technicalIndicators.obv[technicalIndicators.obv.length - 1] > 
												technicalIndicators.obv[technicalIndicators.obv.length - 2] ? 
												styles['positive'] : styles['negative']
											}`}>
												{technicalIndicators.obv[technicalIndicators.obv.length - 1] > 
												 technicalIndicators.obv[technicalIndicators.obv.length - 2] ? '상승' : '하락'}
											</span>
										</div>
										<p className={styles['technical-description']}>거래량누적지표</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>MACD</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{technicalIndicators.macd.macd > 0 ? '+' : ''}{technicalIndicators.macd.macd}
											</p>
											<span className={`${styles['technical-signal']} ${
												technicalIndicators.macd.macd > technicalIndicators.macd.signal ? 
												styles['positive'] : styles['negative']
											}`}>
												{technicalIndicators.macd.macd > technicalIndicators.macd.signal ? '매수' : '매도'}
											</span>
										</div>
										<p className={styles['technical-description']}>이동평균수렴확산</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>BB</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{stockData[stockData.length - 1]?.price > technicalIndicators.bollinger.upper ? '상단' :
												 stockData[stockData.length - 1]?.price < technicalIndicators.bollinger.lower ? '하단' : '중간'}
											</p>
											<span className={`${styles['technical-signal']} ${
												stockData[stockData.length - 1]?.price > technicalIndicators.bollinger.upper ? styles['negative'] :
												stockData[stockData.length - 1]?.price < technicalIndicators.bollinger.lower ? styles['positive'] :
												styles['neutral']
											}`}>
												{stockData[stockData.length - 1]?.price > technicalIndicators.bollinger.upper ? '과매수' :
												 stockData[stockData.length - 1]?.price < technicalIndicators.bollinger.lower ? '과매도' : '중립'}
											</span>
										</div>
										<p className={styles['technical-description']}>볼린저밴드</p>
									</div>
								</div>

								{/* 기술적지표 차트들 - 첫 번째 행: RSI | OBV */}
								<div className={styles['technical-charts']}>
									{/* RSI 차트 */}
									<div className={styles['technical-chart-container']}>
										<div className={styles['chart-header']}>
											<h3>RSI (상대강도지수)</h3>
											<div className={styles['chart-period']}>14일</div>
										</div>
										<div className={styles['unified-chart-wrapper']}>
											<Chart
												data={stockData.map((d, index) => ({
													time: d.time,
													rsi: Math.max(0, Math.min(100, technicalIndicators.rsi + (index * 0.5) - 3))
												}))}
												series={[
													{ key: 'rsi', name: 'RSI', color: '#ff6b6b' }
												]}
												xAxisKey="time"
												yAxisUnit=""
												xAxisUnit=""
												yAxisFormatType="thousands"
											/>
										</div>
									</div>

									{/* OBV 차트 */}
									<div className={styles['technical-chart-container']}>
										<div className={styles['chart-header']}>
											<h3>OBV (거래량누적지표)</h3>
											<div className={styles['chart-period']}>누적</div>
										</div>
										<div className={styles['unified-chart-wrapper']}>
											<Chart
												data={stockData.map((d, index) => ({
													time: d.time,
													obv: technicalIndicators.obv[index] || 0
												}))}
												series={[
													{ key: 'obv', name: 'OBV', color: '#e91e63' }
												]}
												xAxisKey="time"
												yAxisUnit="주"
												xAxisUnit=""
												yAxisFormatType="thousands"
											/>
										</div>
									</div>
								</div>

								{/* 기술적지표 차트들 - 두 번째 행: MACD | 볼린저밴드 */}
								<div className={styles['technical-charts']}>
									{/* MACD 차트 */}
									<div className={styles['technical-chart-container']}>
										<div className={styles['chart-header']}>
											<h3>MACD (이동평균수렴확산)</h3>
											<div className={styles['chart-period']}>12,26,9</div>
										</div>
										<div className={styles['unified-chart-wrapper']}>
											<Chart
												data={stockData.map((d, index) => {
													const baseMacd = technicalIndicators.macd.macd;
													const baseSignal = technicalIndicators.macd.signal;
													const baseHistogram = technicalIndicators.macd.histogram;
													
													return {
														time: d.time,
														macd: Math.round(baseMacd + (index * 2) - 6),
														signal: Math.round(baseSignal + (index * 1.5) - 4.5),
														histogram: Math.round(baseHistogram + (index * 0.5) - 1.5)
													};
												})}
												series={[
													{ key: 'macd', name: 'MACD', color: '#4ecdc4' },
													{ key: 'signal', name: 'Signal', color: '#ff6b6b' },
													{ key: 'histogram', name: 'Histogram', color: '#45b7d1' }
												]}
												xAxisKey="time"
												yAxisUnit=""
												xAxisUnit=""
												yAxisFormatType="thousands"
											/>
										</div>
									</div>

									{/* 볼린저밴드 차트 */}
									<div className={styles['technical-chart-container']}>
										<div className={styles['chart-header']}>
											<h3>볼린저밴드</h3>
											<div className={styles['chart-period']}>20일, 2σ</div>
										</div>
										<div className={styles['unified-chart-wrapper']}>
											<Chart
												data={stockData.map((d, index) => ({
													time: d.time,
													price: d.price,
													upper: technicalIndicators.bollinger.upper + (index * 10),
													middle: technicalIndicators.bollinger.middle + (index * 5),
													lower: technicalIndicators.bollinger.lower + (index * 10)
												}))}
												series={[
													{ key: 'price', name: '주가', color: '#1976d2' },
													{ key: 'upper', name: '상단밴드', color: '#ff9800' },
													{ key: 'middle', name: '중간선', color: '#9c27b0' },
													{ key: 'lower', name: '하단밴드', color: '#4caf50' }
												]}
												xAxisKey="time"
												yAxisUnit="원"
												xAxisUnit=""
												yAxisFormatType="thousands"
											/>
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

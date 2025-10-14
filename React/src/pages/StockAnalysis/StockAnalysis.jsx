import React, { useState, useEffect, useRef, useMemo } from 'react';
import styles from './StockAnalysis.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import UnifiedStockChart from '../../component/UnifiedStockChart/UnifiedStockChart';
import Chart from '../../component/Chart/Chart';
import { useStock } from '../../hooks/useStock';
import stockAnalysisData from '../../../../data/outputs/top_mover_forecast.json';
import chartData from '../../../../data/outputs/chart_data.json';

const safeToFixed = (num, decimals = 1) => {
	const parsed = parseFloat(num);
	if (isNaN(parsed)) {
		return 'N/A';
	}
	return parsed.toFixed(decimals);
};

// Helper function to format currency
const formatCurrency = (value) => {
	if (value === null || isNaN(value)) return 'N/A';
	const val = value / 10000; // Convert to Trillions
	if (val >= 1) {
		return `${val.toFixed(1)}조`;
	}
	return `${value.toFixed(0)}억`;
};

export default function StockAnalysis() {
	const { selectedStock, loading: stockLoading } = useStock();
	const [daysToShow, setDaysToShow] = useState(30);
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	const stockInfo = useMemo(() => {
		if (!selectedStock) return null;
		return stockAnalysisData.entries.find(
			(stock) => stock.ticker === selectedStock.stockCode
		);
	}, [selectedStock]);

	const stockChartData = useMemo(() => {
		if (!selectedStock) return null;
		return chartData.items.find(
			(item) => item.meta.ticker === selectedStock.stockCode
		);
	}, [selectedStock]);

	const visibleChartData = useMemo(() => {
		if (!stockChartData) return [];
		return stockChartData.rows.slice(-daysToShow);
	}, [stockChartData, daysToShow]);

	const financialChartSeries = [
		{ key: 'revenue', name: '매출액', color: '#3b82f6' },
		{ key: 'operatingProfit', name: '영업이익', color: '#10b981' },
		{ key: 'netProfit', name: '순이익', color: '#ef4444' },
	];

	const financialChartData = useMemo(() => {
		if (!stockChartData || !stockChartData.annual_financials) return [];
		return stockChartData.annual_financials
			.map((row) => {
				if (!row) return null;
				let yearStr = null;
				if (row.date && typeof row.date === 'string') {
					yearStr = row.date.substring(0, 4);
				} else if (row.year !== undefined && row.year !== null) {
					yearStr = String(row.year);
				}
				if (!yearStr) return null;
				return {
					time: yearStr,
					revenue:
						typeof row.fund_revenue === 'number' ? row.fund_revenue / 10 : null,
					operatingProfit:
						typeof row.fund_operating_income === 'number'
							? row.fund_operating_income / 10
							: null,
					netProfit:
						typeof row.fund_net_income === 'number'
							? row.fund_net_income / 10
							: null,
				};
			})
			.filter(
				(r) =>
					r &&
					(r.revenue !== null ||
						r.operatingProfit !== null ||
						r.netProfit !== null)
			);
	}, [stockChartData]);

	const financialRatios = useMemo(() => {
		const initialRatios = {
			per: { value: 'N/A', change: 0 },
			pbr: { value: 'N/A', change: 0 },
			roe: { value: 'N/A', change: 0 },
			roa: { value: 'N/A', change: 0 },
			debt_ratio: { value: 'N/A', change: 0 },
			current_ratio: { value: 'N/A', change: 0 },
			quick_ratio: { value: 'N/A', change: 0 },
			equity_ratio: { value: 'N/A', change: 0 },
		};

		const calculateChange = (latestVal, previousVal) => {
			if (typeof latestVal === 'number' && typeof previousVal === 'number') {
				return latestVal - previousVal;
			}
			return 0;
		};

		// 1. Try to use annual financials data first
		if (
			stockChartData?.annual_financials &&
			stockChartData.annual_financials.length > 0
		) {
			const financials = stockChartData.annual_financials;
			const latest = financials[financials.length - 1];

			if (latest) {
				initialRatios.per.value = latest.per ?? 'N/A';
				initialRatios.pbr.value = latest.pbr ?? 'N/A';
				initialRatios.roe.value = latest.roe ?? 'N/A';
				initialRatios.roa.value = latest.roa ?? 'N/A';
				initialRatios.debt_ratio.value = latest.debt_ratio ?? 'N/A';
				initialRatios.current_ratio.value = latest.current_ratio ?? 'N/A';
				initialRatios.quick_ratio.value = latest.quick_ratio ?? 'N/A';
				initialRatios.equity_ratio.value = latest.equity_ratio ?? 'N/A';
			}

			if (financials.length >= 2) {
				const previous = financials[financials.length - 2];
				if (previous) {
					initialRatios.per.change = calculateChange(latest.per, previous.per);
					initialRatios.pbr.change = calculateChange(latest.pbr, previous.pbr);
					initialRatios.roe.change = calculateChange(latest.roe, previous.roe);
					initialRatios.roa.change = calculateChange(latest.roa, previous.roa);
					initialRatios.debt_ratio.change = calculateChange(
						latest.debt_ratio,
						previous.debt_ratio
					);
					initialRatios.current_ratio.change = calculateChange(
						latest.current_ratio,
						previous.current_ratio
					);
					initialRatios.quick_ratio.change = calculateChange(
						latest.quick_ratio,
						previous.quick_ratio
					);
					initialRatios.equity_ratio.change = calculateChange(
						latest.equity_ratio,
						previous.equity_ratio
					);
				}
			}
			return initialRatios;
		}

		// 2. Fallback to fundamentals from top_mover_forecast.json
		if (stockInfo?.fundamentals) {
			const { fundamentals } = stockInfo;
			initialRatios.per.value = fundamentals.per ?? 'N/A';
			initialRatios.pbr.value = fundamentals.pbr ?? 'N/A';
			initialRatios.roe.value = fundamentals.roe ?? 'N/A';
			initialRatios.roa.value = fundamentals.roa ?? 'N/A';
			initialRatios.debt_ratio.value = fundamentals.debt_ratio ?? 'N/A';
			initialRatios.current_ratio.value = fundamentals.current_ratio ?? 'N/A';
			initialRatios.quick_ratio.value = fundamentals.quick_ratio ?? 'N/A';
			initialRatios.equity_ratio.value = fundamentals.equity_ratio ?? 'N/A';
			// No change data available in this case
		}

		return initialRatios;
	}, [stockChartData, stockInfo]);

	useEffect(() => {
		const dashboardMain = document.querySelector(
			`.${styles['stock-analysis-main']}`
		);

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
			const dashboardMain = document.querySelector(
				`.${styles['stock-analysis-main']}`
			);
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

				const dashboardMain = document.querySelector(
					`.${styles['stock-analysis-main']}`
				);
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

	if (stockLoading || !stockInfo || !stockChartData) {
		return (
			<div className="flex items-center justify-center h-screen">
				<div className="flex flex-col items-center justify-center space-y-4">
					<div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin-slow"></div>
					<div className="text-lg font-semibold text-text-light dark:text-text-dark">
						Loading...
					</div>
				</div>
			</div>
		);
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
									<h2>
										{stockInfo.name}/{stockInfo.ticker}/KOSPI
									</h2>
									<p>{stockAnalysisData.date} 기준 주가 및 지표</p>
								</div>
							</div>
							<div className={styles['stock-info-section']}>
								{/* 정적 차트 컨테이너 */}
								<div className={styles['unified-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>기준 시점 주가 및 거래량</h3>
										{/* <div className={styles['chart-controls']}>
											<button
												onClick={() => setDaysToShow(30)}
												disabled={daysToShow === 30}
											>
												최근 30일
											</button>
											<button
												onClick={() => setDaysToShow((prev) => prev + 30)}
												disabled={daysToShow >= stockChartData.rows.length}
											>
												이전 30일 더 보기
											</button>
										</div> */}
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<UnifiedStockChart
											stockData={visibleChartData.map((d) => ({
												time: d.date,
												open: d.open,
												high: d.high,
												low: d.low,
												close: d.close,
												value: d.close,
											}))}
											volumeData={visibleChartData.map((d) => ({
												time: d.date,
												volume: d.volume,
											}))}
											simpleMode={false}
										/>
									</div>
								</div>

								{/* 분석 기준 시점 정보 카드들 */}
								<div className={styles['stock-cards']}>
									<div className={styles['stock-card']}>
										<h3>기준가</h3>
										<p className={styles['stock-value']}>
											₩{stockInfo?.current_price?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>전일 대비</h3>
										<p
											className={`${styles['stock-value']} ${
												(stockInfo?.change_pct || 0) > 0
													? styles['positive']
													: styles['negative']
											}`}
										>
											{(stockInfo?.change_pct || 0) > 0 ? '+' : ''}
											{safeToFixed(stockInfo?.change_pct, 1)}%
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>거래량</h3>
										<p className={styles['stock-value']}>
											{stockChartData?.rows
												?.slice(-1)[0]
												?.volume?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>시가총액</h3>
										<p className={styles['stock-value']}>
											₩
											{safeToFixed(
												(stockInfo?.fundamentals?.market_cap || 0) /
													1000000000000,
												1
											)}
											조
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
										<p className={styles['financial-value']}>
											{formatCurrency(stockInfo.fundamentals?.fund_revenue)}
										</p>
									</div>
									<div className={styles['financial-card']}>
										<h3>영업이익</h3>
										<p className={styles['financial-value']}>
											{formatCurrency(
												stockInfo.fundamentals?.fund_operating_income
											)}
										</p>
									</div>
									<div className={styles['financial-card']}>
										<h3>당기순이익</h3>
										<p className={styles['financial-value']}>
											{formatCurrency(stockInfo.fundamentals?.fund_net_income)}
										</p>
									</div>
								</div>

								{/* 재무제표 차트 */}
								<div className={styles['financial-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>연도별 재무 성과 (단위 : 10억원)</h3>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<Chart
											data={financialChartData}
											series={financialChartSeries}
											xAxisKey="time"
										/>
									</div>
								</div>

								{/* 주요 재무 지표 (PER, PBR, ROE, ROA) */}
								<div className={styles['financial-ratios']}>
									<div className={styles['ratio-item']}>
										<h4>PER</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.per.value, 1)}
											</span>
											<span
												className={`${styles['ratio-change']} ${
													financialRatios.per.change > 0
														? styles['positive']
														: styles['negative']
												}`}
											>
												{financialRatios.per.change !== 0
													? (financialRatios.per.change > 0 ? '+' : '') +
													  safeToFixed(financialRatios.per.change, 1)
													: ''}
											</span>
										</div>
										<p className={styles['ratio-description']}>주가수익비율</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>PBR</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.pbr.value, 1)}
											</span>
											<span
												className={`${styles['ratio-change']} ${
													financialRatios.pbr.change > 0
														? styles['positive']
														: styles['negative']
												}`}
											>
												{financialRatios.pbr.change !== 0
													? (financialRatios.pbr.change > 0 ? '+' : '') +
													  safeToFixed(financialRatios.pbr.change, 1)
													: ''}
											</span>
										</div>
										<p className={styles['ratio-description']}>
											주가순자산비율
										</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>ROE</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.roe.value * 100, 1)}%
											</span>
											<span
												className={`${styles['ratio-change']} ${
													financialRatios.roe.change > 0
														? styles['positive']
														: styles['negative']
												}`}
											>
												{financialRatios.roe.change !== 0
													? (financialRatios.roe.change > 0 ? '+' : '') +
													  safeToFixed(financialRatios.roe.change * 100, 1) +
													  '%p'
													: ''}
											</span>
										</div>
										<p className={styles['ratio-description']}>
											자기자본이익률
										</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>ROA</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.roa.value * 100, 1)}%
											</span>
											<span
												className={`${styles['ratio-change']} ${
													financialRatios.roa.change > 0
														? styles['positive']
														: styles['negative']
												}`}
											>
												{financialRatios.roa.change !== 0
													? (financialRatios.roa.change > 0 ? '+' : '') +
													  safeToFixed(financialRatios.roa.change * 100, 1) +
													  '%p'
													: ''}
											</span>
										</div>
										<p className={styles['ratio-description']}>총자산이익률</p>
									</div>
								</div>

								<div className={styles['financial-ratios']}>
									<div className={styles['ratio-item']}>
										<h4>부채비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.debt_ratio.value, 1)}%
											</span>
											{/* <span className={`${styles['ratio-change']} ${financialRatios.debt_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>
												{financialRatios.debt_ratio.change !== 0 ? (financialRatios.debt_ratio.change > 0 ? '+' : '') + safeToFixed(financialRatios.debt_ratio.change, 1) + '%p' : ''}
											</span> */}
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>유동비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.current_ratio.value, 1)}%
											</span>
											{/* <span className={`${styles['ratio-change']} ${financialRatios.current_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>
												{financialRatios.current_ratio.change !== 0 ? (financialRatios.current_ratio.change > 0 ? '+' : '') + safeToFixed(financialRatios.current_ratio.change, 1) + '%p' : ''}
											</span> */}
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>당좌비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.quick_ratio.value, 1)}%
											</span>
											{/* <span className={`${styles['ratio-change']} ${financialRatios.quick_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>
												{financialRatios.quick_ratio.change !== 0 ? (financialRatios.quick_ratio.change > 0 ? '+' : '') + safeToFixed(financialRatios.quick_ratio.change, 1) + '%p' : ''}
											</span> */}
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>자기자본비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>
												{safeToFixed(financialRatios.equity_ratio.value, 1)}%
											</span>
											{/* <span className={`${styles['ratio-change']} ${financialRatios.equity_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>
												{financialRatios.equity_ratio.change !== 0 ? (financialRatios.equity_ratio.change > 0 ? '+' : '') + safeToFixed(financialRatios.equity_ratio.change, 1) + '%p' : ''}
											</span> */}
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
											<p className={styles['technical-value']}>
												{safeToFixed(stockInfo?.indicators?.rsi, 1)}
											</p>
											<span
												className={`${styles['technical-signal']} ${
													(stockInfo?.indicators?.rsi || 0) > 70
														? styles['negative']
														: (stockInfo?.indicators?.rsi || 0) < 30
														? styles['positive']
														: styles['neutral']
												}`}
											>
												{(stockInfo?.indicators?.rsi || 0) > 70
													? '과매수'
													: (stockInfo?.indicators?.rsi || 0) < 30
													? '과매도'
													: '중립'}
											</span>
										</div>
										<p className={styles['technical-description']}>
											상대강도지수
										</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>OBV</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{(stockInfo?.indicators?.obv || 0) > 0 ? '+' : ''}
												{safeToFixed(
													(stockInfo?.indicators?.obv || 0) / 1000000,
													1
												)}
												M
											</p>
										</div>
										<p className={styles['technical-description']}>
											거래량누적지표
										</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>MACD</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{(stockInfo?.indicators?.macd || 0) > 0 ? '+' : ''}
												{safeToFixed(stockInfo?.indicators?.macd, 0)}
											</p>
											<span
												className={`${styles['technical-signal']} ${
													(stockInfo?.indicators?.macd || 0) >
													(stockInfo?.indicators?.macd_signal || 0)
														? styles['positive']
														: styles['negative']
												}`}
											>
												{(stockInfo?.indicators?.macd || 0) >
												(stockInfo?.indicators?.macd_signal || 0)
													? '매수'
													: '매도'}
											</span>
										</div>
										<p className={styles['technical-description']}>
											이동평균수렴확산
										</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>BB</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{(stockInfo?.current_price || 0) >
												(stockInfo?.indicators?.bb_upper || 0)
													? '상단'
													: (stockInfo?.current_price || 0) <
													  (stockInfo?.indicators?.bb_lower || 0)
													? '하단'
													: '중간'}
											</p>
											<span
												className={`${styles['technical-signal']} ${
													(stockInfo?.current_price || 0) >
													(stockInfo?.indicators?.bb_upper || 0)
														? styles['negative']
														: (stockInfo?.current_price || 0) <
														  (stockInfo?.indicators?.bb_lower || 0)
														? styles['positive']
														: styles['neutral']
												}`}
											>
												{(stockInfo?.current_price || 0) >
												(stockInfo?.indicators?.bb_upper || 0)
													? '과매수'
													: (stockInfo?.current_price || 0) <
													  (stockInfo?.indicators?.bb_lower || 0)
													? '과매도'
													: '중립'}
											</span>
										</div>
										<p className={styles['technical-description']}>
											볼린저밴드
										</p>
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
												data={visibleChartData.map((d) => ({
													time: d.date,
													rsi: d.rsi,
												}))}
												series={[{ key: 'rsi', name: 'RSI', color: '#ff6b6b' }]}
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
												data={visibleChartData.map((d) => ({
													time: d.date,
													obv: d.obv,
												}))}
												series={[{ key: 'obv', name: 'OBV', color: '#e91e63' }]}
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
												data={visibleChartData.map((d) => ({
													time: d.date,
													macd: d.macd,
													signal: d.macd_signal,
													histogram: d.macd_hist,
												}))}
												series={[
													{ key: 'macd', name: 'MACD', color: '#4ecdc4' },
													{ key: 'signal', name: 'Signal', color: '#ff6b6b' },
													{
														key: 'histogram',
														name: 'Histogram',
														color: '#45b7d1',
													},
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
												data={visibleChartData.map((d) => ({
													time: d.date,
													price: d.close,
													upper: d.bb_upper,
													middle: d.bb_mid,
													lower: d.bb_lower,
												}))}
												series={[
													{ key: 'price', name: '주가', color: '#1976d2' },
													{ key: 'upper', name: '상단밴드', color: '#ff9800' },
													{ key: 'middle', name: '중간선', color: '#9c27b0' },
													{ key: 'lower', name: '하단밴드', color: '#4caf50' },
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

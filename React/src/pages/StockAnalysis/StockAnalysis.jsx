import React, { useState, useEffect, useRef, useMemo } from 'react';
import styles from './StockAnalysis.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import UnifiedStockChart from '../../component/UnifiedStockChart/UnifiedStockChart';
import Chart from '../../component/Chart/Chart';
import { useStock } from '../../hooks/useStock';
import stockAnalysisData from '../../../../data/outputs/top_mover_forecast.json';

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

	const stockInfo = useMemo(() => {
		if (!selectedStock) return null;
		return stockAnalysisData.entries.find(
			(stock) => stock.ticker === selectedStock.stockCode
		);
	}, [selectedStock]);

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

    if (stockLoading || !stockInfo) {
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
									<h2>{stockInfo.name}/{stockInfo.ticker}/KOSPI</h2>
									<p>{stockAnalysisData.date} 기준 주가 및 지표</p>
								</div>
							</div>
							<div className={styles['stock-info-section']}>
								{/* 정적 차트 컨테이너 */}
								<div className={styles['unified-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>기준 시점 주가 및 거래량</h3>
										<div className={styles['analysis-timestamp']}>
											<span className={styles['timestamp-label']}>분석 시점:</span>
											<span className={styles['timestamp-value']}>{stockAnalysisData.date}</span>
										</div>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<UnifiedStockChart
											stockData={stockInfo.time_series.price_history}
											volumeData={stockInfo.time_series.price_history.map(d => ({ time: d.time, volume: d.volume }))}
											simpleMode={false}
										/>
									</div>
								</div>

								{/* 분석 기준 시점 정보 카드들 */}
								<div className={styles['stock-cards']}>
									<div className={styles['stock-card']}>
										<h3>기준가</h3>
										<p className={styles['stock-value']}>
											₩{stockInfo.current_price?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>전일 대비</h3>
										<p className={`${styles['stock-value']} ${styles['positive']}`}>
											{stockInfo.change_pct?.toFixed(1) || '0.0'}%
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>거래량</h3>
										<p className={styles['stock-value']}>
											{stockInfo.time_series.price_history[stockInfo.time_series.price_history.length - 1]?.volume?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>시가총액</h3>
										<p className={styles['stock-value']}>
											₩{(stockInfo.fundamentals.market_cap / 1000000000000).toFixed(1)}조
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
										<p className={styles['financial-value']}>₩{(stockInfo.financials.summary.revenue.value / 100000000).toFixed(0)}억</p>
										<span className={`${styles['financial-change']} ${stockInfo.financials.summary.revenue.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.summary.revenue.change > 0 ? '+' : ''}{stockInfo.financials.summary.revenue.change}%</span>
									</div>
									<div className={styles['financial-card']}>
										<h3>영업이익</h3>
										<p className={styles['financial-value']}>₩{(stockInfo.financials.summary.operating_profit.value / 100000000).toFixed(0)}억</p>
										<span className={`${styles['financial-change']} ${stockInfo.financials.summary.operating_profit.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.summary.operating_profit.change > 0 ? '+' : ''}{stockInfo.financials.summary.operating_profit.change}%</span>
									</div>
									<div className={styles['financial-card']}>
										<h3>당기순이익</h3>
										<p className={styles['financial-value']}>₩{(stockInfo.financials.summary.net_profit.value / 100000000).toFixed(0)}억</p>
										<span className={`${styles['financial-change']} ${stockInfo.financials.summary.net_profit.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.summary.net_profit.change > 0 ? '+' : ''}{stockInfo.financials.summary.net_profit.change}%</span>
									</div>
								</div>

								{/* 재무제표 차트 */}
								<div className={styles['financial-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>연도별 재무 성과 (단위 : 10억원)</h3>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<Chart
											data={stockInfo.financials.yearly}
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
											<span className={styles['ratio-number']}>{stockInfo.fundamentals.per.toFixed(1)}</span>
										</div>
										<p className={styles['ratio-description']}>주가수익비율</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>PBR</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{stockInfo.fundamentals.pbr.toFixed(1)}</span>
										</div>
										<p className={styles['ratio-description']}>주가순자산비율</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>ROE</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{(stockInfo.fundamentals.roe * 100).toFixed(1)}%</span>
										</div>
										<p className={styles['ratio-description']}>자기자본이익률</p>
									</div>
									<div className={styles['ratio-item']}>
										<h4>ROA</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{stockInfo.fundamentals.roa.toFixed(1)}%</span>
										</div>
										<p className={styles['ratio-description']}>총자산이익률</p>
									</div>
								</div>

								{/* 기존 재무 비율 분석 */}
								<div className={styles['financial-ratios']}>
									<div className={styles['ratio-item']}>
										<h4>부채비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{stockInfo.financials.ratios.debt_ratio.value}%</span>
											<span className={`${styles['ratio-change']} ${stockInfo.financials.ratios.debt_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.ratios.debt_ratio.change > 0 ? '+' : ''}{stockInfo.financials.ratios.debt_ratio.change}%p</span>
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>유동비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{stockInfo.financials.ratios.current_ratio.value}</span>
											<span className={`${styles['ratio-change']} ${stockInfo.financials.ratios.current_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.ratios.current_ratio.change > 0 ? '+' : ''}{stockInfo.financials.ratios.current_ratio.change}</span>
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>당좌비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{stockInfo.financials.ratios.quick_ratio.value}</span>
											<span className={`${styles['ratio-change']} ${stockInfo.financials.ratios.quick_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.ratios.quick_ratio.change > 0 ? '+' : ''}{stockInfo.financials.ratios.quick_ratio.change}</span>
										</div>
									</div>
									<div className={styles['ratio-item']}>
										<h4>자기자본비율</h4>
										<div className={styles['ratio-value']}>
											<span className={styles['ratio-number']}>{stockInfo.financials.ratios.equity_ratio.value}%</span>
											<span className={`${styles['ratio-change']} ${stockInfo.financials.ratios.equity_ratio.change > 0 ? styles['positive'] : styles['negative']}`}>{stockInfo.financials.ratios.equity_ratio.change > 0 ? '+' : ''}{stockInfo.financials.ratios.equity_ratio.change}%p</span>
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
											<p className={styles['technical-value']}>{stockInfo.indicators.rsi.toFixed(1)}</p>
											<span className={`${styles['technical-signal']} ${
												stockInfo.indicators.rsi > 70 ? styles['negative'] : 
												stockInfo.indicators.rsi < 30 ? styles['positive'] : 
												styles['neutral']
											}`}>
												{stockInfo.indicators.rsi > 70 ? '과매수' : 
												 stockInfo.indicators.rsi < 30 ? '과매도' : '중립'}
											</span>
										</div>
										<p className={styles['technical-description']}>상대강도지수</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>OBV</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{stockInfo.indicators.obv > 0 ? '+' : ''}
												{(stockInfo.indicators.obv / 1000000).toFixed(1)}M
											</p>
										</div>
										<p className={styles['technical-description']}>거래량누적지표</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>MACD</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{stockInfo.indicators.macd > 0 ? '+' : ''}{stockInfo.indicators.macd.toFixed(0)}
											</p>
											<span className={`${styles['technical-signal']} ${
												stockInfo.indicators.macd > stockInfo.indicators.macd_signal ? 
												styles['positive'] : styles['negative']
											}`}>
												{stockInfo.indicators.macd > stockInfo.indicators.macd_signal ? '매수' : '매도'}
											</span>
										</div>
										<p className={styles['technical-description']}>이동평균수렴확산</p>
									</div>
									<div className={styles['technical-card']}>
										<h3>BB</h3>
										<div className={styles['technical-value-container']}>
											<p className={styles['technical-value']}>
												{stockInfo.current_price > stockInfo.indicators.bb_upper ? '상단' :
												 stockInfo.current_price < stockInfo.indicators.bb_lower ? '하단' : '중간'}
											</p>
											<span className={`${styles['technical-signal']} ${
												stockInfo.current_price > stockInfo.indicators.bb_upper ? styles['negative'] :
												stockInfo.current_price < stockInfo.indicators.bb_lower ? styles['positive'] :
												styles['neutral']
											}`}>
												{stockInfo.current_price > stockInfo.indicators.bb_upper ? '과매수' :
												 stockInfo.current_price < stockInfo.indicators.bb_lower ? '과매도' : '중립'}
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
												data={stockInfo.time_series.price_history.map((d, index) => ({
													time: d.time,
													rsi: stockInfo.time_series.indicators_history.rsi[index]
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
												data={stockInfo.time_series.price_history.map((d, index) => ({
													time: d.time,
													obv: stockInfo.time_series.indicators_history.obv[index]
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
												data={stockInfo.time_series.price_history.map((d, index) => ({
													time: d.time,
													macd: stockInfo.time_series.indicators_history.macd[index],
													signal: stockInfo.time_series.indicators_history.signal[index],
													histogram: stockInfo.time_series.indicators_history.histogram[index]
												}))}
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
												data={stockInfo.time_series.price_history.map((d, index) => ({
													time: d.time,
													price: d.price,
													upper: stockInfo.time_series.indicators_history.bollinger_upper[index],
													middle: stockInfo.time_series.indicators_history.bollinger_middle[index],
													lower: stockInfo.time_series.indicators_history.bollinger_lower[index]
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

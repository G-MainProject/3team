import React, {
	useState,
	useEffect,
	useRef,
	useMemo,
	useCallback,
} from 'react';
import styles from './Dashboard.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Sns from '../../component/Sns/Sns';
import Footer from '../../component/Footer/Footer';
import Chart from '../../component/Chart/Chart';
import UnifiedStockChart from '../../component/UnifiedStockChart/UnifiedStockChart';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import MyWordCloud from '../../component/WordCloud/MyWordCloud';
import { useStock } from '../../hooks/useStock';
import { useRealtimeStockData } from '../../hooks/useRealtimeStockData.jsx';
import stockAnalysisData from '../../../../data/outputs/top_mover_forecast.json';




const financialChartSeries = [
	{ key: 'revenue', name: '매출액', color: '#3b82f6' },
	{ key: 'operatingProfit', name: '영업이익', color: '#10b981' },
	{ key: 'netProfit', name: '순이익', color: '#ef4444' },
];

export default function Dashboard() {
	const {
		selectedStock,
		loading: stockLoading,
	} = useStock();

	// 통합된 실시간 주식 데이터 훅 사용 (WebSocket + 폴링)
	const currentSymbol = selectedStock?.stockCode || '005930';
	
	const {
		stockData: realtimeStockData,
		volumeData: realtimeVolumeData,
		summaryData: realtimeSummaryData,
		loading: realtimeLoading,
		error: realtimeError,
		lastUpdate: realtimeLastUpdate,
		lastTradeTime: realtimeLastTradeTime,
		isRefreshing: realtimeIsRefreshing,
		refreshData: refreshRealtimeData,
	} = useRealtimeStockData(currentSymbol);

	// 장마감 상태 관리
	const [isMarketClosed, setIsMarketClosed] = useState(false);

	// 장마감 상태 확인 함수
	const checkMarketStatus = useCallback(() => {
		const now = new Date();
		const hour = now.getHours();
		const minute = now.getMinutes();
		const day = now.getDay(); // 0=일요일, 6=토요일
		
		// 주말이면 장마감
		if (day === 0 || day === 6) {
			setIsMarketClosed(true);
			return;
		}
		
		// 실제 거래 마지막 시간을 기준으로 판단
		if (realtimeLastTradeTime) {
			const lastTradeHour = realtimeLastTradeTime.getHours();
			const lastTradeMinute = realtimeLastTradeTime.getMinutes();
			
			// 마지막 거래가 15:30 이후이거나, 현재 시간이 15:30 이후면 장마감
			const isDataAfterClose = lastTradeHour > 15 || (lastTradeHour === 15 && lastTradeMinute >= 30);
			const isCurrentAfterClose = hour > 15 || (hour === 15 && minute >= 30);
			
			setIsMarketClosed(isDataAfterClose || isCurrentAfterClose);
		} else {
			// 데이터가 없으면 현재 시간 기준으로 판단
			const isClosed = hour > 15 || (hour === 15 && minute >= 30);
			setIsMarketClosed(isClosed);
		}
	}, [realtimeLastTradeTime]);

	// WebSocket 데이터 수신과 갱신 중 상태 동기화는 useRealtimeStockData 훅에서 처리

	// 1분마다 장마감 상태 확인
	useEffect(() => {
		checkMarketStatus(); // 초기 확인
		
		const interval = setInterval(() => {
			checkMarketStatus(); // 장마감 상태 재확인
		}, 60000); // 1분마다

		return () => {
			clearInterval(interval);
		};
	}, [checkMarketStatus]);

	// 에러 발생 시에만 로그 출력
	useEffect(() => {
		if (realtimeError) {
			console.error('[Dashboard] 실시간 데이터 에러:', realtimeError);
		}
	}, [realtimeError]);


	const stockInfo = useMemo(() => {
		if (!selectedStock) return null;
		return stockAnalysisData.entries.find(
			(stock) => stock.ticker === selectedStock.stockCode
		);
	}, [selectedStock]);

	const dashboardNews = useMemo(() => {
		if (!selectedStock || !selectedStock.relatedNews) {
			return [];
		}

		const newsWithSentiment = selectedStock.relatedNews.map((n) => ({
			...n,
			sentiment: n.sentimentClass,
		}));

		// Sort by date descending
		const sortedNews = [...newsWithSentiment].sort(
			(a, b) => new Date(b.date) - new Date(a.date)
		);

		const uniqueNewsByDate = [];
		const dates = new Set();

		for (const news of sortedNews) {
			if (!dates.has(news.date)) {
				uniqueNewsByDate.push(news);
				dates.add(news.date);
			}
		}

		// If we have 3 or more unique-date news, take the first 3.
		if (uniqueNewsByDate.length >= 3) {
			return uniqueNewsByDate.slice(0, 3);
		}

		// Otherwise, just return the top 3 most recent news regardless of date.
		return sortedNews.slice(0, 3);
	}, [selectedStock]);

	// 전체 뉴스 데이터를 기반으로 한 감성 분석 데이터 (항상 전체 비율 표시)
	const CircleGraphData = useMemo(() => {
		if (
			!selectedStock ||
			!selectedStock.sentimentAnalysis ||
			!selectedStock.sentimentAnalysis.sentimentDistribution
		) {
			return [
				{ name: '긍정', value: 0 },
				{ name: '부정', value: 0 },
				{ name: '중립', value: 0 },
			];
		}
		const distribution = selectedStock.sentimentAnalysis.sentimentDistribution;
		const total =
			(distribution.positive || 0) +
			(distribution.negative || 0) +
			(distribution.neutral || 0);

		if (total === 0) {
			return [
				{ name: '긍정', value: 0 },
				{ name: '부정', value: 0 },
				{ name: '중립', value: 0 },
			];
		}

		return [
			{
				name: '긍정',
				value: Math.round(((distribution.positive || 0) / total) * 100),
			},
			{
				name: '부정',
				value: Math.round(((distribution.negative || 0) / total) * 100),
			},
			{
				name: '중립',
				value: Math.round(((distribution.neutral || 0) / total) * 100),
			},
		];
	}, [selectedStock]);

	// 워드 클라우드 데이터
	const wordCloudData = useMemo(() => {
		if (
			!selectedStock ||
			!selectedStock.keywordAnalysis ||
			!selectedStock.keywordAnalysis.wordCloud
		) {
			return [];
		}
		return Object.entries(selectedStock.keywordAnalysis.wordCloud).map(
			([text, value]) => ({ text, value })
		);
	}, [selectedStock]);
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	// 차트 간격 설정 상태
	const [chartInterval, setChartInterval] = useState('1m'); // 1m, 5m, 15m, 30m, 1h

	// 차트 간격 변경 핸들러 (성능 최적화)
	const handleIntervalChange = useCallback((e) => {
		setChartInterval(e.target.value);
	}, []);

	// 실시간 데이터를 차트 형식으로 변환 (성능 최적화)
	const stockData = useMemo(() => {
		if (!realtimeStockData || realtimeStockData.length === 0) return [];
		
		return realtimeStockData.map((item, index) => ({
			time: item.time || new Date(Date.now() - (realtimeStockData.length - index - 1) * 60000).toLocaleTimeString('ko-KR', {
				hour: '2-digit',
				minute: '2-digit',
				hour12: false,
			}),
			price: item.price || 0,
			open: item.open || item.price || 0,
			high: item.high || item.price || 0,
			low: item.low || item.price || 0,
			close: item.close || item.price || 0,
		}));
	}, [realtimeStockData]);

	const volumeData = useMemo(() => {
		if (!realtimeVolumeData || realtimeVolumeData.length === 0) return [];
		
		return realtimeVolumeData.map((item, index) => ({
			time: item.time || new Date(Date.now() - (realtimeVolumeData.length - index - 1) * 60000).toLocaleTimeString('ko-KR', {
				hour: '2-digit',
				minute: '2-digit',
				hour12: false,
			}),
			volume: item.volume || 0,
		}));
	}, [realtimeVolumeData]);

	// 주식 요약 정보 (통합된 실시간 데이터 우선 사용)
	const stockSummary = useMemo(() => {
		// 실시간 요약 데이터가 있으면 우선 사용
		if (realtimeSummaryData) {
			return {
				currentPrice: realtimeSummaryData.currentPrice || 0,
				change: realtimeSummaryData.change || 0,
				changePercent: realtimeSummaryData.changePercent || 0,
				volume: realtimeSummaryData.volume || 0,
				marketCap: realtimeSummaryData.marketCap || 0,
			};
		}

		// 실시간 요약 데이터가 없으면 실시간 차트 데이터에서 계산
		if (realtimeStockData && realtimeStockData.length > 0) {
			const latestData = realtimeStockData[realtimeStockData.length - 1];
			const previousData = realtimeStockData[realtimeStockData.length - 2] || latestData;
			
			const currentPrice = latestData.price || 0;
			const previousPrice = previousData.price || currentPrice;
			const change = currentPrice - previousPrice;
			const changePercent = previousPrice > 0 ? (change / previousPrice) * 100 : 0;

			// 거래량은 별도 실시간 데이터에서 가져오기
			let volume = 0;
			if (realtimeVolumeData && realtimeVolumeData.length > 0) {
				const latestVolume = realtimeVolumeData[realtimeVolumeData.length - 1];
				volume = latestVolume.volume || 0;
			}

			return {
				currentPrice,
				change,
				changePercent: Math.round(changePercent * 100) / 100,
				volume,
				marketCap: selectedStock?.marketCap || 0,
			};
		}

		// 모든 실시간 데이터가 없으면 selectedStock에서 가져오기
		if (selectedStock) {
			return {
			currentPrice: selectedStock.currentPrice || 0,
			change: selectedStock.change || 0,
			changePercent: selectedStock.changePercent || 0,
			volume: selectedStock.volume || 0,
			marketCap: selectedStock.marketCap || 0,
		};
		}

		// 기본값
		return {
			currentPrice: 0,
			change: 0,
			changePercent: 0,
			volume: 0,
			marketCap: 0,
		};
	}, [realtimeSummaryData, realtimeStockData, realtimeVolumeData, selectedStock]);

	// 스크롤 핸들러 최적화 (throttling 적용)
	const handleScroll = useCallback(() => {
		const dashboardMain = document.querySelector(`.${styles['dashboard-main']}`);
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
	}, []);

	useEffect(() => {
		const dashboardMain = document.querySelector(`.${styles['dashboard-main']}`);
		if (dashboardMain) {
			// throttling 적용 (100ms마다 실행)
			let timeoutId;
			const throttledHandleScroll = () => {
				clearTimeout(timeoutId);
				timeoutId = setTimeout(handleScroll, 100);
			};

			dashboardMain.addEventListener('scroll', throttledHandleScroll);
			return () => {
				dashboardMain.removeEventListener('scroll', throttledHandleScroll);
				clearTimeout(timeoutId);
			};
		}
	}, [handleScroll]);

	// 전체 페이지 스크롤 제한 (최적화)
	const handlePageScroll = useCallback((e) => {
		const dashboardMain = document.querySelector(`.${styles['dashboard-main']}`);
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
	}, [allowScrollToFooter, isInFooter]);

	useEffect(() => {
		window.addEventListener('wheel', handlePageScroll, { passive: false });
		return () => window.removeEventListener('wheel', handlePageScroll);
	}, [handlePageScroll]);

	const handleButtonClick = useCallback(() => {
		if (isInFooter) {
			// Footer에서 Dashboard로 이동 - fadeOut 애니메이션 적용
			setButtonAnimation('fade-out');

			// 애니메이션 완료 후 상태 변경
			setTimeout(() => {
				setAllowScrollToFooter(false);
				setIsInFooter(false);

				const dashboardMain = document.querySelector(`.${styles['dashboard-main']}`);
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
	}, [isInFooter]);

	if (stockLoading || !selectedStock) {
		return (
			<div className="flex items-center justify-center h-screen">
				<div className="flex flex-col items-center justify-center space-y-4">
					<div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin-slow"></div>
					<div className="text-lg font-semibold text-text-light dark:text-text-dark">Loading...</div>
				</div>
			</div>
		);
	}

	return (
		<div className={styles['dashboard-container']}>
			<div className={styles['dashboard-content']}>
				<LeftNav />
				<div className={styles['dashboard-main']}>
					<div className={styles['dashboard-grid']}>
						<TopNav />

						{/* 주식 정보 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>
										{selectedStock.stockName}/{selectedStock.stockCode}/KOSPI
									</h2>
									<p>실시간 주가 및 주요 지표</p>
								</div>
								<div className={styles['section-action']}>
									{isMarketClosed && (
										<div className={styles['market-closed-badge']}>
											<i className="fas fa-clock"></i>
											<span>
												장마감
												{realtimeLastTradeTime && (
													<span className={styles['last-trade-time']}>
														(마지막: {realtimeLastTradeTime.toLocaleTimeString('ko-KR', {
															hour: '2-digit',
															minute: '2-digit',
															hour12: false
														})})
													</span>
												)}
											</span>
										</div>
									)}
					{!isMarketClosed && (
						<div className={styles['last-updated']}>
							<i className="fa-solid fa-clock"></i>
							<span>
								마지막 업데이트: {realtimeLastUpdate ? realtimeLastUpdate.toLocaleString('ko-KR', {
									year: 'numeric',
									month: '2-digit',
									day: '2-digit',
									hour: '2-digit',
									minute: '2-digit',
									second: '2-digit',
									hour12: false
								}) : '데이터 없음'}
							</span>
							{realtimeIsRefreshing && (
								<span className={styles['refreshing-indicator']}>
									<i className="fas fa-sync-alt fa-spin"></i>
									갱신 중...
								</span>
							)}
							{/* WebSocket 연결 상태 표시 */}
						</div>
					)}
								</div>
							</div>
							<div className={styles['stock-info-section']}>
								{/* 통합 주식 차트 */}
								<div className={styles['unified-chart-container']}>
									<div className={styles['chart-header']}>
										<h3>실시간 주가 및 거래량</h3>
										<div className={styles['chart-interval-selector']}>
											<label htmlFor="interval-select">차트 간격:</label>
											<select
												id="interval-select"
												value={chartInterval}
												onChange={handleIntervalChange}
												className={styles['interval-select']}
											>
												<option value="1m">1분</option>
												<option value="5m">5분</option>
												<option value="15m">15분</option>
												<option value="30m">30분</option>
												<option value="1h">1시간</option>
											</select>
										</div>
									</div>
									{realtimeLoading || realtimeIsRefreshing ? (
										<div className={styles['chart-loading']}>
											<i className="fas fa-sync-alt fa-spin"></i>
											{realtimeLoading ? '데이터를 불러오는 중...' : '데이터를 갱신하는 중...'}
										</div>
									) : realtimeError ? (
										<div className={styles['chart-error']}>
											<i className="fas fa-exclamation-triangle"></i>
											<p>실시간 데이터를 불러올 수 없습니다</p>
											<p className={styles['error-detail']}>
												{realtimeError.includes('SERVICE_UNAVAILABLE') 
													? '서버가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.'
													: realtimeError
												}
											</p>
											<button 
												onClick={refreshRealtimeData}
												className={styles['retry-button']}
											>
												다시 시도
											</button>
										</div>
									) : stockData.length === 0 ? (
										<div className={styles['chart-error']}>
											<i className="fas fa-chart-line"></i>
											<p>차트 데이터가 없습니다</p>
											<p className={styles['error-detail']}>
												주식 데이터를 가져올 수 없습니다
											</p>
											<button 
												onClick={refreshRealtimeData}
												className={styles['retry-button']}
											>
												다시 시도
											</button>
										</div>
									) : (
										<div className={styles['unified-chart-wrapper']}>
											<UnifiedStockChart
												stockData={stockData}
												volumeData={volumeData}
												simpleMode={false}
											/>
										</div>
									)}
								</div>

								{/* 주식 정보 카드들 */}
								<div className={styles['stock-cards']}>
									<div className={styles['stock-card']}>
										<h3>현재가</h3>
										<p className={styles['stock-value']}>
											₩{stockSummary?.currentPrice?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>전일 대비</h3>
										<p
											className={`${styles['stock-value']} ${
												(stockSummary?.changePercent || 0) >= 0
													? styles['positive']
													: styles['negative']
											}`}
										>
											{(stockSummary?.changePercent || 0) >= 0 ? '+' : ''}
											{(stockSummary?.changePercent || 0).toFixed(2)}%
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>거래량</h3>
										<p className={styles['stock-value']}>
											{(stockSummary?.volume || 0).toLocaleString()}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>시가총액</h3>
										<p className={styles['stock-value']}>
											₩
											{((stockSummary?.marketCap || 0) / 1000000000000).toFixed(
												1
											)}
											조
										</p>
									</div>
								</div>
							</div>
						</div>

						<Sns selectedSymbol={selectedStock.stockCode} />
					</div>

					<div className={styles['dashboard-grid2']}>
						{/* 리포트 기준 주가 섹션 - stockInfo가 있을 때만 표시 */}
						{stockInfo && (
							<div className={styles['section-container']}>
								<div className={styles['section-label']}>
									<div className={styles['section-title']}>
										<h2>{stockInfo.name}/{stockInfo.ticker}/KOSPI</h2>
										<p>{stockAnalysisData.date} 기준 주가 및 지표</p>
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
										<p className={`${styles['stock-value']} ${stockInfo.change_pct > 0 ? styles['positive'] : styles['negative']}`}>
											{stockInfo.change_pct > 0 ? '+' : ''}{stockInfo.change_pct?.toFixed(1) || '0.0'}%
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
						)}

						{/* 재무제표 섹션 - stockInfo가 있을 때만 표시 */}
						{stockInfo && (
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
							</div>
						</div>
						)}

						{/* 뉴스 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>뉴스 기사</h2>
									<p>최신 관련 뉴스 및 시장 동향</p>
								</div>
								<button className={styles['detail-button']}>
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className={styles['news-section']}>
								<div className={styles['news-list']}>
									{dashboardNews.map((news, index) => (
										<div
											key={index}
											className={`${styles['news-item']} ${
												styles[news.sentiment]
											}`}
										>
											<div className={styles['news-content']}>
												<h4>{news.title}</h4>
												<p>{news.content}</p>
												<span className={styles['news-date']}>{news.date}</span>
											</div>
											<div className={styles['sentiment-legend']}>
												<div className={styles['sentiment-item']}>
													<span className={styles['sentiment-label']}>
														{news.sentiment === 'positive'
															? '긍정'
															: news.sentiment === 'negative'
															? '부정'
															: '중립'}
													</span>
												</div>
											</div>
										</div>
									))}
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
								<button className={styles['detail-button']}>
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
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
								<button className={styles['detail-button']}>
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
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
								<button className={styles['detail-button']}>
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
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
											<span className={styles['prediction-label']}>
												단기 (1-3개월):
											</span>
											<span
												className={`${styles['prediction-value']} ${styles['positive']}`}
											>
												매수
											</span>
										</div>
										<div className={styles['prediction-item']}>
											<span className={styles['prediction-label']}>
												중기 (3-6개월):
											</span>
											<span
												className={`${styles['prediction-value']} ${styles['positive']}`}
											>
												강력 매수
											</span>
										</div>
										<div className={styles['prediction-item']}>
											<span className={styles['prediction-label']}>
												장기 (6개월+):
											</span>
											<span
												className={`${styles['prediction-value']} ${styles['negative']}`}
											>
												매도
											</span>
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

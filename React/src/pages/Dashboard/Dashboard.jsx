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
import newsData from '../../../../data/newsData.json';

// 뉴스 감성 분석 데이터 (각 뉴스는 하나의 감성만 가짐)
const newsSentimentData = [
	'positive',
	'positive',
	'negative',
	'positive',
	'neutral',
	'negative',
	'positive',
	'negative',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
	'neutral',
	'neutral',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
	'neutral',
	'positive',
	'negative',
	'positive',
];

// 뉴스 감성 분포 계산
const calculateSentimentRatio = (sentimentData) => {
	const total = sentimentData.length;
	const positiveCount = sentimentData.filter(
		(sentiment) => sentiment === 'positive'
	).length;
	const negativeCount = sentimentData.filter(
		(sentiment) => sentiment === 'negative'
	).length;
	const neutralCount = sentimentData.filter(
		(sentiment) => sentiment === 'neutral'
	).length;

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
		operatingProfit: 588900000000,
		netProfit: 443400000000,
	},
	{
		year: '2019',
		revenue: 2304000000000,
		operatingProfit: 277700000000,
		netProfit: 217400000000,
	},
	{
		year: '2020',
		revenue: 2368100000000,
		operatingProfit: 359900000000,
		netProfit: 264100000000,
	},
	{
		year: '2021',
		revenue: 2796000000000,
		operatingProfit: 516300000000,
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

export default function Dashboard() {
	const {
		selectedStock,
		stocks,
		loading: stockLoading,
		setSelectedStockByCode,
	} = useStock();
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	// 실시간 주식 데이터 상태
	const [stockData, setStockData] = useState([]);
	const [volumeData, setVolumeData] = useState([]);
	const [stockSummary, setStockSummary] = useState({
		currentPrice: 0,
		change: 0,
		changePercent: 0,
		volume: 0,
		marketCap: 0,
	});
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);
	const [error, setError] = useState(null);
	const [lastUpdated, setLastUpdated] = useState(null);

	// 차트 간격 설정 상태
	const [chartInterval, setChartInterval] = useState('1m'); // 1m, 5m, 15m, 30m, 1h

	useEffect(() => {
		if (selectedStock && stocks.length > 0) {
			const selectedRealTimeData = stocks.find(
				(s) => s.stockCode === selectedStock.stockCode
			);
			if (selectedRealTimeData) {
				setStockSummary(selectedRealTimeData);

				const now = new Date();
				const newStockData = [];
				const newVolumeData = [];
				const intervalSettings = {
					'1m': { count: 15, intervalMs: 60000 },
					'5m': { count: 12, intervalMs: 300000 },
					'15m': { count: 16, intervalMs: 900000 },
					'30m': { count: 12, intervalMs: 1800000 },
					'1h': { count: 12, intervalMs: 3600000 },
				};
				const settings =
					intervalSettings[chartInterval] || intervalSettings['1m'];

				for (let i = settings.count - 1; i >= 0; i--) {
					const time = new Date(now.getTime() - i * settings.intervalMs);
					const basePrice = selectedRealTimeData.currentPrice;
					const priceVariation = (Math.random() - 0.5) * (basePrice * 0.01);
					const price = basePrice + priceVariation;
					const volume = Math.floor(Math.random() * 1000000) + 500000;
					const timeString = time.toLocaleTimeString('ko-KR', {
						hour: '2-digit',
						minute: '2-digit',
						hour12: false,
					});

					newStockData.push({
						time: timeString,
						price: Math.round(price),
						open: Math.round(basePrice),
						high: Math.round(Math.max(basePrice, price)),
						low: Math.round(Math.min(basePrice, price)),
						close: Math.round(price),
					});
					newVolumeData.push({ time: timeString, volume: volume });
				}
				setStockData(newStockData);
				setVolumeData(newVolumeData);
				setLastUpdated(new Date());
				setLoading(false);
			}
		}
	}, [selectedStock, stocks, chartInterval]);

	useEffect(() => {
		const dashboardMain = document.querySelector(
			`.${styles['dashboard-main']}`
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
				`.${styles['dashboard-main']}`
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
					`.${styles['dashboard-main']}`
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

	if (stockLoading || !selectedStock) {
		return <div>Loading...</div>; // or a spinner component
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
									{refreshing ? (
										<div className={styles['refresh-indicator']}>
											<div className={styles['refresh-spinner']}></div>
											<span>갱신 중...</span>
										</div>
									) : lastUpdated ? (
										<div className={styles['last-updated']}>
											<i className="fas fa-clock"></i>
											<span>
												마지막 업데이트: {lastUpdated.toLocaleTimeString()}
											</span>
										</div>
									) : null}
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
												onChange={(e) => setChartInterval(e.target.value)}
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
									{loading ? (
										<div className={styles['chart-loading']}>
											데이터를 불러오는 중...
										</div>
									) : error ? (
										<div className={styles['chart-error']}>
											<i className="fas fa-exclamation-triangle"></i>
											<p>차트 데이터를 불러올 수 없습니다</p>
											<p className={styles['error-detail']}>{error}</p>
										</div>
									) : stockData.length === 0 ? (
										<div className={styles['chart-error']}>
											<i className="fas fa-chart-line"></i>
											<p>차트 데이터가 없습니다</p>
											<p className={styles['error-detail']}>
												주식 데이터를 가져올 수 없습니다
											</p>
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
						{/* 리포트 기준 주가 섹션 */}
						<div className={styles['section-container']}>
							<div className={styles['section-label']}>
								<div className={styles['section-title']}>
									<h2>리포트 기준 주가</h2>
									<p>{selectedStock.analysisDate} 기준 주가 및 지표</p>
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
											<span className={styles['timestamp-label']}>
												분석 시점:
											</span>
											<span className={styles['timestamp-value']}>
												{selectedStock.analysisDate}
											</span>
										</div>
									</div>
									<div className={styles['unified-chart-wrapper']}>
										<UnifiedStockChart
											stockData={stockData} // Using dynamic data now
											volumeData={volumeData} // Using dynamic data now
											simpleMode={false}
										/>
									</div>
								</div>

								{/* 분석 기준 시점 정보 카드들 */}
								<div className={styles['stock-cards']}>
									<div className={styles['stock-card']}>
										<h3>기준가</h3>
										<p className={styles['stock-value']}>
											₩{stockSummary?.currentPrice?.toLocaleString() || '0'}
										</p>
									</div>
									<div className={styles['stock-card']}>
										<h3>전일 대비</h3>
										<p
											className={`${styles['stock-value']} ${styles['positive']}`}
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
								{/* 주요 재무 지표 카드들 */}
								<div className={styles['financial-cards']}>
									<div className={styles['financial-card']}>
										<h3>매출액</h3>
										<p className={styles['financial-value']}>₩1,000억</p>
										<span
											className={`${styles['financial-change']} ${styles['positive']}`}
										>
											+12.5%
										</span>
									</div>
									<div className={styles['financial-card']}>
										<h3>영업이익</h3>
										<p className={styles['financial-value']}>₩200억</p>
										<span
											className={`${styles['financial-change']} ${styles['positive']}`}
										>
											+8.3%
										</span>
									</div>
									<div className={styles['financial-card']}>
										<h3>당기순이익</h3>
										<p className={styles['financial-value']}>₩150억</p>
										<span
											className={`${styles['financial-change']} ${styles['positive']}`}
										>
											+15.2%
										</span>
									</div>
								</div>
							</div>
						</div>

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
									{newsData.slice(0, 3).map((news, index) => (
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

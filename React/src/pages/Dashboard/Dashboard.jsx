import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Sns from '../../component/Sns/Sns';
import Footer from '../../component/Footer/Footer';
import Chart from '../../component/Chart/Chart';
import CandleStickChart from '../../component/CandleStickChart/CandleStickChart';
import UnifiedStockChart from '../../component/UnifiedStockChart/UnifiedStockChart';
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

export default function Dashboard({ selectedSymbol, onSymbolChange }) {
	const [showFooterButton, setShowFooterButton] = useState(false);
	const [showFooter, setShowFooter] = useState(false);
	const [buttonAnimation, setButtonAnimation] = useState('');
	const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
	const [isInFooter, setIsInFooter] = useState(false);
	const footerRef = useRef(null);
	const showFooterButtonRef = useRef(false);

	// 심볼에 따른 주식 이름 매핑
	const getStockName = (symbol) => {
		const stockNames = {
			'005930': '삼성전자',
			'000660': 'SK하이닉스',
			'035420': 'NAVER',
			'207940': '삼성바이오로직스',
			'006400': '삼성SDI'
		};
		return stockNames[symbol] || '알 수 없는 주식';
	};

	// 심볼에 따른 시장 구분 매핑
	const getMarketType = (symbol) => {
		const marketTypes = {
			'005930': 'KOSPI',
			'000660': 'KOSPI',
			'035420': 'KOSPI',
			'207940': 'KOSPI',
			'006400': 'KOSPI'
		};
		return marketTypes[symbol] || 'KOSPI';
	};

	// 실시간 주식 데이터 상태
	const [stockData, setStockData] = useState([]);
	const [volumeData, setVolumeData] = useState([]);
	const [stockSummary, setStockSummary] = useState({
		currentPrice: 50000,
		change: 0,
		changePercent: 0,
		volume: 0,
		marketCap: 0,
	});
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);
	const refreshingRef = useRef(false);
	const [error, setError] = useState(null);
	const [lastUpdated, setLastUpdated] = useState(null);
	
	// TopNav용 주식 데이터 상태
	const [topNavStocks, setTopNavStocks] = useState([]);
	const [topNavLoading, setTopNavLoading] = useState(true);
	
	// 차트 간격 설정 상태
	const [chartInterval, setChartInterval] = useState('1m'); // 1m, 5m, 15m, 30m, 1h
	
	// 주요 주식 심볼 목록
	const stockSymbols = [
		{ symbol: '005930', name: '삼성전자' },
		{ symbol: '000660', name: 'SK하이닉스' },
		{ symbol: '035420', name: 'NAVER' },
		{ symbol: '207940', name: '삼성바이오로직스' },
		{ symbol: '006400', name: '삼성SDI' }
	];

	// 갱신 함수 - 모든 주식 데이터를 한 번에 가져와서 동기화
	const refreshStockData = async () => {
		try {
			console.log('🔄 전체 주식 데이터 갱신 시작 - API 호출 예정');
			refreshingRef.current = true;
			setRefreshing(true);
			
			// 모든 주식의 데이터를 병렬로 가져오기
			console.log('📡 모든 주식 API 호출 중...');
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
			console.log('📡 모든 주식 API 응답 받음:', allStockData);
			
			// 변동폭 순으로 정렬 (절댓값 기준)
			const sortedStocks = allStockData.sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent));
			
			// TopNav 데이터 업데이트
			setTopNavStocks(sortedStocks);
			
			// 선택된 주식의 데이터 찾기
			const selectedStockData = sortedStocks.find(stock => stock.symbol === selectedSymbol);
			
			if (selectedStockData) {
				// API 데이터를 차트용 데이터로 변환
				const now = new Date();
				const stockData = [];
				const volumeData = [];
				
				// 차트 간격에 따른 데이터 포인트 수와 간격 설정
				const intervalSettings = {
					'1m': { count: 15, intervalMs: 60000, label: '분' },
					'5m': { count: 12, intervalMs: 300000, label: '분' },
					'15m': { count: 16, intervalMs: 900000, label: '분' },
					'30m': { count: 12, intervalMs: 1800000, label: '분' },
					'1h': { count: 12, intervalMs: 3600000, label: '시간' }
				};
				
				const settings = intervalSettings[chartInterval] || intervalSettings['1m'];
				
				// 설정된 간격으로 데이터 포인트 생성
				for (let i = settings.count - 1; i >= 0; i--) {
					const time = new Date(now.getTime() - i * settings.intervalMs);
					const basePrice = selectedStockData.currentPrice;
					const priceVariation = (Math.random() - 0.5) * (basePrice * 0.01); // ±1% 변동
					const price = basePrice + priceVariation;
					const volume = Math.floor(Math.random() * 1000000) + 500000;
					
					// 시간을 시:분 형식으로 변환
					const timeString = time.toLocaleTimeString('ko-KR', { 
						hour: '2-digit', 
						minute: '2-digit',
						hour12: false 
					});
					
					stockData.push({
						time: timeString,
						price: Math.round(price),
						open: Math.round(basePrice),
						high: Math.round(Math.max(basePrice, price)),
						low: Math.round(Math.min(basePrice, price)),
						close: Math.round(price)
					});
					
					volumeData.push({
						time: timeString,
						volume: volume
					});
				}
				
				setStockData(stockData);
				setVolumeData(volumeData);
				
				// stock-card 상세 데이터도 함께 업데이트 (동일한 데이터 사용)
				setStockSummary({
					currentPrice: selectedStockData.currentPrice,
					change: selectedStockData.change,
					changePercent: selectedStockData.changePercent,
					volume: selectedStockData.volume,
					marketCap: selectedStockData.marketCap,
				});
				
				console.log('✅ 모든 데이터 동기화 완료 - TopNav, 차트, 상세데이터 모두 동일한 API 응답 사용');
				setLastUpdated(new Date());
				setError(null);
			}
		} catch (err) {
			console.error('주식 데이터 갱신 실패:', err);
		} finally {
			// 갱신 중 표시를 더 오래 보이도록 지연
			setTimeout(() => {
				console.log('🔄 갱신 완료 - 로딩 상태 해제');
				refreshingRef.current = false;
				setRefreshing(false);
			}, 1000); // 1초 지연
		}
	};

	// 실시간 주식 데이터 로드 (차트용) - TopNav 데이터 사용
	useEffect(() => {
		const loadStockData = async () => {
			try {
				setLoading(true);
				setError(null);

				// TopNav 데이터에서 선택된 주식 찾기
				if (topNavStocks && topNavStocks.length > 0) {
					const selectedStockData = topNavStocks.find(stock => stock.symbol === selectedSymbol);
					
					if (selectedStockData) {
						// TopNav 데이터를 차트용 데이터로 변환
						const now = new Date();
						const stockData = [];
						const volumeData = [];
						
						// 차트 간격에 따른 데이터 포인트 수와 간격 설정
						const intervalSettings = {
							'1m': { count: 15, intervalMs: 60000, label: '분' },
							'5m': { count: 12, intervalMs: 300000, label: '분' },
							'15m': { count: 16, intervalMs: 900000, label: '분' },
							'30m': { count: 12, intervalMs: 1800000, label: '분' },
							'1h': { count: 12, intervalMs: 3600000, label: '시간' }
						};
						
						const settings = intervalSettings[chartInterval] || intervalSettings['1m'];
						
						// 설정된 간격으로 데이터 포인트 생성
						for (let i = settings.count - 1; i >= 0; i--) {
							const time = new Date(now.getTime() - i * settings.intervalMs);
							const basePrice = selectedStockData.currentPrice;
							const priceVariation = (Math.random() - 0.5) * (basePrice * 0.01); // ±1% 변동
							const price = basePrice + priceVariation;
							const volume = Math.floor(Math.random() * 1000000) + 500000;
							
							// 시간을 시:분 형식으로 변환
							const timeString = time.toLocaleTimeString('ko-KR', { 
								hour: '2-digit', 
								minute: '2-digit',
								hour12: false 
							});
							
							stockData.push({
								time: timeString,
								price: Math.round(price),
								open: Math.round(basePrice),
								high: Math.round(Math.max(basePrice, price)),
								low: Math.round(Math.min(basePrice, price)),
								close: Math.round(price)
							});
							
							volumeData.push({
								time: timeString,
								volume: volume
							});
						}
						
						setStockData(stockData);
						setVolumeData(volumeData);
						setError(null);
					} else {
						// 선택된 주식 데이터가 없으면 빈 배열
						setStockData([]);
						setVolumeData([]);
						setError(null);
					}
				} else {
					// TopNav 데이터가 없으면 빈 배열
					setStockData([]);
					setVolumeData([]);
					setError(null);
				}
			} catch (err) {
				console.error('주식 데이터 로드 실패:', err);
				setError(err.message);
			} finally {
				setLoading(false);
			}
		};

		loadStockData();

		// 10초마다 데이터 새로고침 (테스트용)
		const interval = setInterval(() => {
			refreshStockData();
		}, 10000);

		return () => clearInterval(interval);
	}, [chartInterval, selectedSymbol, topNavStocks]); // 원래 의존성으로 복원

	// 선택된 주식의 요약 정보를 TopNav 데이터와 동기화 (우선순위)
	useEffect(() => {
		if (topNavStocks && topNavStocks.length > 0) {
			const selectedStockData = topNavStocks.find(stock => stock.symbol === selectedSymbol);
			if (selectedStockData) {
				setStockSummary({
					currentPrice: selectedStockData.currentPrice,
					change: selectedStockData.change,
					changePercent: selectedStockData.changePercent,
					volume: selectedStockData.volume,
					marketCap: selectedStockData.marketCap,
				});
			}
		} else {
			// TopNav 데이터가 없으면 기본값 사용
			setStockSummary({
				currentPrice: 50000,
				change: 0,
				changePercent: 0,
				volume: 0,
				marketCap: 0,
			});
		}
	}, [topNavStocks, selectedSymbol]);

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
	}, []);

	// const handleLogout = () => {
	// 	logout();
	// 	window.location.href = '/';
	// };

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
						<TopNav 
							selectedSymbol={selectedSymbol}
							onSymbolChange={onSymbolChange}
							topNavStocks={topNavStocks}
							topNavLoading={topNavLoading}
							onStockSelect={onSymbolChange}
						/>

						{/* 주식 정보 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>{getStockName(selectedSymbol)}/{selectedSymbol}/{getMarketType(selectedSymbol)}</h2>
									<p>실시간 주가 및 주요 지표</p>
								</div>
								<div className="section-action">
									{refreshing ? (
										<div className="refresh-indicator">
											<div className="refresh-spinner"></div>
											<span>갱신 중...</span>
										</div>
									) : lastUpdated ? (
										<div className="last-updated">
											<i className="fas fa-clock"></i>
											<span>마지막 업데이트: {lastUpdated.toLocaleTimeString()}</span>
										</div>
									) : null}
								</div>
							</div>
							<div className="stock-info-section">
								{/* 통합 주식 차트 */}
								<div className="unified-chart-container">
									<div className="chart-header">
										<h3>실시간 주가 및 거래량</h3>
										<div className="chart-interval-selector">
											<label htmlFor="interval-select">차트 간격:</label>
											<select 
												id="interval-select"
												value={chartInterval} 
												onChange={(e) => setChartInterval(e.target.value)}
												className="interval-select"
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
										<div className="chart-loading">데이터를 불러오는 중...</div>
									) : error ? (
										<div className="chart-error">
											<i className="fas fa-exclamation-triangle"></i>
											<p>차트 데이터를 불러올 수 없습니다</p>
											<p className="error-detail">{error}</p>
										</div>
									) : stockData.length === 0 ? (
										<div className="chart-error">
											<i className="fas fa-chart-line"></i>
											<p>차트 데이터가 없습니다</p>
											<p className="error-detail">주식 데이터를 가져올 수 없습니다</p>
									</div>
									) : (
										<div className="unified-chart-wrapper">
											<UnifiedStockChart
												stockData={stockData}
												volumeData={volumeData}
												simpleMode={false}
											/>
										</div>
									)}
								</div>

								{/* 주식 정보 카드들 */}
								<div className="stock-cards">
									<div className="stock-card">
										<h3>현재가</h3>
										<p className="stock-value">
											₩{stockSummary?.currentPrice?.toLocaleString() || '50,000'}
										</p>
									</div>
									<div className="stock-card">
										<h3>전일 대비</h3>
										<p className={`stock-value ${(stockSummary?.change || 0) >= 0 ? 'positive' : 'negative'}`}>
											{(stockSummary?.change || 0) >= 0 ? '+' : ''}{(stockSummary?.changePercent || 0).toFixed(2)}%
										</p>
									</div>
									<div className="stock-card">
										<h3>거래량</h3>
										<p className="stock-value">
											{(stockSummary?.volume || 0).toLocaleString()}
										</p>
									</div>
									<div className="stock-card">
										<h3>시가총액</h3>
										<p className="stock-value">
											₩{((stockSummary?.marketCap || 0) / 1000000000000).toFixed(1)}조
										</p>
									</div>
								</div>
							</div>
						</div>


						<Sns selectedSymbol={selectedSymbol} />
					</div>

					<div className="dashboard-grid2">
						{/* 리포트 기준 주가 섹션 */}
						<div className="section-container">
							<div className="section-label">
								<div className="section-title">
									<h2>리포트 기준 주가</h2>
									<p>2024년 1월 15일 14:30 기준 주가 및 지표</p>
								</div>
								<button className="detail-button">
									상세보기
									<i className="fas fa-chevron-right"></i>
								</button>
							</div>
							<div className="stock-info-section">
								{/* 정적 차트 컨테이너 */}
								<div className="unified-chart-container">
									<div className="chart-header">
										<h3>기준 시점 주가 및 거래량</h3>
										<div className="analysis-timestamp">
											<span className="timestamp-label">분석 시점:</span>
											<span className="timestamp-value">2024-01-15 14:30</span>
										</div>
									</div>
									<div className="unified-chart-wrapper">
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
								<div className="stock-cards">
									<div className="stock-card">
										<h3>기준가</h3>
										<p className="stock-value">
											₩50,600
										</p>
									</div>
									<div className="stock-card">
										<h3>전일 대비</h3>
										<p className="stock-value positive">
											+1.2%
										</p>
									</div>
									<div className="stock-card">
										<h3>거래량</h3>
										<p className="stock-value">
											2,500,000
										</p>
									</div>
									<div className="stock-card">
										<h3>시가총액</h3>
										<p className="stock-value">
											₩378.2조
										</p>
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
									<div className="chart-header">
										<h3>연도별 재무 성과 (단위 : 10억원)</h3>
									</div>
									<div className="unified-chart-wrapper">
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

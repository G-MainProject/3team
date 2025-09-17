import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import RightNav from '../../component/Nav/RightNav';
import Footer from '../../component/Footer/Footer';
import Chart from '../../component/Chart/Chart';
import CandleStickChart from '../../component/CandleStickChart/CandleStickChart';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import MyWordCloud from '../../component/WordCloud/MyWordCloud';

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

const realtimeStockData = [
	{ time: '10:00', price: 50000 },
	{ time: '10:05', price: 50100 },
	{ time: '10:10', price: 50050 },
	{ time: '10:15', price: 50200 },
	{ time: '10:20', price: 50150 },
	{ time: '10:25', price: 50300 },
	{ time: '10:30', price: 50250 },
];

const realtimeStockSeries = [
	{ key: 'price', name: '실시간 주가', color: '#8884d8' },
];

const dailyStockData = [
	{ date: '08-12', price: 50000 },
	{ date: '08-13', price: 51000 },
	{ date: '08-14', price: 50500 },
	{ date: '08-15', price: 52000 },
	{ date: '08-16', price: 51500 },
	{ date: '08-17', price: 52500 },
	{ date: '08-18', price: 53000 },
];

const dailyStockSeries = [
	{ key: 'price', name: '일별 주가', color: '#82ca9d' },
];

{
	/*	거래량 추이 데이터
const candlestickData = [
	{
		date: '08-12',
		open: 50000,
		high: 50500,
		low: 49800,
		close: 50300,
		volume: 1234567,
	},
	{
		date: '08-13',
		open: 50300,
		high: 51200,
		low: 50100,
		close: 51000,
		volume: 1534567,
	},
	{
		date: '08-14',
		open: 51000,
		high: 51100,
		low: 50400,
		close: 50500,
		volume: 1134567,
	},
	{
		date: '08-15',
		open: 50500,
		high: 52200,
		low: 50450,
		close: 52000,
		volume: 1634567,
	},
	{
		date: '08-16',
		open: 52000,
		high: 52100,
		low: 51300,
		close: 51500,
		volume: 1434567,
	},
	{
		date: '08-17',
		open: 51500,
		high: 52800,
		low: 51400,
		close: 52500,
		volume: 1734567,
	},
	{
		date: '08-18',
		open: 52500,
		high: 53200,
		low: 52400,
		close: 53000,
		volume: 1834567,
	},
];
*/
}

// 거래량 추이 데이터를 랜덤으로 생성하는 함수
function generateRealisticStockData(days = 30) {
	const data = [];
	let lastClose = 50000; // 시작 가격
	let lastVolume = 1500000; // 시작 거래량

	for (let i = 0; i < days; i++) {
		const date = `08-${12 + i}`; // 날짜 생성
		const open = lastClose;

		// 가격 변동폭을 -4% ~ +5% 사이로 랜덤하게 설정
		const changePercent = (Math.random() - 0.45) * 0.09;
		let close = open * (1 + changePercent);

		// 고가와 저가 생성
		const high = Math.max(open, close) * (1 + Math.random() * 0.02);
		const low = Math.min(open, close) * (1 - Math.random() * 0.02);

		// 거래량 변동 생성 (가격 변동이 클 때 거래량도 늘어나는 경향을 반영)
		const volumeChange = (Math.random() - 0.5) * 0.7;
		let volume =
			lastVolume * (1 + volumeChange) + Math.abs(changePercent) * 5000000;
		volume = Math.max(500000, volume); // 최소 거래량 보장

		data.push({
			date,
			open: Math.round(open),
			high: Math.round(high),
			low: Math.round(low),
			close: Math.round(close),
			volume: Math.round(volume),
		});

		lastClose = close;
		lastVolume = volume;
	}
	return data;
}

const candlestickData = generateRealisticStockData(30);

// 거래량 데이터를 캔들 차트용 데이터(OHLC)로 변환하는 코드
const volumeCandleData = candlestickData.map((d, i, arr) => {
	// 첫 번째 데이터는 이전 데이터가 없으므로 시가(open)와 종가(close)를 동일하게 설정
	const open = i === 0 ? d.volume : arr[i - 1].volume;
	const close = d.volume;

	return {
		date: d.date,
		open: open,
		close: close,
		// 꼬리(wick)가 없는 캔들을 위해 high와 low를 open/close 중 큰 값/작은 값으로 설정
		high: Math.max(open, close),
		low: Math.min(open, close),
	};
});

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
											<Chart
												data={realtimeStockData}
												series={realtimeStockSeries}
												xAxisKey="time"
												yAxisUnit="원"
												simpleMode={true}
											/>
										</div>
									</div>
									<div className="kpi-chart-item">
										<h3>일별 주가 차트</h3>
										<div className="kpi-chart-placeholder">
											<Chart
												data={dailyStockData}
												series={dailyStockSeries}
												xAxisKey="date"
												yAxisUnit="원"
												simpleMode={true}
											/>
										</div>
									</div>
									<div className="kpi-chart-item">
										<h3>거래량 추이</h3>
										<div className="kpi-chart-placeholder">
											<CandleStickChart
												data={volumeCandleData}
												simpleMode={false}
											/>
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
									<h3>연도별 재무 성과 (단위 : 10억원)</h3>
									<Chart
										data={financialData}
										series={financialChartSeries}
										xAxisKey="year"
										yAxisUnit="원"
										xAxisUnit="년"
										yAxisFormatType="billions"
									/>
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

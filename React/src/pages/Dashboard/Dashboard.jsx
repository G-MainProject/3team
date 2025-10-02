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
		isMarketClosed,
		refreshData: refreshRealtimeData,
	} = useRealtimeStockData(currentSymbol);

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

	// 차트 간격 변경 핸들러 (버튼 클릭)
	const handleIntervalChange = useCallback((interval) => {
		setChartInterval(interval);
	}, []);

	// 실시간 데이터를 차트 형식으로 변환 (간격에 따라 조정)
	const stockData = useMemo(() => {
		if (!realtimeStockData || realtimeStockData.length === 0) return [];
		
		// 간격에 따른 데이터 개수 설정 (차트 표시용)
		const getDataCount = (interval) => {
			switch (interval) {
				case '1m': return 15;  // 15개
				case '5m': return 15;  // 15개 (5분 간격)
				case '15m': return 12; // 12개 (15분 간격)
				case '30m': return 8;  // 8개 (30분 간격)
				case '1h': return 6;   // 6개 (1시간 간격)
				default: return 15;
			}
		};
		
		const dataCount = getDataCount(chartInterval);
		const intervalMinutes = parseInt(chartInterval.replace('m', '').replace('h', '')) * (chartInterval.includes('h') ? 60 : 1);
		
		// 충분한 원본 데이터 확보 (7시간 = 420분 데이터)
		const minDataCount = Math.max(420, dataCount * intervalMinutes);
		
		// 원본 데이터를 복사하고 시간 순서대로 정렬
		const sortedData = [...realtimeStockData].sort((a, b) => {
			// timestamp가 있으면 timestamp로 정렬
			if (a.timestamp && b.timestamp) {
				return new Date(a.timestamp) - new Date(b.timestamp);
			}
			// timestamp가 없으면 time으로 정렬
			if (a.time && b.time) {
				return a.time.localeCompare(b.time);
			}
			return 0;
		});
		
		// 충분한 원본 데이터 확보
		let sourceData;
		if (sortedData.length >= minDataCount) {
			// 충분한 데이터가 있으면 최신 데이터 사용
			sourceData = sortedData.slice(-minDataCount);
		} else {
			// 부족한 데이터는 마지막 데이터로 채우기
			sourceData = [...sortedData];
			const lastItem = sortedData[sortedData.length - 1];
			while (sourceData.length < minDataCount) {
				sourceData.unshift({ ...lastItem });
			}
		}
		
		// 간격에 맞는 데이터 개수로 제한 (차트 표시용)
		let limitedData;
		if (sourceData.length >= dataCount) {
			limitedData = sourceData.slice(-dataCount);
		} else {
			limitedData = sourceData;
		}
		
		return limitedData.map((item, index) => {
			// 시간 생성 로직: 장중 시간(9:00-15:30)에 맞춰 시간 계산
			const now = new Date();
			const currentHour = now.getHours();
			const currentMinute = now.getMinutes();
			
			// 현재 시간이 장중이 아니면 마지막 장중 시간(15:30)을 기준으로 계산
			let baseTime;
			if (currentHour < 9 || (currentHour === 9 && currentMinute < 0) || currentHour >= 15 || (currentHour === 15 && currentMinute >= 30)) {
				// 장외 시간이면 마지막 장중 시간(15:30)을 기준으로 계산
				const today = new Date();
				baseTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 15, 30);
			} else {
				// 장중 시간이면 현재 시간을 기준으로 계산
				baseTime = now;
			}
			
			const dataTime = new Date(baseTime.getTime() - (limitedData.length - index - 1) * intervalMinutes * 60000);
			
			// 간격에 맞게 시간을 정규화 (차트 표시 시간 기준)
			const normalizedTime = new Date(dataTime);
			if (chartInterval === '1h') {
				// 1시간 간격: 14:00 표시라면 13:00:00부터 14:00:00까지
				normalizedTime.setMinutes(0, 0, 0);
			} else if (chartInterval === '30m') {
				// 30분 간격: 14:30 표시라면 14:00:00부터 14:30:00까지
				const minute = normalizedTime.getMinutes();
				if (minute < 30) {
					normalizedTime.setMinutes(0, 0, 0);
				} else {
					normalizedTime.setMinutes(30, 0, 0);
				}
			} else if (chartInterval === '15m') {
				// 15분 간격: 14:15 표시라면 14:00:00부터 14:15:00까지
				const minute = normalizedTime.getMinutes();
				if (minute < 15) normalizedTime.setMinutes(0, 0, 0);
				else if (minute < 30) normalizedTime.setMinutes(15, 0, 0);
				else if (minute < 45) normalizedTime.setMinutes(30, 0, 0);
				else normalizedTime.setMinutes(45, 0, 0);
			} else if (chartInterval === '5m') {
				// 5분 간격: 14:05 표시라면 14:00:00부터 14:05:00까지
				const minute = normalizedTime.getMinutes();
				const normalizedMinute = Math.floor(minute / 5) * 5;
				normalizedTime.setMinutes(normalizedMinute, 0, 0);
			} else if (chartInterval === '1m') {
				// 1분 간격: 14:18 표시라면 14:17:00부터 14:18:00까지
				normalizedTime.setSeconds(0, 0);
			}
			
			// 표시 시간은 정규화된 시간 그대로 사용
			let displayTime = normalizedTime;
			
			const timeString = displayTime.toLocaleTimeString('ko-KR', {
				hour: '2-digit',
				minute: '2-digit',
				hour12: false,
			});
			
			// 장외 시간 데이터는 0으로 표시
			const hour = normalizedTime.getHours();
			const minute = normalizedTime.getMinutes();
			const isMarketTime = (hour >= 9 && hour < 15) || (hour === 15 && minute <= 30);
			
			return {
				time: timeString,
				price: isMarketTime ? (item.price || 0) : 0,
				open: isMarketTime ? (item.open || item.price || 0) : 0,
				high: isMarketTime ? (item.high || item.price || 0) : 0,
				low: isMarketTime ? (item.low || item.price || 0) : 0,
				close: isMarketTime ? (item.close || item.price || 0) : 0,
			};
		});
	}, [realtimeStockData, chartInterval]);


	const volumeData = useMemo(() => {
		// 주가 데이터와 동일한 시간 구조를 사용하여 거래량 데이터 생성 (간격에 따라 조정)
		if (!realtimeStockData || realtimeStockData.length === 0) return [];
		
		// 간격에 따른 데이터 개수 설정 (차트 표시용)
		const getDataCount = (interval) => {
			switch (interval) {
				case '1m': return 15;  // 15개
				case '5m': return 15;  // 15개 (5분 간격)
				case '15m': return 12; // 12개 (15분 간격)
				case '30m': return 8;  // 8개 (30분 간격)
				case '1h': return 6;   // 6개 (1시간 간격)
				default: return 15;
			}
		};
		
		const dataCount = getDataCount(chartInterval);
		const intervalMinutes = parseInt(chartInterval.replace('m', '').replace('h', '')) * (chartInterval.includes('h') ? 60 : 1);
		
		// 주가 데이터와 동일한 정렬 및 제한 로직 적용
		const sortedData = [...realtimeStockData].sort((a, b) => {
			if (a.timestamp && b.timestamp) {
				return new Date(a.timestamp) - new Date(b.timestamp);
			}
			if (a.time && b.time) {
				return a.time.localeCompare(b.time);
			}
			return 0;
		});
		
		// 거래량 데이터도 동일하게 정렬
		const sortedVolumeData = realtimeVolumeData ? [...realtimeVolumeData].sort((a, b) => {
			if (a.timestamp && b.timestamp) {
				return new Date(a.timestamp) - new Date(b.timestamp);
			}
			if (a.time && b.time) {
				return a.time.localeCompare(b.time);
			}
			return 0;
		}) : [];
		
		// 간격에 맞는 데이터 개수로 제한 (주가와 동일)
		let limitedData;
		if (sortedData.length >= dataCount) {
			limitedData = sortedData.slice(-dataCount);
		} else {
			limitedData = [...sortedData];
			const lastItem = sortedData[sortedData.length - 1];
			while (limitedData.length < dataCount) {
				limitedData.unshift({ ...lastItem });
			}
		}
		
		// 거래량 데이터도 충분히 확보 (1분은 실시간, 나머지는 과거 데이터 고정)
		let limitedVolumeData;
		
		// 거래량 데이터 필터링 (volume이 0이어도 유효한 데이터로 간주)
		const validVolumeData = sortedVolumeData.filter(item => item && (item.volume !== undefined && item.volume !== null));
		
		if (chartInterval === '1m') {
			// 1분 간격: 7시간(420분) 데이터 사용
			if (validVolumeData.length >= 420) {
				limitedVolumeData = validVolumeData.slice(-420);
			} else if (validVolumeData.length > 0) {
				limitedVolumeData = [...validVolumeData];
				while (limitedVolumeData.length < 420) {
					const sourceIndex = limitedVolumeData.length % validVolumeData.length;
					const sourceItem = validVolumeData[sourceIndex];
					limitedVolumeData.push({ 
						...sourceItem,
						volume: sourceItem.volume
					});
				}
			} else {
				limitedVolumeData = Array(420).fill(null).map(() => ({ volume: 0 }));
			}
		} else {
			// 5분, 15분, 30분, 1시간 간격: 7시간(420분) 데이터 사용
			if (validVolumeData.length >= 420) {
				limitedVolumeData = validVolumeData.slice(-420);
			} else if (validVolumeData.length > 0) {
				limitedVolumeData = [...validVolumeData];
				while (limitedVolumeData.length < 420) {
					const sourceIndex = limitedVolumeData.length % validVolumeData.length;
					const sourceItem = validVolumeData[sourceIndex];
					limitedVolumeData.push({ 
						...sourceItem,
						volume: sourceItem.volume
					});
				}
			} else {
				limitedVolumeData = Array(420).fill(null).map(() => ({ volume: 0 }));
			}
		}
		
		
		return limitedData.map((item, index) => {
			// 시간 생성 로직: 장중 시간(9:00-15:30)에 맞춰 시간 계산
			const now = new Date();
			const currentHour = now.getHours();
			const currentMinute = now.getMinutes();
			
			// 현재 시간이 장중이 아니면 마지막 장중 시간(15:30)을 기준으로 계산
			let baseTime;
			if (currentHour < 9 || (currentHour === 9 && currentMinute < 0) || currentHour >= 15 || (currentHour === 15 && currentMinute >= 30)) {
				// 장외 시간이면 마지막 장중 시간(15:30)을 기준으로 계산
				const today = new Date();
				baseTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 15, 30);
			} else {
				// 장중 시간이면 현재 시간을 기준으로 계산
				baseTime = now;
			}
			
			const dataTime = new Date(baseTime.getTime() - (limitedData.length - index - 1) * intervalMinutes * 60000);
			
			// 간격에 맞게 시간을 정규화 (차트 표시 시간 기준)
			const normalizedTime = new Date(dataTime);
			if (chartInterval === '1h') {
				// 1시간 간격: 14:00 표시라면 13:00:00부터 14:00:00까지
				normalizedTime.setMinutes(0, 0, 0);
			} else if (chartInterval === '30m') {
				// 30분 간격: 14:30 표시라면 14:00:00부터 14:30:00까지
				const minute = normalizedTime.getMinutes();
				if (minute < 30) {
					normalizedTime.setMinutes(0, 0, 0);
				} else {
					normalizedTime.setMinutes(30, 0, 0);
				}
			} else if (chartInterval === '15m') {
				// 15분 간격: 14:15 표시라면 14:00:00부터 14:15:00까지
				const minute = normalizedTime.getMinutes();
				if (minute < 15) normalizedTime.setMinutes(0, 0, 0);
				else if (minute < 30) normalizedTime.setMinutes(15, 0, 0);
				else if (minute < 45) normalizedTime.setMinutes(30, 0, 0);
				else normalizedTime.setMinutes(45, 0, 0);
			} else if (chartInterval === '5m') {
				// 5분 간격: 14:05 표시라면 14:00:00부터 14:05:00까지
				const minute = normalizedTime.getMinutes();
				const normalizedMinute = Math.floor(minute / 5) * 5;
				normalizedTime.setMinutes(normalizedMinute, 0, 0);
			} else if (chartInterval === '1m') {
				// 1분 간격: 14:18 표시라면 14:17:00부터 14:18:00까지
				normalizedTime.setSeconds(0, 0);
			}
			
			// 표시 시간은 정규화된 시간 그대로 사용
			let displayTime = normalizedTime;
			
			const timeString = displayTime.toLocaleTimeString('ko-KR', {
				hour: '2-digit',
				minute: '2-digit',
				hour12: false,
			});
			
		// 간격에 따라 거래량 집계 (정확한 시간 구간 기반)
		let totalVolume = 0;
		
		// 모든 간격에 대해 동일한 시간 기반 집계 로직 적용
		// 정규화된 시간을 기준으로 해당 구간의 모든 1분 데이터 집계
		// 예: 1분 간격 13:48라면 13:47:00부터 13:48:00까지
		// 예: 5분 간격 14:05라면 14:00:00부터 14:05:00까지
		// 예: 1시간 간격 14:00라면 13:00:00부터 14:00:00까지
		const startTime = new Date(normalizedTime.getTime() - intervalMinutes * 60000);
		const endTime = new Date(normalizedTime);
		
		
		// 1분 간격 원본 데이터에서 해당 구간의 거래량 집계
		for (let i = 0; i < limitedVolumeData.length; i++) {
			const volumeItem = limitedVolumeData[i];
			if (volumeItem && volumeItem.volume !== undefined && volumeItem.volume !== null) {
				// 시간 비교를 위해 volumeItem의 시간을 Date 객체로 변환
				let itemTime;
				if (volumeItem.time) {
					// time이 "HH:MM" 형식인 경우 현재 날짜와 결합
					const today = new Date();
					const [hours, minutes] = volumeItem.time.split(':');
					itemTime = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 
										parseInt(hours), parseInt(minutes), 0); // 초를 0으로 설정
				} else if (volumeItem.timestamp) {
					itemTime = new Date(volumeItem.timestamp);
				} else {
					continue;
				}
				
				// 정확한 구간 내에 있는지 확인 (startTime <= itemTime < endTime)
				// 예: 1분 간격 13:48 표시라면 13:47:00 <= itemTime < 13:48:00
				// 예: 5분 간격 14:05 표시라면 14:00:00 <= itemTime < 14:05:00
				// 예: 1시간 간격 14:00 표시라면 13:00:00 <= itemTime < 14:00:00
				if (itemTime >= startTime && itemTime < endTime) {
					totalVolume += (volumeItem.volume || 0);
				}
			}
		}
			
			return {
				time: timeString,
				volume: totalVolume,
			};
		});
	}, [realtimeStockData, realtimeVolumeData, chartInterval]);


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
											{/* <span className={styles['interval-label']}>차트 간격:</span> */}
											<div className={styles['interval-buttons']}>
												<button
													className={`${styles['interval-btn']} ${chartInterval === '1m' ? styles['active'] : ''}`}
													onClick={() => handleIntervalChange('1m')}
												>
													1분
												</button>
												<button
													className={`${styles['interval-btn']} ${chartInterval === '5m' ? styles['active'] : ''}`}
													onClick={() => handleIntervalChange('5m')}
												>
													5분
												</button>
												<button
													className={`${styles['interval-btn']} ${chartInterval === '15m' ? styles['active'] : ''}`}
													onClick={() => handleIntervalChange('15m')}
												>
													15분
												</button>
												<button
													className={`${styles['interval-btn']} ${chartInterval === '30m' ? styles['active'] : ''}`}
													onClick={() => handleIntervalChange('30m')}
												>
													30분
												</button>
												<button
													className={`${styles['interval-btn']} ${chartInterval === '1h' ? styles['active'] : ''}`}
													onClick={() => handleIntervalChange('1h')}
												>
													1시간
												</button>
											</div>
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
										<div className={`${styles['unified-chart-wrapper']} ${isMarketClosed ? styles['market-closed-chart'] : ''}`}>
											{isMarketClosed && (
												<div className={styles['market-closed-overlay']}>
													<div className={styles['market-closed-message']}>
														<i className="fas fa-clock"></i>
														<span>장마감 - 마지막 거래 데이터</span>
													</div>
												</div>
											)}
											<UnifiedStockChart
												stockData={stockData}
												volumeData={volumeData}
												simpleMode={false}
												isMarketClosed={isMarketClosed}
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

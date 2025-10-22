import React from 'react';
import {
	ComposedChart,
	Line,
	Bar,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	Legend,
	ResponsiveContainer,
} from 'recharts';
import './UnifiedStockChart.css';

const UnifiedStockChart = ({ 
	stockData, 
	volumeData, 
	simpleMode = false,
	isMarketClosed = false
}) => {

	if (!stockData || stockData.length === 0) {
		return (
			<div className="unified-chart-placeholder">차트 데이터가 없습니다.</div>
		);
	}

    // 거래량을 시간 기준으로 매칭 (인덱스가 아닌 time/date 키로 결합)
    const volumeByTime = (volumeData || []).reduce((acc, v) => {
        const key = v.time || v.date;
        if (key) acc[key] = v.volume ?? 0;
        return acc;
    }, {});


    // 데이터를 통합하여 하나의 배열로 만들기 (시간 정렬 포함)
    const combinedData = stockData
        .map((stockItem, index) => {
            const key = stockItem.time || stockItem.date;
            // 시간이 정확히 일치하지 않으면 인덱스로 매칭 시도
            let vol = key && volumeByTime[key] != null ? volumeByTime[key] : 0;
            
            // 시간 매칭이 실패한 경우 인덱스로 매칭
            if (vol === 0 && volumeData && volumeData[index]) {
                vol = volumeData[index].volume || 0;
            }
            
            return {
                ...stockItem,
                volume: vol,
                date: key,
            };
        })
        .filter(d => d.date)
        .sort((a, b) => {
            // HH:mm 형식 우선 비교, 아니면 문자열 비교
            const at = a.date;
            const bt = b.date;
            if (/^\d{2}:\d{2}$/.test(at) && /^\d{2}:\d{2}$/.test(bt)) {
                return at.localeCompare(bt);
            }
            return String(at).localeCompare(String(bt));
        });

	// Y축 도메인 계산
	const priceValues = combinedData.map(d => d.value).filter(v => typeof v === 'number');
	const volumeValues = combinedData.map(d => d.volume).filter(v => typeof v === 'number');
	
	const priceMin = Math.min(...priceValues);
	const priceMax = Math.max(...priceValues);
	const volumeMax = Math.max(...volumeValues);

	const priceDomain = [
		Math.floor(priceMin * 0.98),
		Math.ceil(priceMax * 1.02)
	];

	const volumeDomain = [0, Math.ceil(volumeMax * 1.1)];

	// 툴팁 포맷터
	const formatTooltipValue = (value, name) => {
		if (name === 'value') {
			return [`₩${value.toLocaleString()}`, '주가'];
		}
		if (name === 'volume') {
			return [`${value.toLocaleString()}주`, '거래량'];
		}
		return [value, name];
	};

	// Y축 틱 포맷터
	const priceTickFormatter = (value) => `₩${value.toLocaleString()}`;
    const volumeTickFormatter = (value) => {
        if (value >= 1000000000) return `${(value / 1000000000).toFixed(1)}B`;
        if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
        return `${value.toLocaleString()}`;
    };

	return (
		<div className="unified-stock-chart">
			<ResponsiveContainer width="100%" height="100%">
				<ComposedChart
					data={combinedData}
					margin={{
						top: 20,
						right: 30,
						left: 20,
						bottom: 5,
					}}
				>
					<CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
					
					<XAxis 
						dataKey="date" 
						hide={simpleMode}
						tick={{ fontSize: 12 }}
					/>
					
					{/* 주가 Y축 */}
					<YAxis
						yAxisId="price"
						orientation="left"
						domain={priceDomain}
						tickFormatter={priceTickFormatter}
						hide={simpleMode}
						tick={{ fontSize: 12 }}
					/>
					
					{/* 거래량 Y축 - 거래량 데이터가 있을 때만 표시 */}
					{volumeData && volumeData.length > 0 && (
						<YAxis
							yAxisId="volume"
							orientation="right"
							domain={volumeDomain}
							tickFormatter={volumeTickFormatter}
							hide={simpleMode}
							tick={{ fontSize: 12 }}
						/>
					)}

					<Tooltip
						formatter={formatTooltipValue}
						contentStyle={{
							backgroundColor: 'rgba(255, 255, 255, 0.95)',
							border: '1px solid #e9ecef',
							borderRadius: '8px',
							boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
						}}
						labelStyle={{ 
							color: '#495057', 
							fontWeight: 'bold',
							fontSize: '14px'
						}}
						itemStyle={{ 
							fontWeight: 'normal',
							fontSize: '13px'
						}}
					/>

					{!simpleMode && (
						<Legend
							wrapperStyle={{
								paddingTop: '20px',
								color: '#495057',
								fontSize: '12px',
							}}
						/>
					)}

					{/* 거래량 바 차트 - 거래량 데이터가 있을 때만 표시 */}
					{volumeData && volumeData.length > 0 && (
						<Bar
							yAxisId="volume"
							dataKey="volume"
							name="거래량"
							fill="#e3f2fd"
							opacity={0.7}
							radius={[2, 2, 0, 0]}
						/>
					)}

					{/* 실시간 주가 라인 차트 */}
					<Line
						yAxisId="price"
						type="monotone"
						dataKey="value"
						name={isMarketClosed ? "마지막 거래 주가" : "실시간 주가"}
						stroke={isMarketClosed ? "#6c757d" : "#1976d2"}
						strokeWidth={3}
						strokeDasharray={isMarketClosed ? "5 5" : "0"}
						dot={{ fill: isMarketClosed ? '#6c757d' : '#1976d2', strokeWidth: 2, r: 4 }}
						activeDot={{ r: 6, stroke: isMarketClosed ? '#6c757d' : '#1976d2', strokeWidth: 2, fill: '#fff' }}
					/>
				</ComposedChart>
			</ResponsiveContainer>
		</div>
	);
};

export default UnifiedStockChart;

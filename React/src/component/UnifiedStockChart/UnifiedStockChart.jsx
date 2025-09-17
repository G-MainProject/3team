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
	simpleMode = false 
}) => {
	if (!stockData || stockData.length === 0 || !volumeData || volumeData.length === 0) {
		return (
			<div className="unified-chart-placeholder">차트 데이터가 없습니다.</div>
		);
	}

	// 데이터를 통합하여 하나의 배열로 만들기
	const combinedData = stockData.map((stockItem, index) => {
		const volumeItem = volumeData[index] || volumeData[volumeData.length - 1];
		return {
			...stockItem,
			volume: volumeItem ? volumeItem.volume : 0,
			date: stockItem.time || stockItem.date,
		};
	});

	// Y축 도메인 계산
	const priceValues = combinedData.map(d => d.price).filter(v => typeof v === 'number');
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
		if (name === 'price') {
			return [`₩${value.toLocaleString()}`, '주가'];
		}
		if (name === 'volume') {
			return [`${value.toLocaleString()}주`, '거래량'];
		}
		return [value, name];
	};

	// Y축 틱 포맷터
	const priceTickFormatter = (value) => `₩${value.toLocaleString()}`;
	const volumeTickFormatter = (value) => `${(value / 1000000).toFixed(1)}M`;

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
					
					{/* 거래량 Y축 */}
					<YAxis
						yAxisId="volume"
						orientation="right"
						domain={volumeDomain}
						tickFormatter={volumeTickFormatter}
						hide={simpleMode}
						tick={{ fontSize: 12 }}
					/>

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

					{/* 거래량 바 차트 */}
					<Bar
						yAxisId="volume"
						dataKey="volume"
						name="거래량"
						fill="#e3f2fd"
						opacity={0.7}
						radius={[2, 2, 0, 0]}
					/>

					{/* 실시간 주가 라인 차트 */}
					<Line
						yAxisId="price"
						type="monotone"
						dataKey="price"
						name="실시간 주가"
						stroke="#1976d2"
						strokeWidth={3}
						dot={{ fill: '#1976d2', strokeWidth: 2, r: 4 }}
						activeDot={{ r: 6, stroke: '#1976d2', strokeWidth: 2, fill: '#fff' }}
					/>
				</ComposedChart>
			</ResponsiveContainer>
		</div>
	);
};

export default UnifiedStockChart;

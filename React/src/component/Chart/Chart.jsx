import React from 'react';
import {
	LineChart,
	Line,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	Legend,
	ResponsiveContainer,
} from 'recharts';
import './Chart.css';

// 30일간의 주식 데이터를 생성합니다.
const generateDummyData = () => {
	const data = [];
	let price = 10000; // 시작 가격
	for (let i = 7; i > 0; i--) {
		const date = new Date();
		date.setDate(date.getDate() - i);
		const fluctuation = (Math.random() - 0.45) * 2000;
		price += fluctuation;
		price = Math.max(price, 5000); // 최소 가격
		data.push({
			date: date.toLocaleDateString('ko-KR', {
				month: '2-digit',
				day: '2-digit',
			}),
			price: Math.round(price),
		});
	}
	return data;
};

const Chart = () => {
	const data = generateDummyData();

	const dataMin = Math.min(...data.map((item) => item.price));
	const dataMax = Math.max(...data.map((item) => item.price));
	const padding = (dataMax - dataMin) * 0.1; // 10% padding

	// Y축 단위를 '원'으로 포맷팅하는 함수
	// const formatYAxis = (tickItem) => {
	// 	return `${tickItem.toLocaleString()}원`;
	// };

	return (
		<div className="chart-container">
			<ResponsiveContainer width="100%" height="100%">
				<LineChart
					data={data}
					margin={{
						top: 15,
						right: 15,
						left: 15,
						bottom: 10,
					}}
				>
					{/* 차트 그리드 라인 */}
					<CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
					{/* X축 (날짜) */}
					<XAxis dataKey="date" hide={true} />
					{/* Y축 (가격) */}
					<YAxis domain={[dataMin - padding, dataMax + padding]} hide={true} />

					{/* 마우스 호버 시 정보 표시 */}
					<Tooltip
						contentStyle={{
							backgroundColor: 'rgba(255, 255, 255, 0.8)',
							border: '1px solid #e9ecef',
							borderRadius: '6px',
							boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
						}}
						labelStyle={{ color: '#495057' }}
						itemStyle={{ color: '#007bff', fontWeight: 'bold' }}
						formatter={(value) => [`${value.toLocaleString()}원`, '가격']}
					/>
					{/* 범례 */}
					{/* <Legend wrapperStyle={{ color: '#495057' }} /> */}
					{/* 가격 라인 */}
					<Line
						type="monotone"
						dataKey="price"
						stroke="#007bff"
						strokeWidth={2}
						activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
						dot={{ r: 3, fill: '#007bff' }}
					/>
				</LineChart>
			</ResponsiveContainer>
		</div>
	);
};

export default Chart;

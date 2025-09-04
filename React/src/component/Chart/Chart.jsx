import React from 'react';
import {
	LineChart,
	Line,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	ResponsiveContainer,
} from 'recharts';
import './Chart.css';

// Generate detailed dummy stock data
const generateDummyData = (numPoints) => {
	const data = [];
	let lastPrice = 50000;
	const startDate = new Date();
	startDate.setDate(startDate.getDate() - numPoints);

	for (let i = 0; i < numPoints; i++) {
		const newDate = new Date(startDate);
		newDate.setDate(newDate.getDate() + i);

		// Simulate price fluctuation
		const fluctuation = (Math.random() - 0.48) * 2000;
		lastPrice += fluctuation;
		lastPrice = Math.max(lastPrice, 10000); // Ensure price doesn't go too low

		data.push({
			date: `${newDate.getMonth() + 1}/${newDate.getDate()}`,
			price: Math.round(lastPrice),
		});
	}
	return data;
};

const dummyData = generateDummyData(100); // Generate 100 data points for a detailed graph

const Chart = () => {
	// Formatter for Y-axis ticks (currency in Won)
	const formatYAxis = (tickItem) => {
		return `₩${tickItem.toLocaleString()}`;
	};

	// Custom Tooltip
	const CustomTooltip = ({ active, payload, label }) => {
		if (active && payload && payload.length) {
			return (
				<div className="custom-tooltip">
					<p className="label">{`날짜 : ${label}`}</p>
					<p className="intro">{`가격 : ₩${payload[0].value.toLocaleString()}`}</p>
				</div>
			);
		}
		return null;
	};

	return (
		<div className="chart-container">
			<h3 className="chart-title">주식 데이터 시뮬레이션</h3>
			<ResponsiveContainer width="100%" height={400}>
				<LineChart
					data={dummyData}
					margin={{
						top: 5,
						right: 30,
						left: 40,
						bottom: 5,
					}}
				>
					<CartesianGrid strokeDasharray="3 3" stroke="#555" />
					<XAxis dataKey="date" stroke="#ccc" />
					<YAxis
						stroke="#ccc"
						tickFormatter={formatYAxis}
						domain={['dataMin - 5000', 'dataMax + 5000']}
					/>
					<Tooltip content={<CustomTooltip />} />
					<Line
						type="monotone"
						dataKey="price"
						stroke="#2ecc71" // Green line for positive feel
						strokeWidth={2}
						dot={false}
						activeDot={{ r: 6 }}
					/>
				</LineChart>
			</ResponsiveContainer>
		</div>
	);
};

export default Chart;

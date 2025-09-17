import React from 'react';
import {
	XAxis,
	YAxis,
	ResponsiveContainer,
	ComposedChart,
	Bar,
	Tooltip,
} from 'recharts';
import './CandleStickChart.css';

const CustomCandle = (props) => {
	const { x, y, width, height, open, close, high, low } = props;
	const isRising = close >= open;
	const color = isRising ? '#ef4444' : '#3b82f6';
	const ratio = height > 0 ? height / (high - low) : 0;
	const bodyHeight = Math.max(1, Math.abs(open - close) * ratio);
	const bodyY = y + (high - Math.max(open, close)) * ratio;

	return (
		<g>
			<line
				x1={x + width / 2}
				y1={y}
				x2={x + width / 2}
				y2={y + height}
				stroke={color}
				strokeWidth={1}
			/>
			<rect x={x} y={bodyY} width={width} height={bodyHeight} fill={color} />
		</g>
	);
};

// [수정] 사용하지 않았던 simpleMode prop 다시 추가
const CandleStickChart = ({ data, simpleMode }) => {
	if (!data || data.length === 0) {
		return (
			<div className="chart-container-placeholder">데이터가 없습니다.</div>
		);
	}

	// [추가] 마우스 호버 시 보일 커스텀 툴팁 컴포넌트
	const CustomTooltip = ({ active, payload, label }) => {
		if (active && payload && payload.length) {
			const candleData = payload[0].payload;
			return (
				<div className="custom-tooltip">
					<p className="label">{`날짜: ${label}`}</p>
					{/* 거래량 캔들이므로 시가/종가 대신 전일/금일 거래량으로 표시 */}
					<p>{`전일 거래량: ${candleData.open.toLocaleString()}`}</p>
					<p>{`금일 거래량: ${candleData.close.toLocaleString()}`}</p>
				</div>
			);
		}
		return null;
	};

	const yDomain = [
		Math.min(...data.map((d) => d.low)) * 0.98,
		Math.max(...data.map((d) => d.high)) * 1.02,
	];

	return (
		<div className="chart-container">
			<ResponsiveContainer width="100%" height="100%">
				<ComposedChart
					data={data}
					margin={{
						top: 10,
						right: 5,
						left: 5,
						bottom: 0,
					}}
				>
					<XAxis dataKey="date" hide={true} />
					<YAxis domain={yDomain} hide={true} />

					{/* [추가] simpleMode가 아닐 때만 툴팁을 표시 */}
					{!simpleMode && <Tooltip content={<CustomTooltip />} />}

					<Bar
						dataKey={(d) => [d.low, d.high]}
						shape={<CustomCandle />}
						isAnimationActive={false}
						barSize={10}
					/>
				</ComposedChart>
			</ResponsiveContainer>
		</div>
	);
};

export default CandleStickChart;

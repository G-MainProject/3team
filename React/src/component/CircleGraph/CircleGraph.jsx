import React from 'react';
import {
	PieChart,
	Pie,
	Cell,
	Tooltip,
	Legend,
	ResponsiveContainer,
} from 'recharts';
import './CircleGraph.css';

const CustomLegend = ({ payload }) => {
	// Filter out legend items with type 'none' (from the white dot pie)
	const filteredPayload = payload.filter((entry) => entry.type !== 'none');

	return (
		<div className="sentiment-legend">
			{filteredPayload.map((entry, index) => {
				const sentimentName = entry.value;
				const sentimentValue = entry.payload.value;
				let sentimentClass = '';
				if (sentimentName === '긍정') sentimentClass = 'positive';
				else if (sentimentName === '부정') sentimentClass = 'negative';
				else if (sentimentName === '중립') sentimentClass = 'neutral';

				return (
					<div key={`item-${index}`} className="legend-item">
						<span
							className={`legend-color ${sentimentClass}`}
							style={{ backgroundColor: entry.color }}
						></span>
						<span>{`${sentimentName} ${sentimentValue}%`}</span>
					</div>
				);
			})}
		</div>
	);
};

const tooltipFormatter = (value, name) => {
	// Hides tooltip for the white dot (which has a numeric name/index)
	if (typeof name === 'number') {
		return null;
	}
	return [`${value}%`, name];
};

export default function CircleGraph({ data, colors }) {
	// data가 없거나 빈 배열인 경우 처리
	if (!data || !Array.isArray(data) || data.length === 0) {
		return (
			<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
				<p>데이터가 없습니다.</p>
			</div>
		);
	}

	return (
		<ResponsiveContainer width="100%" height="100%">
			<PieChart>
				<Pie
					data={data}
					cx="40%"
					cy="50%"
					labelLine={false}
					outerRadius="80%"
					fill="#8884d8"
					dataKey="value"
					// label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
					paddingAngle={0}
					stroke="none"
				>
					{data.map((entry, index) => (
						<Cell key={`cell-${index}`} fill={colors ? colors[index % colors.length] : '#8884d8'} />
					))}
				</Pie>
				<Pie
					data={[{ value: 1 }]}
					cx="40%"
					cy="50%"
					outerRadius={60}
					fill="white"
					stroke="none"
					legendType="none"
				/>
				<Tooltip formatter={tooltipFormatter} />
				<Legend
					content={<CustomLegend />}
					verticalAlign="middle"
					align="right"
					layout="vertical"
					wrapperStyle={{ right: 50 }}
				/>
			</PieChart>
		</ResponsiveContainer>
	);
}

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

export default function CircleGraph({ data, colors, onSegmentClick, selectedFilter }) {
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
					innerRadius="35%"
					fill="#8884d8"
					dataKey="value"
					// label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
					paddingAngle={0}
					stroke="none"
					onClick={onSegmentClick}
					style={{ cursor: onSegmentClick ? 'pointer' : 'default' }}
				>
					{data.map((entry, index) => {
						// 선택된 필터에 해당하는 섹션인지 확인
						const sentimentMap = {
							'긍정': 'positive',
							'부정': 'negative',
							'중립': 'neutral'
						};
						const isSelected = selectedFilter && selectedFilter !== 'all' && 
							sentimentMap[entry.name] === selectedFilter;
						
						// 색상 결정 로직
						const baseColor = colors ? colors[index % colors.length] : '#8884d8';
						let selectedColor;
						
						if (selectedFilter === 'all' || !selectedFilter) {
							// 전체 필터링일 때는 모든 섹션을 진한 색상으로
							selectedColor = baseColor;
						} else if (isSelected) {
							// 선택된 섹션은 진한 색상
							selectedColor = baseColor;
						} else {
							// 선택되지 않은 섹션은 연한 색상
							selectedColor = `${baseColor}60`;
						}
						
						return (
							<Cell 
								key={`cell-${index}`} 
								fill={selectedColor}
								style={{
									cursor: 'pointer',
									transition: 'all 0.3s ease'
								}}
							/>
						);
					})}
				</Pie>
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

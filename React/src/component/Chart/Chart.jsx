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

const Chart = ({
	data,
	series,
	xAxisKey,
	yAxisUnit,
	xAxisUnit,
	simpleMode = false,
	formatTooltipValue = true,
	yAxisFormatType = 'thousands', // 'billions' or 'thousands'
}) => {
	if (!data || data.length === 0 || !series || series.length === 0) {
		return (
			<div className="chart-container-placeholder">차트 데이터가 없습니다.</div>
		);
	}

	// Y-axis domain calculation
	let yDomain = ['auto', 'auto'];
	if (data.length > 0) {
		let dataMin = Infinity;
		let dataMax = -Infinity;

		series.forEach((s) => {
			data.forEach((d) => {
				const value = d[s.key];
				if (typeof value === 'number') {
					if (value < dataMin) dataMin = value;
					if (value > dataMax) dataMax = value;
				}
			});
		});

		if (dataMin !== Infinity && dataMax !== -Infinity) {
			const padding = (dataMax - dataMin) * 0.1;
			const finalMin = simpleMode
				? dataMin === dataMax
					? dataMin * 0.9
					: dataMin - padding
				: 0;
			const finalMax = dataMin === dataMax ? dataMax * 1.1 : dataMax + padding;
			yDomain = [Math.floor(finalMin), Math.ceil(finalMax)];
		}
	}

	// Axis formatters
	const xAxisTickFormatter = (tick) => `${tick}${xAxisUnit || ''}`;

	const yAxisTickFormatter = (tickItem) => {
		if (tickItem === 0) return '0';
		if (yAxisUnit === '원') {
			if (yAxisFormatType === 'billions') {
				return `${Math.round(tickItem / 1000000000).toLocaleString()}`;
			}
			return `${tickItem.toLocaleString()}`; // thousands formatting
		}
		if (yAxisUnit === '주') {
			return `${(tickItem / 1000000).toLocaleString()}M`;
		}
		return `${tickItem.toLocaleString()}`;
	};

	const tooltipValueFormatter = (value) => {
		if (yAxisFormatType === 'billions') {
			const valueInBillion = value / 1000000000;
			return `${Math.round(valueInBillion).toLocaleString()}`;
		}

		const formattedValue = formatTooltipValue
			? value.toLocaleString()
			: value.toString();
		return `${formattedValue}${yAxisUnit || ''}`;
	};

	return (
		<div className="chart-container">
			<ResponsiveContainer width="100%" height="100%">
				<LineChart
					data={data}
					margin={{
						top: 10,
						right: 20,
						left: 10,
						bottom: 10,
					}}
				>
					<CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
					<XAxis
						dataKey={xAxisKey}
						hide={simpleMode}
						tickFormatter={xAxisTickFormatter}
						type="category"
						allowDuplicatedCategory={false}
					/>
					<YAxis
						hide={simpleMode}
						tickFormatter={yAxisTickFormatter}
						domain={yDomain}
					/>
					<Tooltip
						formatter={tooltipValueFormatter}
						contentStyle={{
							backgroundColor: 'rgba(255, 255, 255, 0.9)',
							border: '1px solid #e9ecef',
							borderRadius: '6px',
							boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
						}}
						labelStyle={{ color: '#495057', fontWeight: 'bold' }}
						itemStyle={{ fontWeight: 'normal' }}
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
					{series &&
						series.map((s) => (
							<Line
								key={s.key}
								type="monotone"
								dataKey={s.key}
								name={s.name}
								stroke={s.color}
								strokeWidth={2}
								activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
								dot={true}
							/>
						))}
				</LineChart>
			</ResponsiveContainer>
		</div>
	);
};

export default Chart;
import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import './CircleGraph.css';

const data = [
	{ name: '긍정', value: 400 },
	{ name: '부정', value: 300 },
	{ name: '중립', value: 300 },
];

const COLORS = ['#0088FE', '#FF8042', '#00C49F'];

export default function CircleGraph() {
	return (
		<div className="circle-graph-container">
			<PieChart width={400} height={400}>
				<Pie
					data={data}
					cx={200}
					cy={200}
					labelLine={false}
					outerRadius={80}
					fill="#8884d8"
					dataKey="value"
					label={({ name, percent }) =>
						`${name} ${(percent * 100).toFixed(0)}%`
					}
				>
					{data.map((entry, index) => (
						<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
					))}
				</Pie>
				<Tooltip />
				<Legend />
			</PieChart>
		</div>
	);
}

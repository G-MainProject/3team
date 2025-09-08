import React from 'react';
import './MyWordCloud.css';
import { WordCloud } from '@isoterik/react-word-cloud';

export default function MyWordCloud() {
	const data11 = [
		{ text: 'React', value: 64 },
		{ text: '컴포넌트', value: 45 },
		{ text: '라이브러리', value: 80 },
		{ text: '구현', value: 70 },
		{ text: '스타일', value: 55 },
		{ text: '데이터', value: 72 },
		{ text: '시각화', value: 88 },
		{ text: '협업', value: 40 },
		{ text: '디자인', value: 60 },
		{ text: '프로젝트', value: 75 },
		{ text: '팀', value: 50 },
	];

	const colors = ['#3498db', '#2980b9', '#7f8c8d', '#95a5a6', '#2c3e50'];

	const minVal = Math.min(...data11.map((w) => w.value));
	const maxVal = Math.max(...data11.map((w) => w.value));
	const minFontSize = 20;
	const maxFontSize = 90;

	const scaleFontSize = (value) => {
		return (
			((value - minVal) / (maxVal - minVal)) * (maxFontSize - minFontSize) +
			minFontSize
		);
	};

	const options = {
		fill: (word, index) => colors[index % colors.length],
		font: "'Helvetica Neue', Helvetica, Arial, sans-serif",
		padding: 2, // Reduced padding
		enableTooltip: true,
		rotate: () => 0, // All words horizontal
		transition: 'all .5s ease',
		fontSize: (word) => scaleFontSize(word.value),
	};

	return (
		<div className="word-cloud-container">
			<h3 className="word-cloud-title">
				주요 키워드 분석
			</h3>
			<WordCloud
				words={data11}
				width={560} // Adjusted for padding
				height={350} // Adjusted for title and padding
				{...options}
			/>
		</div>
	);
}

import React, { useRef, useEffect, useState } from 'react';
import './MyWordCloud.css';
import { WordCloud } from '@isoterik/react-word-cloud';

export default function MyWordCloud({ data }) {
	const containerRef = useRef(null);
	const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

	useEffect(() => {
		const updateDimensions = () => {
			if (containerRef.current) {
				setDimensions({
					width: containerRef.current.offsetWidth,
					height: containerRef.current.offsetHeight,
				});
			}
		};

		updateDimensions();
		window.addEventListener('resize', updateDimensions);

		return () => {
			window.removeEventListener('resize', updateDimensions);
		};
	}, []);

	const wordCloudData = data;

	const colors = ['#3498db', '#2980b9', '#7f8c8d', '#95a5a6', '#2c3e50'];

	const minVal = Math.min(...wordCloudData.map((w) => w.value));
	const maxVal = Math.max(...wordCloudData.map((w) => w.value));
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
		<div className="word-cloud-container" ref={containerRef}>
			<h3 className="word-cloud-title">
				주요 키워드 분석
			</h3>
			{dimensions.width > 0 && dimensions.height > 0 && (
				<WordCloud
					words={wordCloudData}
					width={dimensions.width}
					height={dimensions.height - 40} // Adjust for title height and potential padding
					{...options}
				/>
			)}
		</div>
	);
}

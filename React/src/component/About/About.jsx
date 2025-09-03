import React from 'react';
import { useNavigate } from 'react-router-dom';
import './About.css';

export default function About() {
	const navigate = useNavigate();

	return (
		<div>
			<h2>소개 페이지입니다.</h2>
			<button onClick={() => navigate('/')}>홈 페이지</button>
		</div>
	);
}

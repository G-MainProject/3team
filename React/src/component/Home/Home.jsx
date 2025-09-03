import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Home.css';

export default function Home() {
	const navigate = useNavigate();

	function goToAbout() {
		navigate('/about');
	}
	return (
		<div>
			<h2>홈 페이지입니다.</h2>
			<button onClick={goToAbout}>소개 페이지</button>
		</div>
	);
}

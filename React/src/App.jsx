import React from 'react';
import './App.css';
// import { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';

import Home from './component/Home/Home.jsx';
import About from './component/About/About.jsx';
import Nav from './component/Nav/Nav.jsx';

function App() {
	return (
		<BrowserRouter>
			<Nav />
			<div style={{ marginBottom: '100px' }} />
			<Routes>
				<Route path="/" element={<Home />} />
				<Route path="/about" element={<About />} />
			</Routes>
		</BrowserRouter>
	);
}

export default App;

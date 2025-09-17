import React, { useState } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { PublicRoute, PrivateRoute } from './pages/Login/ProtectedRoute';

import Home from './pages/Home/Home.jsx';
import Login from './pages/Login/Login.jsx';
import Dashboard from './pages/Dashboard/Dashboard.jsx';
import Signup from './pages/Signup/Signup.jsx';
import Mypage from './pages/Mypage/Mypage.jsx';

function App() {
	const [selectedSymbol, setSelectedSymbol] = useState('005930'); // 기본값: 삼성전자
	return (
		<BrowserRouter>
			<AuthProvider>
				<Routes>
					<Route path="/" element={<Home />} />
					<Route path="/login" element={
						<PublicRoute>
							<Login />
						</PublicRoute>
					} />
					<Route path="/signup" element={
						<PublicRoute>
							<Signup />
						</PublicRoute>
					} />
					<Route path="/dashboard" element={
						<PrivateRoute>
							<Dashboard 
								selectedSymbol={selectedSymbol}
								onSymbolChange={setSelectedSymbol}
							/>
						</PrivateRoute>
					} />
					<Route path="/mypage" element={
						<PrivateRoute>
							<Mypage />
						</PrivateRoute>
					} />
				</Routes>
			</AuthProvider>
		</BrowserRouter>
	);
}

export default App;

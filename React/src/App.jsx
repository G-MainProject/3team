import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { StockProvider } from './contexts/StockContext';
import { WebSocketProvider } from './contexts/WebSocketContext.jsx';
import { PublicRoute, PrivateRoute } from './pages/Login/ProtectedRoute';

import Home from './pages/Home/Home.jsx';
import Login from './pages/Login/Login.jsx';
import Dashboard from './pages/Dashboard/Dashboard.jsx';
import Signup from './pages/Signup/Signup.jsx';
import Mypage from './pages/Mypage/Mypage.jsx';
import StockAnalysis from './pages/StockAnalysis/StockAnalysis.jsx';
import AIInsights from './pages/AIInsights/AIInsights.jsx';

function App() {
	return (
		<BrowserRouter>
			<AuthProvider>
				<NotificationProvider>
					<StockProvider>
						<WebSocketProvider>
						<Routes>
							<Route path="/" element={<Home />} />
							<Route
								path="/login"
								element={
									<PublicRoute>
										<Login />
									</PublicRoute>
								}
							/>
							<Route
								path="/signup"
								element={
									<PublicRoute>
										<Signup />
									</PublicRoute>
								}
							/>
							<Route
								path="/dashboard"
								element={
									<PrivateRoute>
										<Dashboard />
									</PrivateRoute>
								}
							/>
							<Route
								path="/mypage"
								element={
									<PrivateRoute>
										<Mypage />
									</PrivateRoute>
								}
							/>
							<Route
								path="/stock-analysis"
								element={
									<PrivateRoute>
										<StockAnalysis />
									</PrivateRoute>
								}
							/>
							<Route
								path="/ai-insights"
								element={
									<PrivateRoute>
										<AIInsights />
									</PrivateRoute>
								}
							/>
						</Routes>
						</WebSocketProvider>
					</StockProvider>
				</NotificationProvider>
			</AuthProvider>
		</BrowserRouter>
	);
}

export default App;

import React, { useState, useEffect, useRef } from 'react';
import './Sns.css';
import apiService from '../../services/api';
import { firestore } from '../../services/firebase';
import { useAuth } from '../../contexts/AuthContext';
import {
	collection,
	query,
	orderBy,
	onSnapshot,
	addDoc,
	deleteDoc,
	doc,
	serverTimestamp,
} from 'firebase/firestore';

const Sns = ({ selectedSymbol = '005930' }) => {
	// 기존 상태
	const [redditPosts, setRedditPosts] = useState([]);
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);
	const [error, setError] = useState(null);
	const [activePlatform, setActivePlatform] = useState('x');
	const [lastUpdated, setLastUpdated] = useState(null);
	const snsContainerRef = useRef(null);

	// 실시간 채팅용 상태
	const [messages, setMessages] = useState([]);
	const [newMessage, setNewMessage] = useState('');
	const messagesEndRef = useRef(null);
	const feedContainerRef = useRef(null);
	const { user: currentUser } = useAuth();

	// 사용자 정보 디버깅
	console.log('SNS 컴포넌트 - 현재 사용자 정보:', currentUser);

	// 관리자 여부 확인
	const isAdmin = currentUser && currentUser.role === 'ADMIN';

	// 높이 조정
	const adjustHeightToMatchSection = () => {
		if (snsContainerRef.current) {
			const sectionContainer = document.querySelector(
				'.dashboard-grid .section-container:nth-child(2)'
			);
			if (sectionContainer) {
				const sectionHeight = sectionContainer.offsetHeight;
				snsContainerRef.current.style.height = `${sectionHeight}px`;
			}
		}
	};

	// 주식 이름 매핑
	const getStockName = (symbol) => {
		const stockNames = {
			'005930': '삼성전자',
			'000660': 'SK하이닉스',
			'035420': 'NAVER',
			207940: '삼성바이오로직스',
			'006400': '삼성SDI',
		};
		return stockNames[symbol] || '알 수 없는 주식';
	};

	// 데이터 로딩 및 실시간 리스너 설정
	useEffect(() => {
		setLoading(true);
		setError(null);

		// 실시간 반응 (Firebase 활성화)
		if (activePlatform === 'x') {
			setLoading(true);
			setError(null);

			// Firebase가 초기화되지 않은 경우 처리
			if (!firestore) {
				console.error('Firebase가 초기화되지 않았습니다.');
				setError('Firebase 연결에 실패했습니다.');
				setLoading(false);
				return;
			}

			// 종목별 메시지 필터링을 위한 쿼리 수정
			const messagesRef = collection(firestore, 'messages');
			const q = query(
				messagesRef,
				orderBy('timestamp', 'asc') // 시간 오름차순으로 변경하여 채팅처럼 보이게 함
			);

			const unsubscribe = onSnapshot(
				q,
				(snapshot) => {
					const messagesData = snapshot.docs.map((doc) => ({
						id: doc.id,
						...doc.data(),
					}));
					setMessages(messagesData);
					setLoading(false);
				},
				(error) => {
					console.error('메시지 로드 실패:', error);
					// 이전 에러 메시지 "Missing or insufficient permissions"를 고려하여 규칙 확인을 유도
					if (error.code === 'permission-denied') {
						setError(
							'메시지를 불러올 권한이 없습니다. Firebase 규칙을 확인하세요.'
						);
					} else {
						setError('메시지를 불러올 수 없습니다.');
					}
					setLoading(false);
				}
			);

			return () => unsubscribe();
		}
		// Reddit 데이터
		else if (activePlatform === 'reddit') {
			const fetchRedditData = async () => {
				try {
					const data = await apiService.getSnsData(selectedSymbol);
					setRedditPosts(data.redditPosts || []);
					setLastUpdated(new Date());
				} catch (err) {
					console.error('Reddit 데이터 요청 오류:', err);
					setError('Reddit 데이터를 가져올 수 없습니다.');
					setRedditPosts([]);
				} finally {
					setLoading(false);
				}
			};

			fetchRedditData();
		}
	}, [activePlatform]);

	// 자동 새로고침 (Reddit 전용)
	useEffect(() => {
		if (activePlatform !== 'reddit') return;

		const interval = setInterval(() => {
			if (!loading) {
				const fetchRedditData = async () => {
					try {
						setRefreshing(true);
						const data = await apiService.getSnsData(selectedSymbol);
						setRedditPosts(data.redditPosts || []);
						setLastUpdated(new Date());
						setError(null);
					} catch (error) {
						console.error('Reddit 자동 새로고침 오류:', error);
					} finally {
						setRefreshing(false);
					}
				};
				fetchRedditData();
			}
		}, 60000); // 1분

		return () => clearInterval(interval);
	}, [selectedSymbol, loading, activePlatform]);

	// 높이 조정 관련 useEffect
	useEffect(() => {
		const timer = setTimeout(() => adjustHeightToMatchSection(), 100);
		const handleResize = () => adjustHeightToMatchSection();
		window.addEventListener('resize', handleResize);
		return () => {
			clearTimeout(timer);
			window.removeEventListener('resize', handleResize);
		};
	}, [loading]);

	// 메시지 자동 스크롤 (활성화)
	useEffect(() => {
		if (activePlatform === 'x' && feedContainerRef.current) {
			const { scrollHeight, clientHeight } = feedContainerRef.current;
			feedContainerRef.current.scrollTop = scrollHeight - clientHeight;
		}
	}, [messages, activePlatform]);

	// 메시지 삭제 핸들러
	const handleDeleteMessage = async (messageId) => {
		if (!isAdmin) {
			alert('관리자만 메시지를 삭제할 수 있습니다.');
			return;
		}

		if (!firestore) {
			alert('Firebase 연결에 실패했습니다.');
			return;
		}

		if (!window.confirm('정말로 이 메시지를 삭제하시겠습니까?')) {
			return;
		}

		try {
			await deleteDoc(doc(firestore, 'messages', messageId));
			console.log('메시지가 삭제되었습니다.');
		} catch (error) {
			console.error('메시지 삭제 실패:', error);
			alert('메시지 삭제에 실패했습니다.');
		}
	};

	// 메시지 전송 핸들러
	const handleSendMessage = async (e) => {
		e.preventDefault();
		if (newMessage.trim() === '') return;

		// 사용자 정보 확인
		if (!currentUser) {
			alert('로그인이 필요합니다. 먼저 로그인해주세요.');
			return;
		}

		if (!currentUser.id && !currentUser.uid) {
			console.error('사용자 ID가 없습니다:', currentUser);
			alert('사용자 정보가 올바르지 않습니다. 다시 로그인해주세요.');
			return;
		}

		// Firebase가 초기화되지 않은 경우 처리
		if (!firestore) {
			alert('Firebase 연결에 실패했습니다.');
			return;
		}

		try {
			await addDoc(collection(firestore, 'messages'), {
				text: newMessage.trim(),
				uid: currentUser.id || currentUser.uid, // Spring 백엔드는 id, Firebase는 uid
				displayName:
					currentUser.name ||
					currentUser.displayName ||
					currentUser.email ||
					'익명',
				timestamp: serverTimestamp(),
				// selectedSymbol: selectedSymbol,
			});
			setNewMessage('');
		} catch (error) {
			console.error('메시지 전송 실패:', error);
			console.error('현재 사용자 정보:', currentUser);
			alert('메시지 전송에 실패했습니다.');
		}
	};

	// 타임스탬프 포맷
	const formatTimestamp = (timestamp) => {
		if (!timestamp) return '';
		const messageDate = timestamp.toDate
			? timestamp.toDate()
			: new Date(timestamp);
		const now = new Date();

		const startOfNow = new Date(
			now.getFullYear(),
			now.getMonth(),
			now.getDate()
		);
		const startOfMessageDate = new Date(
			messageDate.getFullYear(),
			messageDate.getMonth(),
			messageDate.getDate()
		);

		const diffInMs = startOfNow.getTime() - startOfMessageDate.getTime();
		const diffInDays = Math.round(diffInMs / (1000 * 60 * 60 * 24));

		if (diffInDays === 0) {
			// 오늘
			return messageDate.toLocaleString('ko-KR', { timeStyle: 'short' });
		} else if (diffInDays > 0 && diffInDays <= 7) {
			// 1-7일 전
			return `${diffInDays}일 전`;
		} else {
			// 7일 이상 전 또는 미래의 날짜 (오차 방지)
			return messageDate.toLocaleString('ko-KR', {
				dateStyle: 'short',
				timeStyle: 'short',
			});
		}
	};

	// 30분 이상 지난 메시지인지 확인
	const isOldMessage = (timestamp) => {
		if (!timestamp) return false;
		const messageDate = timestamp.toDate
			? timestamp.toDate()
			: new Date(timestamp);
		const now = new Date();
		const diffInMinutes = (now.getTime() - messageDate.getTime()) / (1000 * 60);
		return diffInMinutes > 30;
	};

	const renderContent = () => {
		if (loading) {
			return (
				<div className="loading-container">
					<div className="loading-spinner"></div>
					<p>데이터를 불러오는 중...</p>
				</div>
			);
		}
		if (error) {
			return (
				<div className="error-message">
					<i className="fa-solid fa-exclamation-triangle"></i>
					<span>{error}</span>
				</div>
			);
		}

		// 실시간 반응 탭
		if (activePlatform === 'x') {
			return (
				<>
					<div className="social-feed" ref={feedContainerRef}>
						{messages.length > 0 ? (
							messages.map((msg) => (
								<div
									key={msg.id}
									className={`social-item message-item ${
										currentUser &&
										(msg.uid === currentUser.uid || msg.uid === currentUser.id)
											? 'my-message'
											: ''
									} ${isOldMessage(msg.timestamp) ? 'old-message' : ''}`}
								>
									<div className="social-header">
										<span className="social-author">{msg.displayName}</span>
										<div className="message-header-right">
											<span className="social-time">
												{formatTimestamp(msg.timestamp)}
											</span>
											{isAdmin && (
												<button
													className="message-delete-btn"
													onClick={() => handleDeleteMessage(msg.id)}
													title="메시지 삭제"
												>
													<i className="fas fa-trash"></i>
												</button>
											)}
										</div>
									</div>
									<div className="social-content">{msg.text}</div>
								</div>
							))
						) : (
							<div className="no-data">
								<p>아직 메시지가 없습니다. 첫 메시지를 남겨보세요!</p>
							</div>
						)}
						<div ref={messagesEndRef} />
					</div>
					<div className="message-input-form">
						<form onSubmit={handleSendMessage}>
							<input
								type="text"
								value={newMessage}
								onChange={(e) => setNewMessage(e.target.value)}
								placeholder={
									currentUser
										? '메시지를 입력하세요...'
										: '로그인 후 메시지를 남길 수 있습니다.'
								}
								disabled={!currentUser}
							/>
							<button
								type="submit"
								disabled={!currentUser || newMessage.trim() === ''}
							>
								<i className="fas fa-paper-plane"></i>
								전송
							</button>
						</form>
					</div>
				</>
			);
		}

		// Reddit 탭
		if (activePlatform === 'reddit') {
			return (
				<>
					<div className="social-feed">
						{redditPosts.length > 0 ? (
							redditPosts.map((item) => (
								<div
									key={item.id}
									className="social-item"
									onClick={() =>
										window.open(item.url, '_blank', 'noopener,noreferrer')
									}
								>
									<div className="social-header">
										<span className="social-author">{item.author}</span>
										<span className="social-time">{item.time}</span>
									</div>
									<div className="social-content">{item.content}</div>
									<div className="social-stats">
										<span className="social-likes">
											<i className="fa-regular fa-heart"></i>
											{item.likes}
										</span>
										<span className="social-engagement">
											<i className="fa-regular fa-comment"></i>
											{item.replies}
										</span>
										{item.url && (
											<span className="social-link">
												<i className="fa-solid fa-external-link-alt"></i>
											</span>
										)}
									</div>
								</div>
							))
						) : (
							<div className="no-data">
								<p>Reddit 데이터가 없습니다.</p>
							</div>
						)}
					</div>
					<div className="sns-status">
						{refreshing ? (
							<div className="refresh-indicator">
								<div className="refresh-spinner"></div>
								<span>갱신 중...</span>
							</div>
						) : lastUpdated ? (
							<div className="last-updated">
								<i className="fa-solid fa-clock"></i>
								<span>마지막 업데이트: {lastUpdated.toLocaleTimeString()}</span>
							</div>
						) : null}
					</div>
				</>
			);
		}
		return null;
	};

	return (
		<div className="sns-container" ref={snsContainerRef}>
			<div className="sns-content">
				<div className="sns-header">
					<h3>
						<span>{getStockName(selectedSymbol)}</span> 실시간 SNS 여론
					</h3>
					<div className="sns-header-right">
						<ul>
							<li>
								<button
									className={`social-btn ${
										activePlatform === 'x' ? 'active' : ''
									}`}
									onClick={() => setActivePlatform('x')}
								>
									SIGNAL
								</button>
							</li>
							<li>
								<button
									className={`social-btn ${
										activePlatform === 'reddit' ? 'active' : ''
									}`}
									onClick={() => setActivePlatform('reddit')}
								>
									Reddit
								</button>
							</li>
						</ul>
					</div>
				</div>
				{renderContent()}
			</div>
		</div>
	);
};

export default Sns;

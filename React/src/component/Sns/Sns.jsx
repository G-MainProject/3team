import React, { useState, useEffect, useRef, useCallback } from 'react';
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
	limit,
	getDocs,
	startAfter,
	where,
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
	const isPrepending = useRef(false); // 이전 메시지 로드 여부 플래그
	const { user: currentUser } = useAuth();

	// 무한 스크롤용 상태
	const [lastDoc, setLastDoc] = useState(null); // 페이지네이션 커서
	const [hasMore, setHasMore] = useState(true); // 더 불러올 메시지가 있는지
	const [loadingMore, setLoadingMore] = useState(false); // 추가 로딩 상태

	// 관리자 여부 확인
	const isAdmin = currentUser && currentUser.role === 'ADMIN';

	// 높이 조정
	const adjustHeightToMatchSection = () => {
		if (snsContainerRef.current) {
			const selectors = [
				'.dashboard-grid .section-container:first-child',
				'[class*="dashboard-grid"] [class*="section-container"]:first-child',
				'.dashboard-grid .section-container:nth-child(2)',
				'[class*="dashboard-grid"] [class*="section-container"]:nth-child(2)',
			];
			
			let sectionContainer = null;
			for (const selector of selectors) {
				sectionContainer = document.querySelector(selector);
				if (sectionContainer) break;
			}
			
			if (sectionContainer) {
				const sectionHeight = sectionContainer.offsetHeight;
				snsContainerRef.current.style.height = `${sectionHeight}px`;
			} else {
				snsContainerRef.current.style.height = '400px';
			}
		}
	};

	// 주식 이름 매핑
	const getStockName = (symbol) => {
		const stockNames = {
			'005930': '삼성전자',
			'000660': 'SK하이닉스',
			'035420': 'NAVER',
			'207940': '삼성바이오로직스',
			'006400': '삼성SDI',
		};
		return stockNames[symbol] || '알 수 없는 주식';
	};

	// 이전 메시지 로드 함수 (무한 스크롤)
	const loadMoreMessages = useCallback(async () => {
		if (loadingMore || !hasMore || !lastDoc) return;

		isPrepending.current = true; // 이전 메시지를 로드하고 있음을 표시
		setLoadingMore(true);
		try {
			const messagesRef = collection(firestore, 'messages');
			const moreMessagesQuery = query(
				messagesRef,
				orderBy('timestamp', 'desc'),
				startAfter(lastDoc),
				limit(30)
			);

			const snapshot = await getDocs(moreMessagesQuery);
			if (snapshot.empty) {
				setHasMore(false);
				setLoadingMore(false);
				return;
			}

			const newMessages = snapshot.docs
				.map((doc) => ({ id: doc.id, ...doc.data() }))
				.reverse();
			const lastVisible = snapshot.docs[snapshot.docs.length - 1];

			const feed = feedContainerRef.current;
			const oldScrollHeight = feed ? feed.scrollHeight : 0;

			setMessages((prev) => [...newMessages, ...prev]);
			setLastDoc(lastVisible);
			if (snapshot.docs.length < 30) {
				setHasMore(false);
			}

			if (feed) {
				requestAnimationFrame(() => {
					feed.scrollTop = feed.scrollHeight - oldScrollHeight;
				});
			}
		} catch (err) {
			console.error('이전 메시지 로드 실패:', err);
		} finally {
			setLoadingMore(false);
		}
	}, [loadingMore, hasMore, lastDoc]);

	// 스크롤 이벤트 리스너
	useEffect(() => {
		const feed = feedContainerRef.current;
		if (!feed || activePlatform !== 'x') return;

		const handleScroll = () => {
			if (feed.scrollTop === 0 && hasMore && !loadingMore) {
				loadMoreMessages();
			}
		};

		feed.addEventListener('scroll', handleScroll);
		return () => feed.removeEventListener('scroll', handleScroll);
	}, [activePlatform, hasMore, loadingMore, loadMoreMessages]);

	// 데이터 로딩 및 실시간 리스너 설정
	useEffect(() => {
		// Reddit 데이터 로딩
		if (activePlatform === 'reddit') {
			setLoading(true);
			setError(null);
			const fetchRedditData = async () => {
				try {
					console.log('🔄 Reddit 데이터 요청 중 - 심볼:', selectedSymbol);
					const data = await apiService.getSnsData(selectedSymbol);
					setRedditPosts(data.redditPosts || []);
					setLastUpdated(new Date());
					console.log('✅ Reddit 데이터 로드 완료:', data.redditPosts?.length || 0, '개');
				} catch (err) {
					console.error('Reddit 데이터 요청 오류:', err);
					setError('Reddit 데이터를 가져올 수 없습니다.');
					setRedditPosts([]);
				} finally {
					setLoading(false);
				}
			};
			fetchRedditData();
			return;
		}

		// 실시간 채팅 (X platform) 로직
		if (activePlatform === 'x') {
			let unsubscribe;
			const setupChat = async () => {
				setLoading(true);
				setError(null);
				setMessages([]);
				setLastDoc(null);
				setHasMore(true);
				setLoadingMore(false);

				if (!firestore) {
					setError('Firebase 연결에 실패했습니다.');
					setLoading(false);
					return;
				}

				try {
					const messagesRef = collection(firestore, 'messages');
					const initialQuery = query(messagesRef, orderBy('timestamp', 'desc'), limit(30));
					const snapshot = await getDocs(initialQuery);

					if (!snapshot.empty) {
						const initialMessages = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })).reverse();
						const lastVisible = snapshot.docs[snapshot.docs.length - 1];
						setMessages(initialMessages);
						setLastDoc(lastVisible);
						if (snapshot.docs.length < 30) setHasMore(false);
					} else {
						setHasMore(false);
					}
					setLoading(false);

					const latestTimestamp = snapshot.docs[0]?.data().timestamp || new Date();
					const newMessagesQuery = query(messagesRef, orderBy('timestamp', 'asc'), where('timestamp', '>', latestTimestamp));

					unsubscribe = onSnapshot(newMessagesQuery, (querySnapshot) => {
						querySnapshot.docChanges().forEach((change) => {
							if (change.type === 'added') {
								const newMessageData = { id: change.doc.id, ...change.doc.data() };
								setMessages(prev => prev.some(msg => msg.id === newMessageData.id) ? prev : [...prev, newMessageData]);
							}
						});
					}, (err) => {
						console.error('새 메시지 수신 실패:', err);
					});

				} catch (err) {
					console.error('메시지 로드 실패:', err);
					setError('메시지를 불러올 수 없습니다.');
					setLoading(false);
				}
			};
			setupChat();
			return () => {
				if (unsubscribe) unsubscribe();
			};
		}
	}, [activePlatform, selectedSymbol]);

	// 자동 새로고침 (Reddit 전용)
	useEffect(() => {
		if (activePlatform !== 'reddit') return;
		const interval = setInterval(() => {
			if (!loading) {
				const fetchRedditData = async () => {
					try {
						setRefreshing(true);
						console.log('🔄 Reddit 자동 새로고침 - 심볼:', selectedSymbol);
						const data = await apiService.getSnsData(selectedSymbol);
						setRedditPosts(data.redditPosts || []);
						setLastUpdated(new Date());
						setError(null);
						console.log('✅ Reddit 자동 새로고침 완료:', data.redditPosts?.length || 0, '개');
					} catch (error) {
						console.error('Reddit 자동 새로고침 오류:', error);
					} finally {
						setRefreshing(false);
					}
				};
				fetchRedditData();
			}
		}, 60000);
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

	// 컴포넌트 마운트 시 높이 조정
	useEffect(() => {
		const timer = setTimeout(() => adjustHeightToMatchSection(), 200);
		return () => clearTimeout(timer);
	}, []);

	// Intersection Observer를 사용한 높이 조정
	useEffect(() => {
		const currentRef = snsContainerRef.current;
		if (!currentRef) return;
		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						setTimeout(() => adjustHeightToMatchSection(), 100);
					}
				});
			},
			{ threshold: 0.1 }
		);
		observer.observe(currentRef);
		return () => {
			if (currentRef) {
				observer.unobserve(currentRef);
			}
		};
	}, []);

	// 메시지 자동 스크롤 (개선)
	useEffect(() => {
		// 이전 메시지를 로드하는 중에는 이 로직을 실행하지 않음
		if (isPrepending.current) {
			isPrepending.current = false; // 플래그 리셋
			return;
		}

		// activePlatform이 'x'일 때만 스크롤 로직 실행
		if (activePlatform === 'x' && feedContainerRef.current) {
			const feed = feedContainerRef.current;
			// 렌더링 후 스크롤을 맨 아래로 이동
			setTimeout(() => {
				feed.scrollTop = feed.scrollHeight;
			}, 50);
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
		if (!currentUser) {
			alert('로그인이 필요합니다. 먼저 로그인해주세요.');
			return;
		}
		if (!currentUser.id && !currentUser.uid) {
			alert('사용자 정보가 올바르지 않습니다. 다시 로그인해주세요.');
			return;
		}
		if (!firestore) {
			alert('Firebase 연결에 실패했습니다.');
			return;
		}
		try {
			await addDoc(collection(firestore, 'messages'), {
				text: newMessage.trim(),
				uid: currentUser.id || currentUser.uid,
				displayName: currentUser.name || currentUser.displayName || currentUser.email || '익명',
				timestamp: serverTimestamp(),
			});
			setNewMessage('');
		} catch (error) {
			console.error('메시지 전송 실패:', error);
			alert('메시지 전송에 실패했습니다.');
		}
	};

	// 타임스탬프 포맷
	const formatTimestamp = (timestamp) => {
		if (!timestamp) return '';
		const messageDate = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
		const now = new Date();
		const startOfNow = new Date(now.getFullYear(), now.getMonth(), now.getDate());
		const startOfMessageDate = new Date(messageDate.getFullYear(), messageDate.getMonth(), messageDate.getDate());
		const diffInMs = startOfNow.getTime() - startOfMessageDate.getTime();
		const diffInDays = Math.round(diffInMs / (1000 * 60 * 60 * 24));

		if (diffInDays === 0) {
			return messageDate.toLocaleString('ko-KR', { timeStyle: 'short' });
		} else if (diffInDays > 0 && diffInDays <= 7) {
			return `${diffInDays}일 전`;
		} else {
			return messageDate.toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' });
		}
	};

	// 24시간 이상 지난 메시지인지 확인
	const isOldMessage = (timestamp) => {
		if (!timestamp) return false;
		const messageDate = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
		const now = new Date();
		const diffInHours = (now.getTime() - messageDate.getTime()) / (1000 * 60 * 60);
		return diffInHours > 24;
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

		// 실시간 반응 탭 (카카오톡 스타일)
		if (activePlatform === 'x') {
			return (
				<>
					<div className="social-feed signal-feed" ref={feedContainerRef}>
						{loadingMore && (
							<div className="loading-container" style={{ height: '50px' }}>
								<div className="loading-spinner"></div>
							</div>
						)}
						{messages.length > 0 ? (
							messages.map((msg, index) => {
								const isMyMessage = currentUser && (msg.uid === currentUser.uid || msg.uid === currentUser.id);
								const isLastMessage = index === messages.length - 1;
								
								return (
									<div
										key={msg.id}
										className={`message-item ${isMyMessage ? 'my-message' : ''} ${isOldMessage(msg.timestamp) ? 'old-message' : ''} ${isLastMessage ? 'last-message' : ''}`}
									>
										<div className="message-bubble">
											{!isMyMessage && (
												<div className="message-header">
													<span className="message-author">{msg.displayName}</span>
													<div className="message-header-right">
														<span className="message-time">{formatTimestamp(msg.timestamp)}</span>
														{isAdmin && (
															<button className="message-delete-btn" onClick={() => handleDeleteMessage(msg.id)} title="메시지 삭제">
																<i className="fas fa-trash"></i>
															</button>
														)}
													</div>
												</div>
											)}
											<div className="message-text">{msg.text}</div>
											{isMyMessage && (
												<div className="message-header">
													<div className="message-header-right">
														<span className="message-time">{formatTimestamp(msg.timestamp)}</span>
														{isAdmin && (
															<button className="message-delete-btn" onClick={() => handleDeleteMessage(msg.id)} title="메시지 삭제">
																<i className="fas fa-trash"></i>
															</button>
														)}
													</div>
												</div>
											)}
										</div>
									</div>
								);
							})
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
								placeholder={currentUser ? '메시지를 입력하세요...' : '로그인 후 메시지를 남길 수 있습니다.'}
								disabled={!currentUser}
							/>
							<button type="submit" disabled={!currentUser || newMessage.trim() === ''}>
								<i className="fas fa-paper-plane"></i>
								전송
							</button>
						</form>
					</div>
				</>
			);
		}

		// Reddit 탭 (기존 카드 스타일 유지)
		if (activePlatform === 'reddit') {
			return (
				<>
					<div className="social-feed">
						{redditPosts.length > 0 ? (
							redditPosts.map((item) => (
								<div
									key={item.id}
									className="social-item reddit-item"
									onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}
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
						{activePlatform === 'x' ? (
							<>
								<span>SIGNAL</span> 실시간 반응
							</>
						) : (
							<>
								<span>{getStockName(selectedSymbol)}</span> 실시간 SNS 반응
							</>
						)}
					</h3>
					<div className="sns-header-right">
						<ul>
							<li>
								<button
									className={`social-btn ${activePlatform === 'x' ? 'active' : ''}`}
									onClick={() => setActivePlatform('x')}
								>
									SIGNAL
								</button>
							</li>
							<li>
								<button
									className={`social-btn ${activePlatform === 'reddit' ? 'active' : ''}`}
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

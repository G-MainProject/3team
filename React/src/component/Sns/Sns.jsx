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
  const { user: currentUser } = useAuth();

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
      '207940': '삼성바이오로직스',
      '006400': '삼성SDI',
    };
    return stockNames[symbol] || '알 수 없는 주식';
  };

  // 데이터 로딩 및 실시간 리스너 설정
  useEffect(() => {
    setLoading(true);
    setError(null);

    // 실시간 반응 (Firebase)
    if (activePlatform === 'x') {
      if (!selectedSymbol) return;

      const messagesCol = collection(
        firestore,
        'stocks',
        selectedSymbol,
        'messages'
      );
      const q = query(messagesCol, orderBy('timestamp', 'asc'));

      const unsubscribe = onSnapshot(
        q,
        (querySnapshot) => {
          const msgs = [];
          querySnapshot.forEach((doc) => {
            msgs.push({ id: doc.id, ...doc.data() });
          });
          setMessages(msgs);
          setLoading(false);
        },
        (err) => {
          console.error('메시지 수신 오류:', err);
          setError('메시지를 불러오는 중 오류가 발생했습니다.');
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
  }, [selectedSymbol, activePlatform]);

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

  // 메시지 자동 스크롤
  useEffect(() => {
    if (activePlatform === 'x') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, activePlatform]);


  // 메시지 전송 핸들러
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (newMessage.trim() === '') return;
    if (!currentUser) {
      alert('로그인이 필요합니다.');
      return;
    }

    const messagesCol = collection(firestore, 'stocks', selectedSymbol, 'messages');
    try {
      await addDoc(messagesCol, {
        text: newMessage,
        timestamp: serverTimestamp(),
        uid: currentUser.username, // username을 uid로 사용
        displayName: currentUser.name || currentUser.username || '익명', // name 또는 username을 표시 이름으로 사용
      });
      setNewMessage('');
    } catch (err) {
      console.error('메시지 전송 오류:', err);
      setError('메시지 전송에 실패했습니다.');
    }
  };

  // 타임스탬프 포맷
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = timestamp.toDate();
    return date.toLocaleString('ko-KR', { timeStyle: 'short' });
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className='loading-container'>
          <div className='loading-spinner'></div>
          <p>데이터를 불러오는 중...</p>
        </div>
      );
    }
    if (error) {
      return (
        <div className='error-message'>
          <i className="fa-solid fa-exclamation-triangle"></i>
          <span>{error}</span>
        </div>
      );
    }

    // 실시간 반응 탭
    if (activePlatform === 'x') {
      return (
        <>
          <div className='social-feed'>
            {messages.length > 0 ? (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`social-item message-item ${currentUser && msg.uid === currentUser.username ? 'my-message' : ''}`}>
                  <div className='social-header'>
                    <span className='social-author'>{msg.displayName}</span>
                    <span className='social-time'>
                      {formatTimestamp(msg.timestamp)}
                    </span>
                  </div>
                  <div className='social-content'>{msg.text}</div>
                </div>
              ))
            ) : (
              <div className='no-data'>
                <p>아직 메시지가 없습니다. 첫 메시지를 남겨보세요!</p>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className='message-input-form'>
            <form onSubmit={handleSendMessage}>
              <input
                type='text'
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder={currentUser ? '메시지를 입력하세요...' : '로그인 후 메시지를 남길 수 있습니다.'}
                disabled={!currentUser}
              />
              <button type='submit' disabled={!currentUser || newMessage.trim() === ''}>
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
          <div className='social-feed'>
            {redditPosts.length > 0 ? (
              redditPosts.map(item => (
                <div 
                  key={item.id} 
                  className='social-item'
                  onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}>
                  <div className='social-header'>
                    <span className='social-author'>{item.author}</span>
                    <span className='social-time'>{item.time}</span>
                  </div>
                  <div className='social-content'>{item.content}</div>
                  <div className='social-stats'>
                    <span className='social-likes'><i className="fa-regular fa-heart"></i>{item.likes}</span>
                    <span className='social-engagement'><i className="fa-regular fa-comment"></i>{item.replies}</span>
                    {item.url && <span className='social-link'><i className="fa-solid fa-external-link-alt"></i></span>}
                  </div>
                </div>
              ))
            ) : (
              <div className='no-data'><p>Reddit 데이터가 없습니다.</p></div>
            )}
          </div>
          <div className='sns-status'>
            {refreshing ? (
              <div className='refresh-indicator'>
                <div className='refresh-spinner'></div><span>갱신 중...</span>
              </div>
            ) : lastUpdated ? (
              <div className='last-updated'>
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
    <div className='sns-container' ref={snsContainerRef}>
      <div className='sns-content'>
        <div className='sns-header'>
          <h3><span>{getStockName(selectedSymbol)}</span> 실시간 여론</h3>
          <div className='sns-header-right'>
            <ul>
              <li>
                <button 
                  className={`social-btn ${activePlatform === 'x' ? 'active' : ''}`}
                  onClick={() => setActivePlatform('x')}>
                  실시간 반응
                </button>
              </li>
              <li>
                <button 
                  className={`social-btn ${activePlatform === 'reddit' ? 'active' : ''}`}
                  onClick={() => setActivePlatform('reddit')}>
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
}

export default Sns;

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import './TopNav.css'
import maleAvatar from '../../assets/images/male.jpg'
import femaleAvatar from '../../assets/images/female.jpg'
import { useAuth } from '../../contexts/AuthContext'
import { useNotification } from '../../contexts/NotificationContext'

const TopNav = ({ selectedSymbol, onSymbolChange, topNavStocks, topNavLoading, onStockSelect }) => {
  const { user, logout } = useAuth()
  const { notificationCount, notificationHistory, clearNotifications, setNotificationCount, setNotificationHistory } = useNotification()
  const [topStocks, setTopStocks] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedStock, setSelectedStock] = useState(selectedSymbol || '005930') // props에서 받은 값 사용
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)
  const [showNotificationDropdown, setShowNotificationDropdown] = useState(false)
  const [previousTopStock, setPreviousTopStock] = useState(null)
  // refreshing은 props로 받아서 사용
  const dropdownRef = useRef(null)
  const navigate = useNavigate()
  
  // 사용자 성별 정보 가져오기
  const getUserGender = () => {
    if (!user) return 'male'; // 기본값
    // 서버에서 오는 성별 값: MALE, FEMALE, OTHER
    return user.gender === 'FEMALE' ? 'female' : 'male';
  }
  
  // 주요 주식 심볼 목록
  const stockSymbols = useMemo(() => [
    { symbol: '005930', name: '삼성전자' },
    { symbol: '000660', name: 'SK하이닉스' },
    { symbol: '035420', name: 'NAVER' },
    { symbol: '207940', name: '삼성바이오로직스' },
    { symbol: '006400', name: '삼성SDI' }
  ], [])

  // fetchRealStockData 함수 제거 - Dashboard에서 데이터를 받아서 사용

  // Dashboard에서 전달받은 데이터만 사용 (완전 동기화)
  useEffect(() => {
    if (topNavStocks && topNavStocks.length > 0) {
      // console.log('📡 TopNav props 데이터 받음:', topNavStocks);
      
      // Dashboard의 데이터가 있으면 사용
      setIsLoading(topNavLoading)
      
      // 애니메이션 시작
      setIsAnimating(true)
      
      // 약간의 지연 후 데이터 업데이트
      setTimeout(() => {
        const newTopStocks = topNavStocks.slice(0, 5)
        
        // 순위 변경 감지
        if (previousTopStock && newTopStocks[0] && previousTopStock.symbol !== newTopStocks[0].symbol) {
          console.log('🔔 순위 변경 감지:', previousTopStock.name, '→', newTopStocks[0].name);
          
          // 이전 1위의 현재 순위 찾기
          const previousRank = newTopStocks.findIndex(stock => stock.symbol === previousTopStock.symbol) + 1
          const currentRank = 1
          
          // 알림 히스토리에 추가
          const newNotification = {
            previousStock: {
              name: previousTopStock.name,
              rank: previousRank,
              changePercent: previousTopStock.changePercent
            },
            currentStock: {
              name: newTopStocks[0].name,
              rank: currentRank,
              changePercent: newTopStocks[0].changePercent
            },
            type: 'rank_change'
          }
          setNotificationHistory(prev => [newNotification, ...prev.slice(0, 9)]) // 최대 10개 유지
          
          // 드롭다운이 닫혀있을 때만 카운트 증가
          if (!showNotificationDropdown) {
            setNotificationCount(prev => prev + 1)
          }
        }
        
        setTopStocks(newTopStocks)
        setPreviousTopStock(newTopStocks[0]) // 현재 1위 저장
        setIsLoading(false)
        // console.log('✅ TopNav 데이터 동기화 완료 - Dashboard와 동일한 데이터 사용');
        
        // 애니메이션 종료
        setTimeout(() => {
          setIsAnimating(false)
        }, 300)
      }, 150)
    }
  }, [topNavStocks, topNavLoading])

  // selectedSymbol이 변경될 때 selectedStock 동기화
  useEffect(() => {
    if (selectedSymbol) {
      setSelectedStock(selectedSymbol)
    }
  }, [selectedSymbol])

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleUserClick = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleMyPage = () => {
    setIsDropdownOpen(false);
    navigate('/mypage');
  };

  const handleLogout = () => {
    logout();
    setIsDropdownOpen(false);
    alert('로그아웃 되었습니다.');
    // Dashboard에서 로그아웃 시 홈페이지로 이동
    window.location.href = '/';
  };

  // 주식 클릭 핸들러
  const handleStockClick = (stock) => {
    setSelectedStock(stock.symbol)
    if (onSymbolChange) {
      onSymbolChange(stock.symbol)
    }
    // Dashboard로 이동하면서 해당 주식 선택
    navigate('/dashboard', { state: { selectedSymbol: stock.symbol } })
  }

  // 벨 버튼 클릭 핸들러
  const handleBellClick = () => {
    setShowNotificationDropdown(!showNotificationDropdown)
    if (notificationCount > 0) {
      clearNotifications() // 알림 확인 시 카운트 리셋
    }
  }

  // 알림에서 주식 클릭 핸들러
  const handleNotificationStockClick = (stockName) => {
    // 주식 이름으로 심볼 찾기
    const stock = topStocks.find(s => s.name === stockName)
    if (stock && onStockSelect) {
      onStockSelect(stock.symbol)
      setShowNotificationDropdown(false) // 알림 드롭다운 닫기
    }
  }

  return (
    <div className='top-nav-container'>
        {/* 주식 변동폭 순위 */}
        <div className='progress-indicator'>
          {isLoading ? (
            <div className="stock-loading">실시간 주식 데이터 로딩 중...</div>
          ) : topStocks.length > 0 ? (
            <div className="stock-list-container">
              <div className="stock-items">
                {topStocks.map((stock, index) => (
                  <div key={stock.symbol} className={`stock-item ${isAnimating ? 'animating' : ''}`}>
                    <div 
                      className={`stock-circle ${stock.symbol === selectedStock ? 'active' : ''}`}
                      onClick={() => handleStockClick(stock)}
                      title={`${stock.name} - ${stock.currentPrice?.toLocaleString()}원 (${stock.changePercent >= 0 ? '+' : ''}${stock.changePercent?.toFixed(2)}%)`}
                    >
                      {index + 1}
                    </div>
                    <span className='stock-label'>{stock.name}</span>
                    <span className={`stock-change ${stock.changePercent >= 0 ? 'positive' : 'negative'}`}>
                      {stock.changePercent >= 0 ? '+' : ''}{stock.changePercent?.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            // 기본값 표시 (데이터가 없을 때)
            stockSymbols.slice(0, 5).map((stock, index) => (
              <div key={stock.symbol} className="stock-item">
                <div 
                  className={`stock-circle ${stock.symbol === selectedStock ? 'active' : ''}`}
                  onClick={() => handleStockClick(stock)}
                  title={`${stock.name} - 데이터 없음`}
                >
                  {index + 1}
                </div>
                <span className='stock-label'>{stock.name}</span>
                <span className="stock-change">--%</span>
              </div>
            ))
          )}
        </div>

        <button className='top-nav-darkmode'>
            <i className="fa-regular fa-moon fa-flip-horizontal"></i>
        </button>

        <div className="notification-container">
          <button className='top-nav-bell' onClick={handleBellClick}>
            <i className="fa-regular fa-bell"></i>
            {notificationCount > 0 && (
              <span className="notification-badge">{notificationCount}</span>
            )}
          </button>
          
          {/* 알림 드롭다운 */}
          <div className={`notification-dropdown ${showNotificationDropdown ? 'open' : 'closed'}`}>
              <div className="notification-header">
                <h4>알림</h4>
                <button 
                  onClick={() => setShowNotificationDropdown(false)}
                  className="notification-close-btn"
                >
                  <i className="fas fa-times"></i>
                </button>
              </div>
              <div className="notification-list">
                {notificationHistory.length > 0 ? (
                  notificationHistory.map(notification => (
                    <div key={notification.id} className="notification-item">
                      <div className="notification-content">
                        <div className="rank-change-icon">
                          <i className="fas fa-exchange-alt"></i>
                        </div>
                        <div className="rank-change-details">
                          <div className="rank-change-title">
                            <span className="rank-badge rank-1">1위</span>
                            <span 
                              className="stock-name clickable" 
                              onClick={() => handleNotificationStockClick(notification.currentStock.name)}
                              title="클릭하여 해당 주가 보기"
                            >
                              {notification.currentStock.name}
                            </span>
                            <span className={`change-percent ${notification.currentStock.changePercent >= 0 ? 'positive' : 'negative'}`}>
                              {notification.currentStock.changePercent >= 0 ? '+' : ''}{notification.currentStock.changePercent.toFixed(2)}%
                            </span>
                          </div>
                          <div className="rank-change-subtitle">
                            <span className="previous-rank">
                              이전 1위: <strong 
                                className="clickable" 
                                onClick={() => handleNotificationStockClick(notification.previousStock.name)}
                                title="클릭하여 해당 주가 보기"
                              >
                                {notification.previousStock.name}
                              </strong> 
                              <span className="rank-number">({notification.previousStock.rank}위)</span>
                            </span>
                          </div>
                          <span className="notification-time">{notification.time}</span>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="notification-empty">
                    <i className="fas fa-bell-slash"></i>
                    <p>새로운 알림이 없습니다</p>
                  </div>
                )}
              </div>
            </div>
        </div>

        <div className="top-nav-user-container" ref={dropdownRef}>
          <button className="top-nav-user" onClick={handleUserClick}>
              <img src={getUserGender() === 'female' ? femaleAvatar : maleAvatar} alt="avatar" />
              <ul>
                  <li>Welcome back,</li>
                  <li>{user?.name || user?.email || '???'}</li>
              </ul>
              <i className={`fa-solid fa-chevron-down ${isDropdownOpen ? 'rotated' : ''}`}></i>
          </button>
          
          <div className={`top-nav-dropdown ${isDropdownOpen ? 'open' : 'closed'}`}>
            <button className="dropdown-item" onClick={handleMyPage}>
              <i className="fa-solid fa-user"></i>
              <span>내 정보</span>
            </button>
            <button className="dropdown-item" onClick={handleLogout}>
              <i className="fa-solid fa-arrow-right-from-bracket"></i>
              <span>로그아웃</span>
            </button>
          </div>
        </div>
    </div>
  )
}

export default TopNav

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './TopNav.css';
import maleAvatar from '../../assets/images/male.jpg';
import femaleAvatar from '../../assets/images/female.jpg';
import { useAuth } from '../../contexts/AuthContext';
import { useNotification } from '../../contexts/NotificationContext';
import { useStock } from '../../hooks/useStock';
import { useRealtimeStockData } from '../../hooks/useRealtimeStockData';

const TopNav = () => {
  const { user, logout } = useAuth();
  const {
    notificationCount,
    notificationHistory,
    clearNotifications,
    setNotificationCount,
    setNotificationHistory,
  } = useNotification();
  const { stocks, selectedStock, setSelectedStockByCode, loading: stockLoading } = useStock();

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showNotificationDropdown, setShowNotificationDropdown] = useState(false);
  const previousTopStockRef = useRef(null);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // 상위 5개 주식 선택 (초기에는 랜덤하게 5개 선택)
  const top5Stocks = useMemo(() => {
    if (!stocks || stocks.length === 0) return [];
    return [...stocks].slice(0, 5); // 일단 처음 5개 선택
  }, [stocks]);

  // 각 주식의 실시간 데이터 가져오기
  const stock1Data = useRealtimeStockData(top5Stocks[0]?.stockCode || '');
  const stock2Data = useRealtimeStockData(top5Stocks[1]?.stockCode || '');
  const stock3Data = useRealtimeStockData(top5Stocks[2]?.stockCode || '');
  const stock4Data = useRealtimeStockData(top5Stocks[3]?.stockCode || '');
  const stock5Data = useRealtimeStockData(top5Stocks[4]?.stockCode || '');

  // 실시간 데이터가 포함된 상위 5개 주식 (실시간 데이터로 정렬)
  const topStocks = useMemo(() => {
    if (!top5Stocks || top5Stocks.length === 0) return [];
    
    const realtimeDataArray = [stock1Data, stock2Data, stock3Data, stock4Data, stock5Data];
    
    // 실시간 데이터로 업데이트된 주식 목록 생성
    const updatedStocks = top5Stocks.map((stock, index) => {
      const realtimeData = realtimeDataArray[index];
      if (realtimeData?.summaryData) {
        return {
          ...stock,
          currentPrice: realtimeData.summaryData.currentPrice || stock.currentPrice,
          changePercent: realtimeData.summaryData.changePercent || stock.changePercent,
          volume: realtimeData.summaryData.volume || stock.volume,
          marketCap: realtimeData.summaryData.marketCap || stock.marketCap,
        };
      }
      return stock;
    });
    
    // 등락폭 절댓값 기준으로 정렬 (실시간 데이터가 있는 것만)
    const sortedStocks = [...updatedStocks].sort((a, b) => {
      const aChange = Math.abs(a.changePercent || 0);
      const bChange = Math.abs(b.changePercent || 0);
      return bChange - aChange;
    });
    
    return sortedStocks;
  }, [top5Stocks, stock1Data, stock2Data, stock3Data, stock4Data, stock5Data]);

  const getUserGender = () => {
    if (!user) return 'male';
    return user.gender === 'FEMALE' ? 'female' : 'male';
  };


  // 순위 변경 감지 및 알림 처리 (실제 순위 변경만 감지)
  const handleRankChange = useCallback((currentTopStock, topStocks) => {
    const prevStock = previousTopStockRef.current;
    
    // 이전 주식이 있고, 실제로 다른 주식이 1등이 된 경우에만 처리
    if (prevStock && prevStock.stockCode !== currentTopStock.stockCode) {
      const previousRank = topStocks.findIndex(stock => stock.stockCode === prevStock.stockCode) + 1;
      const currentRank = 1;

      // 애니메이션 시작
      setIsAnimating(true);
      setTimeout(() => {
        setIsAnimating(false);
      }, 300);

      // 알림 생성
      const newNotification = {
        id: Date.now(),
        previousStock: {
          name: prevStock.stockName,
          rank: previousRank,
          changePercent: prevStock.changePercent,
        },
        currentStock: {
          name: currentTopStock.stockName,
          rank: currentRank,
          changePercent: currentTopStock.changePercent,
        },
        type: 'rank_change',
      };
      
      // setNotificationHistory 호출
      if (setNotificationHistory) {
        setNotificationHistory(prev => [newNotification, ...prev.slice(0, 9)]);
      }

      if (!showNotificationDropdown && setNotificationCount) {
        setNotificationCount(prev => prev + 1);
      }
    }
    
    // 현재 주식을 이전 주식으로 저장
    previousTopStockRef.current = currentTopStock;
  }, [setNotificationCount, setNotificationHistory, showNotificationDropdown]);

  // topStocks를 ref로 저장하여 최신 값 참조
  const topStocksRef = useRef(topStocks);
  topStocksRef.current = topStocks;

  useEffect(() => {
    if (topStocks && topStocks.length > 0) {
      const currentTopStock = topStocks[0];
      handleRankChange(currentTopStock, topStocksRef.current);
      
      // 새로고침 시 실시간 데이터로 정렬된 1등 주식 자동 선택 (한 번만 실행)
      if (!selectedStock) {
        setSelectedStockByCode(currentTopStock.stockCode);
      }
    }
  }, [topStocks[0]?.stockCode, handleRankChange]); // eslint-disable-line react-hooks/exhaustive-deps

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
    window.location.href = '/';
  };

  const handleStockClick = (stock) => {
    setSelectedStockByCode(stock.stockCode);
    navigate(location.pathname);
  };

  const handleBellClick = () => {
    setShowNotificationDropdown(!showNotificationDropdown);
    if (notificationCount > 0) {
      clearNotifications();
    }
  };

  const handleNotificationStockClick = (stockName) => {
    const stock = topStocks.find(s => s.stockName === stockName);
    if (stock) {
        setSelectedStockByCode(stock.stockCode);
        setShowNotificationDropdown(false);
    }
  };

  return (
    <div className='top-nav-container'>
        <div className='progress-indicator'>
          {stockLoading ? (
            <div className="stock-loading">실시간 주식 데이터 로딩 중...</div>
          ) : topStocks.length > 0 ? (
            <div className="stock-list-container">
              <div className="stock-items">
                {topStocks.map((stock, index) => (
                  <div key={stock.stockCode} className={`stock-item ${isAnimating ? 'animating' : ''}`}>
                    <div 
                      className={`stock-circle ${stock.stockCode === selectedStock?.stockCode ? 'active' : ''}`}
                      onClick={() => handleStockClick(stock)}
                      title={`${stock.stockName} - ${stock.currentPrice?.toLocaleString()}원 (${stock.changePercent >= 0 ? '+' : ''}${stock.changePercent?.toFixed(2)}%)`}
                    >
                      {index + 1}
                    </div>
                    <span className='stock-label'>{stock.stockName}</span>
                    <span className={`stock-change ${stock.changePercent >= 0 ? 'positive' : 'negative'}`}>
                      {stock.changePercent >= 0 ? '+' : ''}{stock.changePercent?.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="stock-loading">주식 데이터가 없습니다.</div>
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
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './TopNav.css';
import maleAvatar from '../../assets/images/male.jpg';
import femaleAvatar from '../../assets/images/female.jpg';
import { useAuth } from '../../contexts/AuthContext';
import { useNotification } from '../../contexts/NotificationContext';
import { useStock } from '../../hooks/useStock';

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
  const [previousTopStock, setPreviousTopStock] = useState(null);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Memoize the sorted stock list for the TopNav
  const topNavStocks = useMemo(() => {
    if (!stocks) return [];
    return [...stocks].sort((a, b) => Math.abs(b.changePercent || 0) - Math.abs(a.changePercent || 0));
  }, [stocks]);

  const getUserGender = () => {
    if (!user) return 'male';
    return user.gender === 'FEMALE' ? 'female' : 'male';
  };

  useEffect(() => {
    if (topNavStocks && topNavStocks.length > 0) {
      setIsAnimating(true);
      setTimeout(() => {
        const newTopStocks = topNavStocks.slice(0, 5);

        if (previousTopStock && newTopStocks[0] && previousTopStock.stockCode !== newTopStocks[0].stockCode) {
          const previousRank = newTopStocks.findIndex(stock => stock.stockCode === previousTopStock.stockCode) + 1;
          const currentRank = 1;

          const newNotification = {
            id: Date.now(),
            previousStock: {
              name: previousTopStock.stockName,
              rank: previousRank,
              changePercent: previousTopStock.changePercent,
            },
            currentStock: {
              name: newTopStocks[0].stockName,
              rank: currentRank,
              changePercent: newTopStocks[0].changePercent,
            },
            type: 'rank_change',
          };
          setNotificationHistory(prev => [newNotification, ...prev.slice(0, 9)]);

          if (!showNotificationDropdown) {
            setNotificationCount(prev => prev + 1);
          }
        }

        setPreviousTopStock(newTopStocks[0]);
        setIsAnimating(false);
      }, 300);
    }
  }, [topNavStocks, setNotificationCount, setNotificationHistory, showNotificationDropdown, previousTopStock]);

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
    const stock = topNavStocks.find(s => s.stockName === stockName);
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
          ) : topNavStocks.length > 0 ? (
            <div className="stock-list-container">
              <div className="stock-items">
                {topNavStocks.slice(0, 5).map((stock, index) => (
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
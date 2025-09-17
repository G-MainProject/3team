import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import './TopNav.css'
import maleAvatar from '../../assets/images/male.jpg'
import femaleAvatar from '../../assets/images/female.jpg'
import { useAuth } from '../../contexts/AuthContext'
import { getStockSummary } from '../../services/yahooFinanceApi'

const TopNav = ({ onStepClick, selectedSymbol, onSymbolChange, topNavStocks, topNavLoading }) => {
  const { user, logout } = useAuth()
  const [topStocks, setTopStocks] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedStock, setSelectedStock] = useState(selectedSymbol || '005930') // props에서 받은 값 사용
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)
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

  // 실제 주식 데이터 가져오기 함수
  const fetchRealStockData = useCallback(async () => {
    try {
      const stockDataPromises = stockSymbols.map(async (stock) => {
        try {
          const summary = await getStockSummary(stock.symbol)
          if (summary) {
            return {
              ...stock,
              currentPrice: summary.currentPrice,
              change: summary.change,
              changePercent: summary.changePercent,
              volume: summary.volume,
              marketCap: summary.marketCap
            }
          } else {
            // API 호출 실패 시 기본값 반환
            return {
              ...stock,
              currentPrice: 50000,
              change: 0,
              changePercent: 0,
              volume: 0,
              marketCap: 0
            }
          }
        } catch (error) {
          console.error(`${stock.name} 데이터 가져오기 실패:`, error)
          // 개별 주식 데이터 가져오기 실패 시 기본값 반환
          return {
            ...stock,
            currentPrice: 50000,
            change: 0,
            changePercent: 0,
            volume: 0,
            marketCap: 0
          }
        }
      })

      const stockData = await Promise.all(stockDataPromises)
      return stockData
    } catch (error) {
      console.error('주식 데이터 가져오기 실패:', error)
      // 전체 실패 시 기본값 반환
      return stockSymbols.map((stock, index) => ({
        ...stock,
        currentPrice: 50000 + (index * 10000),
        change: 0,
        changePercent: 0,
        volume: 1000000 + (index * 100000),
        marketCap: 1000000000000 + (index * 100000000000)
      }))
    }
  }, [stockSymbols])

  // Dashboard에서 전달받은 데이터 사용
  useEffect(() => {
    if (topNavStocks && topNavStocks.length > 0) {
      // Dashboard의 데이터가 있으면 사용
      setIsLoading(topNavLoading)
      
      // 애니메이션 시작
      setIsAnimating(true)
      
      // 약간의 지연 후 데이터 업데이트
      setTimeout(() => {
        setTopStocks(topNavStocks.slice(0, 5)) // 상위 5개만
        setIsLoading(false)
        
        // 애니메이션 종료
        setTimeout(() => {
          setIsAnimating(false)
        }, 300)
      }, 150)
    } else {
      // Dashboard 데이터가 없으면 개별 로딩
      const fetchStockData = async () => {
        try {
          setIsLoading(true)
          
          // 실제 주식 데이터 가져오기
          const stockData = await fetchRealStockData()
          
          // 변동폭 순으로 정렬 (절댓값 기준)
          const sortedStocks = stockData.sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent))
          
          // 애니메이션 시작
          setIsAnimating(true)
          
          // 약간의 지연 후 데이터 업데이트
          setTimeout(() => {
            setTopStocks(sortedStocks.slice(0, 5)) // 상위 5개만
            setIsLoading(false)
            
            // 애니메이션 종료
            setTimeout(() => {
              setIsAnimating(false)
            }, 300)
          }, 150)
        } catch (error) {
          console.error('주식 데이터 가져오기 실패:', error)
          setIsLoading(false)
        }
      }

      // 초기 로드
      fetchStockData()
      
      // 10초마다 업데이트
      const interval = setInterval(fetchStockData, 10000)
      return () => clearInterval(interval)
    }
  }, [topNavStocks, topNavLoading, fetchRealStockData])

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
    navigate('/');
  };

  // 주식 클릭 핸들러
  const handleStockClick = (stock) => {
    setSelectedStock(stock.symbol)
    if (onSymbolChange) {
      onSymbolChange(stock.symbol)
    }
    if (onStepClick) {
      onStepClick('Dashboard')
    }
  }

  return (
    <div className='top-nav-container'>
        {/* 주식 변동폭 순위 */}
        <div className='progress-indicator'>
          {isLoading ? (
            <div className="stock-loading">실시간 주식 데이터 로딩 중...</div>
          ) : topStocks.length > 0 ? (
            topStocks.map((stock, index) => (
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
            ))
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

        <button className='top-nav-bell'>
            <i className="fa-regular fa-bell"></i>
        </button>

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

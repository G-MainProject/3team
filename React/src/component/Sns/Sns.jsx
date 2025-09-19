import React, { useState, useEffect, useRef } from 'react'
import './Sns.css'
import apiService from '../../services/api'

const Sns = ({ selectedSymbol = '005930' }) => {
  const [tweets, setTweets] = useState([])
  const [redditPosts, setRedditPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activePlatform, setActivePlatform] = useState('x')
  const [lastUpdated, setLastUpdated] = useState(null)
  const snsContainerRef = useRef(null)

  // section-container 높이에 맞춰 sns-container 높이 조정
  const adjustHeightToMatchSection = () => {
    if (snsContainerRef.current) {
      // section-container 찾기 (주가 차트 섹션)
      const sectionContainer = document.querySelector('.dashboard-grid .section-container:nth-child(2)')
      if (sectionContainer) {
        const sectionHeight = sectionContainer.offsetHeight
        snsContainerRef.current.style.height = `${sectionHeight}px`
        console.log('SNS 컨테이너 높이 조정:', sectionHeight + 'px')
      }
    }
  }

  // 심볼에 따른 주식 이름 매핑
  const getStockName = (symbol) => {
    const stockNames = {
      '005930': '삼성전자',
      '000660': 'SK하이닉스',
      '035420': 'NAVER',
      '207940': '삼성바이오로직스',
      '006400': '삼성SDI'
    }
    return stockNames[symbol] || '알 수 없는 주식'
  }

  // selectedSymbol이 변경될 때마다 데이터 업데이트
  useEffect(() => {
    const fetchSnsData = async () => {
      console.log('SNS 데이터 요청 시작:', selectedSymbol)
      setLoading(true)
      setError(null)
      
      try {
        // apiService를 사용한 API 호출
        console.log('API 호출 시작:', selectedSymbol)
        const data = await apiService.getSnsData(selectedSymbol)
        console.log('API 응답 데이터:', data)
        
        console.log('API 성공 - 데이터 설정 중')
        setTweets(data.tweets || [])
        setRedditPosts(data.redditPosts || [])
        setLastUpdated(new Date())
        setError(null)
        console.log('데이터 설정 완료 - tweets:', data.tweets?.length, 'reddit:', data.redditPosts?.length)
        
      } catch (error) {
        console.error('SNS API 호출 오류:', error)
        setError('API 서버에서 데이터를 가져올 수 없습니다.')
        // API 실패 시 빈 데이터 설정
        setTweets([])
        setRedditPosts([])
        setLastUpdated(new Date())
      } finally {
        setLoading(false)
      }
    }

    fetchSnsData()
  }, [selectedSymbol])

  // 컴포넌트 마운트 후 및 데이터 로드 후 높이 조정
  useEffect(() => {
    // DOM이 완전히 렌더링된 후 높이 조정
    const timer = setTimeout(() => {
      adjustHeightToMatchSection()
    }, 100)

    return () => clearTimeout(timer)
  }, [tweets, redditPosts, loading])

  // 윈도우 리사이즈 시 높이 재조정
  useEffect(() => {
    const handleResize = () => {
      adjustHeightToMatchSection()
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // 5분마다 자동 새로고침
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading) {
        const fetchSnsData = async () => {
          try {
            const data = await apiService.getSnsData(selectedSymbol)
            setTweets(data.tweets || [])
            setRedditPosts(data.redditPosts || [])
            setLastUpdated(new Date())
            setError(null)
          } catch (error) {
            console.error('SNS 자동 새로고침 오류:', error)
          }
        }
        fetchSnsData()
      }
    }, 300000) // 5분 = 300,000ms

    return () => clearInterval(interval)
  }, [selectedSymbol, loading])

  if (loading) {
    return (
      <div className='sns-container' ref={snsContainerRef}>
        <div className='sns-content'>
          <div className='loading-container'>
            <div className='loading-spinner'></div>
            <p>데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    )
  }

  const data = activePlatform === 'x' ? tweets : redditPosts
  const isReddit = activePlatform === 'reddit'

  return (
    <div className='sns-container' ref={snsContainerRef}>
      <div className='sns-content'>
        <div className='sns-header'>
          <h3><span>{getStockName(selectedSymbol)}</span> SNS 실시간 여론</h3>
          <ul>
            <li>
              <button 
                className={`social-btn ${activePlatform === 'x' ? 'active' : ''}`}
                onClick={() => setActivePlatform('x')}
              >
                X
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

        <div className='social-feed'>
          {error && (
            <div className='error-message'>
              <i className="fa-solid fa-exclamation-triangle"></i>
              <span>{error}</span>
            </div>
          )}
          
          {data && data.length > 0 ? (
            data.map(item => (
              <div 
                key={item.id} 
                className='social-item'
                onClick={() => {
                  if (item.url) {
                    window.open(item.url, '_blank', 'noopener,noreferrer');
                  }
                }}
              >
                <div className='social-header'>
                  <span className='social-author'>{item.author}</span>
                  <span className='social-time'>{item.time}</span>
                </div>
                <div className='social-content'>
                  {item.content}
                </div>
                <div className='social-stats'>
                  <span className='social-likes'>
                    <i className="fa-regular fa-heart"></i>
                    {item.likes}
                  </span>
                  <span className='social-engagement'>
                    <i className={isReddit ? "fa-regular fa-comment" : "fa-solid fa-retweet"}></i>
                    {isReddit ? item.replies : item.retweets}
                  </span>
                  {item.url && (
                    <span className='social-link'>
                      <i className="fa-solid fa-external-link-alt"></i>
                    </span>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className='no-data'>
              <i className="fa-solid fa-comment-slash"></i>
              <p>{activePlatform === 'x' ? 'x.com' : 'reddit.com'} 데이터가 없습니다.</p>
            </div>
          )}
        </div>

        {lastUpdated && (
          <div className='last-updated'>
            <i className="fa-solid fa-clock"></i>
            <span>마지막 업데이트: {lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default Sns
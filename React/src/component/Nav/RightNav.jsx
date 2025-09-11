import React, { useState, useEffect } from 'react'
import './RightNav.css'

const RightNav = () => {
  const [tweets, setTweets] = useState([])
  const [threads, setThreads] = useState([
    {
      id: 1,
      author: '@SamsungTech',
      content: '삼성전자의 새로운 AI 반도체 기술이 업계를 혁신하고 있습니다. 이번 기술은...',
      time: '1시간 전',
      likes: 3420,
      replies: 156
    }
  ])
  const [loading, setLoading] = useState(true)
  const [activePlatform, setActivePlatform] = useState('x')

  // 임시 데이터 (실제로는 API 호출)
  useEffect(() => {
    const mockTweets = [
      {
        id: 1,
        author: '@SamsungNews',
        content: '삼성전자, 3분기 실적 발표... AI 반도체 수요 증가로 긍정적 전망',
        time: '2시간 전',
        likes: 1240,
        retweets: 89
      },
      {
        id: 2,
        author: '@TechAnalyst',
        content: '삼성전자 메모리 반도체 기술력이 업계를 선도하고 있다. 특히 HBM 기술에서...',
        time: '4시간 전',
        likes: 892,
        retweets: 156
      },
      {
        id: 3,
        author: '@InvestorDaily',
        content: '삼성전자 주가 상승세 지속, 글로벌 공급망 안정화와 AI 수요 증가가 견인',
        time: '6시간 전',
        likes: 2103,
        retweets: 234
      },
      {
        id: 4,
        author: '@MarketWatch',
        content: '삼성전자, 시스템 반도체 확장 전략으로 수익성 개선 기대감 확산',
        time: '8시간 전',
        likes: 567,
        retweets: 78
      },
      {
        id: 5,
        author: '@TechTrends',
        content: '삼성전자 차세대 반도체 기술 개발 속도가 빨라지고 있다. 경쟁사 대비...',
        time: '10시간 전',
        likes: 1456,
        retweets: 189
      }
    ]

    const mockThreads = [
      {
        id: 1,
        author: '@SamsungTech',
        content: '삼성전자의 새로운 AI 반도체 기술이 업계를 혁신하고 있습니다. 이번 기술은...',
        time: '1시간 전',
        likes: 3420,
        replies: 156
      },
      {
        id: 2,
        author: '@InvestorInsight',
        content: '삼성전자 주가 분석: 현재 시장 상황에서의 투자 전략과 향후 전망에 대해...',
        time: '3시간 전',
        likes: 1890,
        replies: 89
      },
      {
        id: 3,
        author: '@TechReview',
        content: '삼성전자 메모리 반도체의 경쟁력 분석: SK하이닉스와의 차별화 포인트는...',
        time: '5시간 전',
        likes: 2567,
        replies: 234
      },
      {
        id: 4,
        author: '@MarketAnalysis',
        content: '글로벌 반도체 시장에서 삼성전자의 위치와 향후 5년 전망...',
        time: '7시간 전',
        likes: 1234,
        replies: 67
      },
      {
        id: 5,
        author: '@TechFuture',
        content: '삼성전자의 시스템 반도체 확장 전략이 가져올 시장 변화...',
        time: '9시간 전',
        likes: 1876,
        replies: 123
      }
    ]
    
    // API 호출 시뮬레이션
    setTimeout(() => {
      setTweets(mockTweets)
      setThreads(mockThreads)
      setLoading(false)
    }, 1000)
  }, [])

  const handlePlatformChange = (platform) => {
    setActivePlatform(platform)
  }

  const renderContent = () => {
    if (loading) {
      return (
        <div className='loading-container'>
          <div className='loading-spinner'></div>
          <p>데이터를 불러오는 중...</p>
        </div>
      )
    }

    const data = activePlatform === 'x' ? tweets : threads
    const isThreads = activePlatform === 'threads'

    return (
      <div className='social-feed'>
        {data && data.length > 0 ? (
          data.map(item => (
            <div key={item.id} className='social-item'>
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
                  <i className={isThreads ? "fa-regular fa-comment" : "fa-solid fa-retweet"}></i>
                  {isThreads ? item.replies : item.retweets}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className='no-data'>
            <p>데이터를 불러올 수 없습니다.</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className='right-nav-container'>
      <div className='right-nav-content'>
        <div className='right-nav-header'>
          <h3><span>삼성전자</span> SNS 실시간 여론</h3>
          <ul>
            <li>
              <button 
                className={`social-btn ${activePlatform === 'x' ? 'active' : ''}`}
                onClick={() => handlePlatformChange('x')}
              >
                X
              </button>
            </li>
            <li>
              <button 
                className={`social-btn ${activePlatform === 'threads' ? 'active' : ''}`}
                onClick={() => handlePlatformChange('threads')}
              >
                Threads
              </button>
            </li>
          </ul>
        </div>
        
        {renderContent()}
      </div>
    </div>
  )
}

export default RightNav

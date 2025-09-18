import React, { useState, useEffect } from 'react'
import './Sns.css'

const Sns = ({ selectedSymbol = '005930' }) => {
  const [tweets, setTweets] = useState([])
  const [redditPosts, setRedditPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activePlatform, setActivePlatform] = useState('x')
  const [lastUpdated, setLastUpdated] = useState(null)

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

  // 심볼별 SNS 데이터
  const getSnsData = (symbol) => {
    const stockName = getStockName(symbol)
    
    const tweetsData = {
      '005930': [
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
        }
      ],
      '000660': [
        {
          id: 1,
          author: '@SKHynixNews',
          content: 'SK하이닉스, HBM3E 메모리 대량 생산 시작... AI 서버 수요 급증으로 호재',
          time: '1시간 전',
          likes: 1567,
          retweets: 123
        },
        {
          id: 2,
          author: '@MemoryTech',
          content: 'SK하이닉스의 차세대 메모리 기술이 업계 표준을 이끌고 있다',
          time: '3시간 전',
          likes: 934,
          retweets: 67
        }
      ],
      '035420': [
        {
          id: 1,
          author: '@NaverTech',
          content: '네이버, AI 검색 기술 혁신으로 사용자 경험 대폭 개선',
          time: '2시간 전',
          likes: 2100,
          retweets: 189
        },
        {
          id: 2,
          author: '@TechKorea',
          content: '네이버의 클라우드 서비스 확장으로 수익성 개선 기대',
          time: '5시간 전',
          likes: 1456,
          retweets: 98
        }
      ],
      '207940': [
        {
          id: 1,
          author: '@BioTechNews',
          content: '삼성바이오로직스, 신약 개발 파트너십 확대로 성장 동력 확보',
          time: '1시간 전',
          likes: 789,
          retweets: 45
        }
      ],
      '006400': [
        {
          id: 1,
          author: '@BatteryTech',
          content: '삼성SDI, 전기차 배터리 기술 혁신으로 글로벌 시장 점유율 확대',
          time: '3시간 전',
          likes: 1234,
          retweets: 78
        }
      ]
    }


    const redditData = {
      '005930': [
        {
          id: 1,
          author: 'u/StockAnalyst (r/stocks)',
          content: '삼성전자 주가 분석: AI 반도체 수요 증가로 긍정적 전망\n\n최근 삼성전자의 AI 반도체 사업이 주목받고 있습니다...',
          time: '2시간 전',
          likes: 45,
          replies: 12
        },
        {
          id: 2,
          author: 'u/Investor123 (r/investing)',
          content: '삼성전자 투자 의견: 현재 시점에서의 매수/매도 전략',
          time: '4시간 전',
          likes: 23,
          replies: 8
        }
      ],
      '000660': [
        {
          id: 1,
          author: 'u/MemoryExpert (r/SecurityAnalysis)',
          content: 'SK하이닉스 HBM 기술력 분석: 삼성전자와의 경쟁 구도',
          time: '1시간 전',
          likes: 67,
          replies: 15
        }
      ],
      '035420': [
        {
          id: 1,
          author: 'u/TechInvestor (r/stocks)',
          content: '네이버 AI 기술 투자 전망: 검색 시장에서의 경쟁력',
          time: '3시간 전',
          likes: 34,
          replies: 6
        }
      ],
      '207940': [
        {
          id: 1,
          author: 'u/BioAnalyst (r/investing)',
          content: '삼성바이오로직스 신약 개발 파이프라인과 수익성 전망',
          time: '2시간 전',
          likes: 28,
          replies: 5
        }
      ],
      '006400': [
        {
          id: 1,
          author: 'u/BatteryExpert (r/stocks)',
          content: '삼성SDI 전기차 배터리 시장에서의 경쟁력과 성장 전략',
          time: '3시간 전',
          likes: 41,
          replies: 9
        }
      ]
    }

    return {
      tweets: tweetsData[symbol] || [],
      redditPosts: redditData[symbol] || []
    }
  }

  // selectedSymbol이 변경될 때마다 데이터 업데이트
  useEffect(() => {
    const fetchSnsData = async () => {
      console.log('SNS 데이터 요청 시작:', selectedSymbol)
      setLoading(true)
      setError(null)
      
      try {
        // 실제 Spring API 호출
        console.log('API 호출 URL:', `http://localhost:8080/api/sns/${selectedSymbol}`)
        const response = await fetch(`http://localhost:8080/api/sns/${selectedSymbol}`)
        console.log('API 응답 상태:', response.status)
        console.log('API 응답 OK:', response.ok)
        
        const data = await response.json()
        console.log('API 응답 데이터:', data)
        
        if (response.ok) {
          console.log('API 성공 - 데이터 설정 중')
          setTweets(data.tweets || [])
          setRedditPosts(data.redditPosts || [])
          setLastUpdated(new Date())
          setError(null)
          console.log('데이터 설정 완료 - tweets:', data.tweets?.length, 'reddit:', data.redditPosts?.length)
        } else {
          console.error('SNS 데이터 로드 실패:', data)
          setError('API 서버에서 데이터를 가져올 수 없습니다. 더미 데이터를 표시합니다.')
          // API 실패 시 더미 데이터 사용
          const snsData = getSnsData(selectedSymbol)
          setTweets(snsData.tweets)
          setRedditPosts(snsData.redditPosts || [])
          setLastUpdated(new Date())
        }
      } catch (error) {
        console.error('SNS API 호출 오류:', error)
        setError('네트워크 오류가 발생했습니다. 더미 데이터를 표시합니다.')
        // 네트워크 오류 시 더미 데이터 사용
        const snsData = getSnsData(selectedSymbol)
        setTweets(snsData.tweets)
        setRedditPosts(snsData.redditPosts || [])
        setLastUpdated(new Date())
      } finally {
        setLoading(false)
      }
    }

    fetchSnsData()
  }, [selectedSymbol])

  // 5분마다 자동 새로고침
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading) {
        const fetchSnsData = async () => {
          try {
            const response = await fetch(`http://localhost:8080/api/sns/${selectedSymbol}`)
            const data = await response.json()
            
            if (response.ok) {
              setTweets(data.tweets || [])
              setRedditPosts(data.redditPosts || [])
              setLastUpdated(new Date())
              setError(null)
            }
          } catch (error) {
            console.error('자동 새로고침 실패:', error)
          }
        }
        fetchSnsData()
      }
    }, 300000) // 5분 = 300,000ms

    return () => clearInterval(interval)
  }, [selectedSymbol, loading])

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

    const data = activePlatform === 'x' ? tweets : redditPosts
    const isReddit = activePlatform === 'reddit'

    return (
      <div className='social-feed'>
        {error && (
          <div className='error-message'>
            <i className="fa-solid fa-exclamation-triangle"></i>
            <span>{error}</span>
          </div>
        )}
        
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
                  <i className={isReddit ? "fa-regular fa-comment" : "fa-solid fa-retweet"}></i>
                  {isReddit ? item.replies : item.retweets}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className='no-data'>
            <p>데이터를 불러올 수 없습니다.</p>
          </div>
        )}
        
        {lastUpdated && (
          <div className='last-updated'>
            <i className="fa-solid fa-clock"></i>
            <span>마지막 업데이트: {lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className='sns-container'>
      <div className='sns-content'>
        <div className='sns-header'>
          <h3><span>{getStockName(selectedSymbol)}</span> SNS 실시간 여론</h3>
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
                className={`social-btn ${activePlatform === 'reddit' ? 'active' : ''}`}
                onClick={() => handlePlatformChange('reddit')}
              >
                Reddit
              </button>
            </li>
          </ul>
        </div>
        
        {renderContent()}
      </div>
    </div>
  )
}

export default Sns

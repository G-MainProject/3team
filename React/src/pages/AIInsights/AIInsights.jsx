import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import styles from './AIInsights.module.css';
import LeftNav from '../../component/Nav/LeftNav';
import TopNav from '../../component/Nav/TopNav';
import Footer from '../../component/Footer/Footer';
import CircleGraph from '../../component/CircleGraph/CircleGraph';
import MyWordCloud from '../../component/WordCloud/MyWordCloud';
import { getStockSummary } from '../../services/yahooFinanceApi';
import finalReportData from '../../../../data/final_report.json';



export default function AIInsights({ selectedSymbol: globalSelectedSymbol }) {
    const location = useLocation();
    // AIInsights 페이지 내에서 사용할 로컬 상태
    const [localSelectedSymbol, setLocalSelectedSymbol] = useState(null);

    const [showFooterButton, setShowFooterButton] = useState(false);
    const [showFooter, setShowFooter] = useState(false);
    const [buttonAnimation, setButtonAnimation] = useState('');
    const [allowScrollToFooter, setAllowScrollToFooter] = useState(false);
    const [isInFooter, setIsInFooter] = useState(false);
    const [newsFilter, setNewsFilter] = useState('all'); // 뉴스 필터 상태 추가
    const [selectedNews, setSelectedNews] = useState(null); // 선택된 뉴스 상태 추가
    // TopNav용 주식 데이터 상태
    const [topNavStocks, setTopNavStocks] = useState([]);
    const [topNavLoading, setTopNavLoading] = useState(true);
    const footerRef = useRef(null);
    const showFooterButtonRef = useRef(false);
    const newsSectionRef = useRef(null); // 뉴스 섹션 스크롤을 위한 ref 추가

    // Initialize localSelectedSymbol from globalSelectedSymbol or URL state
    useEffect(() => {
        if (location.state?.selectedSymbol && !localSelectedSymbol) {
            setLocalSelectedSymbol(location.state.selectedSymbol);
        } else if (globalSelectedSymbol && !localSelectedSymbol) {
            setLocalSelectedSymbol(globalSelectedSymbol);
        }
    }, [location.state?.selectedSymbol, globalSelectedSymbol, localSelectedSymbol]);

    const [currentStockData, setCurrentStockData] = useState(null); // Holds the full report for the selected stock

    // Original stock symbols for reference (to keep their 'symbol' values)
    const originalStockSymbols = useMemo(
        () => [
            { symbol: '005930', name: '삼성전자' },
            { symbol: '000660', name: 'SK하이닉스' },
            { symbol: '035420', name: 'NAVER' },
            { symbol: '207940', name: '삼성바이오로직스' },
            { symbol: '006400', name: '삼성SDI' },
        ],
        []
    );

    // Dynamically create stockSymbols based on finalReportData
    const stockSymbols = useMemo(() => {
        const generatedSymbols = new Map(); // To store generated symbols and their corresponding stock names
        const symbols = [];

        finalReportData.forEach(report => {
            const existingSymbolEntry = originalStockSymbols.find(s => s.name === report.stockName);
            let symbol;

            if (existingSymbolEntry) {
                symbol = existingSymbolEntry.symbol;
            } else {
                let potentialSymbol = report.stockName.substring(0, 6);
                if (generatedSymbols.has(potentialSymbol) && generatedSymbols.get(potentialSymbol) !== report.stockName) {
                    // Collision detected, use full stockName as symbol
                    symbol = report.stockName;
                } else {
                    symbol = potentialSymbol;
                }
            }
            generatedSymbols.set(symbol, report.stockName); // Store the generated symbol and its stockName
            symbols.push({ symbol: symbol, name: report.stockName });
        });
        return symbols;
    }, [originalStockSymbols]);

    // Effect to set currentStockData based on localSelectedSymbol
    useEffect(() => {
        if (localSelectedSymbol && stockSymbols.length > 0) {
            const stockName = stockSymbols.find(s => s.symbol === localSelectedSymbol)?.name;
            const data = finalReportData.find(report => report.stockName === stockName);
            setCurrentStockData(data);
        } else if (stockSymbols.length > 0 && finalReportData.length > 0 && !localSelectedSymbol) {
            // Default to the first stock in finalReportData if no local symbol is selected initially
            const defaultStockName = finalReportData[0].stockName;
            const defaultSymbol = stockSymbols.find(s => s.name === defaultStockName)?.symbol || finalReportData[0].stockName.substring(0, 6);
            setLocalSelectedSymbol(defaultSymbol);
        }
    }, [localSelectedSymbol, stockSymbols]);

    // 필터링된 뉴스 데이터
    const filteredNewsData = useMemo(() => {
        if (!currentStockData || !currentStockData.relatedNews) {
            return [];
        }
        const news = currentStockData.relatedNews.map(n => ({
            ...n,
            sentiment: n.sentimentClass // Assign individual news item sentiment
        }));

        if (newsFilter === 'all') {
            return news;
        }
        return news.filter((n) => n.sentiment === newsFilter);
    }, [newsFilter, currentStockData]);

    // 전체 뉴스 데이터를 기반으로 한 감성 분석 데이터 (항상 전체 비율 표시)
    const CircleGraphData = useMemo(() => {
        if (!currentStockData || !currentStockData.sentimentAnalysis || !currentStockData.sentimentAnalysis.sentimentDistribution) {
            return [
                { name: '긍정', value: 0 },
                { name: '부정', value: 0 },
                { name: '중립', value: 0 },
            ];
        }
        const distribution = currentStockData.sentimentAnalysis.sentimentDistribution;
        const total = (distribution.positive || 0) + (distribution.negative || 0) + (distribution.neutral || 0);

        if (total === 0) {
            return [
                { name: '긍정', value: 0 },
                { name: '부정', value: 0 },
                { name: '중립', value: 0 },
            ];
        }

        return [
            { name: '긍정', value: Math.round(((distribution.positive || 0) / total) * 100) },
            { name: '부정', value: Math.round(((distribution.negative || 0) / total) * 100) },
            { name: '중립', value: Math.round(((distribution.neutral || 0) / total) * 100) },
        ];
    }, [currentStockData]);

    // 워드 클라우드 데이터
    const wordCloudData = useMemo(() => {
        if (!currentStockData || !currentStockData.keywordAnalysis || !currentStockData.keywordAnalysis.wordCloud) {
            return [];
        }
        return Object.entries(currentStockData.keywordAnalysis.wordCloud).map(([text, value]) => ({ text, value }));
    }, [currentStockData]);

    // TopNav용 주식 데이터 로드
    useEffect(() => {
        const loadTopNavData = async () => {
            if (stockSymbols.length === 0) return; // 심볼이 준비될 때까지 기다림
            try {
                setTopNavLoading(true);

                // 모든 주식의 요약 정보를 병렬로 가져오기
                const stockDataPromises = stockSymbols.map(async (stock) => {
                    try {
                        const summary = await getStockSummary(stock.symbol);
                        if (summary) {
                            return {
                                ...stock,
                                currentPrice: summary.currentPrice,
                                change: summary.change,
                                changePercent: summary.changePercent,
                                volume: summary.volume,
                                marketCap: summary.marketCap,
                            };
                        } else {
                            // 요약 정보 가져오기 실패 시 기본값 설정
                            return {
                                ...stock,
                                currentPrice: 50000, change: 0, changePercent: 0, volume: 0, marketCap: 0,
                            };
                        }
                    } catch (error) {
                        console.error(`${stock.name} 데이터 가져오기 실패:`, error);
                        return {
                            ...stock,
                            currentPrice: 50000, change: 0, changePercent: 0, volume: 0, marketCap: 0,
                        };
                    }
                });

                const allStockData = await Promise.all(stockDataPromises);

                // 변동폭 순으로 정렬 (절댓값 기준)
                const sortedStocks = allStockData.sort(
                    (a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent)
                );

                setTopNavStocks(sortedStocks);
                setTopNavLoading(false);
            } catch (error) {
                console.error('TopNav 주식 데이터 로드 실패:', error);
                setTopNavLoading(false);
            }
        };

        // 초기 로드
        loadTopNavData();

        // 1분마다 업데이트
        const interval = setInterval(loadTopNavData, 60000);
        return () => clearInterval(interval);
    }, [stockSymbols]); // stockSymbols가 변경될 때만 실행

    // 초기 선택 심볼 설정
    useEffect(() => {
        // URL 상태나 전역 심볼이 없고, 로컬 심볼도 아직 설정되지 않았으며, TopNav 데이터가 로드되었을 때
        if (!location.state?.selectedSymbol && !globalSelectedSymbol && !localSelectedSymbol && topNavStocks.length > 0) {
            const topStock = topNavStocks[0];
            if (topStock) {
                setLocalSelectedSymbol(topStock.symbol);
            }
        }
    }, [topNavStocks, localSelectedSymbol, globalSelectedSymbol, location.state?.selectedSymbol]);

    useEffect(() => {
        if (selectedNews && newsSectionRef.current) {
            newsSectionRef.current.scrollTop = 0;
        }
    }, [selectedNews]);

    useEffect(() => {
        const dashboardMain = document.querySelector(
            `.${styles['ai-insights-main']}`
        );

        const handleScroll = () => {
            if (!dashboardMain) return;

            const scrollTop = dashboardMain.scrollTop;
            const scrollHeight = dashboardMain.scrollHeight;
            const clientHeight = dashboardMain.clientHeight;

            const scrollPercentage = (scrollTop + clientHeight) / scrollHeight;

            if (scrollPercentage > 0.99) {
                if (!showFooterButtonRef.current) {
                    setButtonAnimation('');
                    setShowFooterButton(true);
                    showFooterButtonRef.current = true;
                }
                setShowFooter(true);
            } else {
                if (showFooterButtonRef.current) {
                    setButtonAnimation('hiding');

                    const button = document.querySelector('.footer-scroll-button');
                    if (button) {
                        const handleAnimationEnd = () => {
                            setShowFooterButton(false);
                            setButtonAnimation('');
                            showFooterButtonRef.current = false;
                            button.removeEventListener('animationend', handleAnimationEnd);
                        };
                        button.addEventListener('animationend', handleAnimationEnd);
                    } else {
                        setShowFooterButton(false);
                        setButtonAnimation('');
                        showFooterButtonRef.current = false;
                    }
                }
                setShowFooter(false);
            }
        };

        if (dashboardMain) {
            dashboardMain.addEventListener('scroll', handleScroll);
            return () => dashboardMain.removeEventListener('scroll', handleScroll);
        }
    }, [allowScrollToFooter]);

    // 전체 페이지 스크롤 제한
    useEffect(() => {
        const handlePageScroll = (e) => {
            const dashboardMain = document.querySelector(
                `.${styles['ai-insights-main']}`
            );
            if (!dashboardMain) return;

            const scrollTop = dashboardMain.scrollTop;
            const scrollHeight = dashboardMain.scrollHeight;
            const clientHeight = dashboardMain.clientHeight;

            // 스크롤이 맨 아래에 도달했는지 확인 (반올림 오차 허용)
            const isAtBottom = Math.round(scrollTop + clientHeight) >= scrollHeight;

            // Footer 영역에 있을 때 위로 스크롤 제한
            if (isInFooter && e.deltaY < 0) {
                e.preventDefault();
                return;
            }

            // Dashboard에서 Footer로 가는 것을 제한
            if (!allowScrollToFooter && isAtBottom && e.deltaY > 0) {
                e.preventDefault();
                dashboardMain.scrollTo({
                    top: dashboardMain.scrollHeight - clientHeight,
                    behavior: 'smooth',
                });
            }
        };

        window.addEventListener('wheel', handlePageScroll, { passive: false });
        return () => window.removeEventListener('wheel', handlePageScroll);
    }, [allowScrollToFooter, isInFooter]);

    const handleButtonClick = () => {
        if (isInFooter) {
            // Footer에서 Dashboard로 이동 - fadeOut 애니메이션 적용
            setButtonAnimation('fade-out');

            // 애니메이션 완료 후 상태 변경
            setTimeout(() => {
                setAllowScrollToFooter(false);
                setIsInFooter(false);

                const dashboardMain = document.querySelector(
                    `.${styles['ai-insights-main']}`
                );
                if (dashboardMain) {
                    dashboardMain.scrollTo({
                        top: 0,
                        behavior: 'smooth',
                    });
                }
            }, 300); // fadeOut 애니메이션 시간과 동일
        } else {
            // Dashboard에서 Footer로 이동
            setAllowScrollToFooter(false);
            setIsInFooter(true);

            if (footerRef.current) {
                footerRef.current.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start',
                });
            }
        }
    };

    return (
        <div className={styles['ai-insights-container']}>
            <div className={styles['ai-insights-content']}>
                <LeftNav />
                <div className={styles['ai-insights-main']}>
                    <div className={styles['ai-insights-grid']}>
                        <TopNav
                            selectedSymbol={localSelectedSymbol} // 로컬 상태 전달
                            topNavStocks={topNavStocks}
                            topNavLoading={topNavLoading}
                            onStockSelect={setLocalSelectedSymbol} // TopNav의 클릭 핸들러
                        />
                    </div>

                    <div className={styles['ai-insights-grid2']}>
                        {/* 뉴스 섹션 */}
                        <div className={styles['section-container']}>
                            <div className={styles['section-label']}>
                                <div className={styles['section-title']}>
                                    <h2>뉴스 기사</h2>
                                    <p>최신 관련 뉴스 및 시장 동향</p>
                                </div>
                                <div className={styles['news-filter']}>
                                    <button
                                        className={`${styles['filter-button']} ${
                                            newsFilter === 'all' ? styles['active'] : ''
                                        }`}
                                        onClick={() => setNewsFilter('all')}
                                    >
                                        전체
                                    </button>
                                    <button
                                        className={`${styles['filter-button']} ${
                                            newsFilter === 'positive' ? styles['active'] : ''
                                        }`}
                                        onClick={() => setNewsFilter('positive')}
                                    >
                                        긍정
                                    </button>
                                    <button
                                        className={`${styles['filter-button']} ${
                                            newsFilter === 'negative' ? styles['active'] : ''
                                        }`}
                                        onClick={() => setNewsFilter('negative')}
                                    >
                                        부정
                                    </button>
                                    <button
                                        className={`${styles['filter-button']} ${
                                            newsFilter === 'neutral' ? styles['active'] : ''
                                        }`}
                                        onClick={() => setNewsFilter('neutral')}
                                    >
                                        중립
                                    </button>
                                </div>
                            </div>
                            <div className={styles['news-section']} ref={newsSectionRef}>
                                {selectedNews ? (
                                    // 선택된 뉴스 상세 뷰
                                    <div className={styles['news-detail']}>
                                        <div className={styles['news-detail-header']}>
                                            <button
                                                className={styles['back-button']}
                                                onClick={() => setSelectedNews(null)}
                                            >
                                                <i className="fa-solid fa-arrow-left"></i>
                                                뉴스 목록으로 돌아가기
                                            </button>
                                        </div>
                                        <div className={styles['news-detail-content']}>
                                            <div className={styles['news-detail-meta']}>
                                                <span className={styles['news-detail-date']}>
                                                    {selectedNews.date}
                                                </span>
                                                <span
                                                    className={`${styles['news-detail-sentiment']} ${
                                                        styles[selectedNews.sentiment]
                                                    }`}
                                                >
                                                    {selectedNews.sentiment === 'positive'
                                                        ? '긍정'
                                                        : selectedNews.sentiment === 'negative'
                                                        ? '부정'
                                                        : '중립'}
                                                </span>
                                            </div>
                                            <h2 className={styles['news-detail-title']}>
                                                {selectedNews.title}
                                            </h2>
                                            <div className={styles['news-detail-body']}>
                                                <p>{selectedNews.content}</p>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    // 뉴스 목록 뷰
                                    <div className={styles['news-list']}>
                                        {filteredNewsData.map((news, index) => (
                                            <div
                                                key={index}
                                                className={`${styles['news-item']} ${
                                                    styles[news.sentiment]
                                                }`}
                                                onClick={() => setSelectedNews(news)}
                                            >
                                                <div className={styles['news-content']}>
                                                    <h4>{news.title}</h4>
                                                    <p>{news.content}</p>
                                                    <span className={styles['news-date']}>
                                                        {news.date}
                                                    </span>
                                                </div>
                                                <div className={styles['sentiment-legend']}>
                                                    <div className={styles['sentiment-item']}>
                                                        <span className={styles['sentiment-label']}>
                                                            {news.sentiment === 'positive'
                                                                ? '긍정'
                                                                : news.sentiment === 'negative'
                                                                ? '부정'
                                                                : '중립'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* 감성 분석 섹션 */}
                        <div className={styles['section-container']}>
                            <div className={styles['section-label']}>
                                <div className={styles['section-title']}>
                                    <h2>뉴스 감성 분석</h2>
                                    <p>뉴스 기사의 감정 분석 결과</p>
                                </div>
                            </div>
                            <div className={styles['sentiment-section']}>
                                <CircleGraph
                                    data={CircleGraphData}
                                    colors={['#34a853', '#ea4335', '#fbbc04']}
                                    selectedFilter={newsFilter}
                                    onSegmentClick={(data) => {
                                        if (data && data.name) {
                                            // 감성 이름을 영어로 변환
                                            const sentimentMap = {
                                                긍정: 'positive',
                                                부정: 'negative',
                                                중립: 'neutral',
                                            };
                                            const sentiment = sentimentMap[data.name];
                                            if (sentiment) {
                                                setNewsFilter(sentiment);
                                            }
                                        }
                                    }}
                                />
                            </div>
                        </div>

                        {/* 워드 클라우드 섹션 */}
                        <div className={styles['section-container']}>
                            <div className={styles['section-label']}>
                                <div className={styles['section-title']}>
                                    <h2>핵심 키워드</h2>
                                    <p>뉴스에서 자주 언급되는 주요 키워드</p>
                                </div>
                            </div>
                            <div className={styles['wordcloud-section']}>
                                <div className={styles['wordcloud-container']}>
                                    <div className={styles['wordcloud-placeholder']}>
                                        <MyWordCloud data={wordCloudData} />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* AI 분석 섹션 */}
                        <div className={styles['section-container']}>
                            <div className={styles['section-label']}>
                                <div className={styles['section-title']}>
                                    <h2>AI 분석 및 예측</h2>
                                    <p>Gemini AI 기반 종합 분석 및 투자 권고</p>
                                </div>
                            </div>
                            <div className={styles['ai-analysis-section']}>
                                <div className={styles['ai-analysis-container']}>
                                    <div className={styles['ai-analysis-content']}>
                                        <h3>종합 분석</h3>
                                        <p>
                                            현재 시장 상황을 종합적으로 분석한 결과, 삼성전자는 AI
                                            반도체 수요 증가와 글로벌 공급망 안정화로 인해
                                            중장기적으로 긍정적인 전망을 보이고 있습니다. 특히 메모리
                                            반도체 분야에서의 기술적 우위와 시스템 반도체 확장 전략이
                                            수익성 개선에 기여할 것으로 예상됩니다.
                                        </p>
                                    </div>
                                    <div className={styles['ai-prediction']}>
                                        <h3>투자 권고사항</h3>
                                        <div className={styles['prediction-item']}>
                                            <span className={styles['prediction-label']}>
                                                단기 (1-3개월):
                                            </span>
                                            <span
                                                className={`${styles['prediction-value']} ${styles['positive']}`}
                                            >
                                                매수
                                            </span>
                                        </div>
                                        <div className={styles['prediction']}>
                                            <span className={styles['prediction-label']}>
                                                중기 (3-6개월):
                                            </span>
                                            <span
                                                className={`${styles['prediction-value']} ${styles['positive']}`}
                                            >
                                                강력 매수
                                            </span>
                                        </div>
                                        <div className={styles['prediction-item']}>
                                            <span className={styles['prediction-label']}>
                                                장기 (6개월+):
                                            </span>
                                            <span
                                                className={`${styles['prediction-value']} ${styles['negative']}`}
                                            >
                                                매도
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer/Dashboard 이동 버튼 */}
            {showFooterButton && (
                <button
                    className={`footer-scroll-button ${buttonAnimation} ${
                        isInFooter ? 'in-footer' : ''
                    }`}
                    onClick={handleButtonClick}
                >
                    <i
                        className={`fa-solid ${
                            isInFooter ? 'fa-arrow-up' : 'fa-arrow-down'
                        }`}
                    ></i>
                    <span>{isInFooter ? 'Dashboard로 이동' : 'Footer로 이동'}</span>
                </button>
            )}

            {/* Footer */}
            {showFooter && (
                <div ref={footerRef}>
                    <Footer />
                </div>
            )}
        </div>
    );
}
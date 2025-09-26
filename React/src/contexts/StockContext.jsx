import React, { createContext, useState, useEffect } from 'react';
import finalReportData from '../../../data/raws/sentiment_report.json';

const StockContext = createContext();
export { StockContext };

export const StockProvider = ({ children }) => {
    const [stocks, setStocks] = useState([]);
    const [selectedStock, setSelectedStock] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const initializeStocks = async () => {
            setLoading(true);
            const uniqueStocks = Array.from(
                new Map(finalReportData.map(stock => [stock.stockCode, stock])).values()
            );
            const initialStocks = uniqueStocks.map(stock => ({ ...stock }));

            // 초기 선택된 주식 설정 (변동폭 절댓값 기준 1등 주식)
            if (initialStocks.length > 0 && !selectedStock) {
                const sortedStocks = [...initialStocks].sort((a, b) => Math.abs(b.changePercent || 0) - Math.abs(a.changePercent || 0));
                setSelectedStock(sortedStocks[0]);
            }

            // API 호출 제거 - useRealtimeStockData에서 처리
            setStocks(initialStocks);
            setLoading(false);
        };

        initializeStocks();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const setSelectedStockByCode = (stockCode) => {
        const stock = stocks.find(s => s.stockCode === stockCode);
        if (stock) {
            setSelectedStock(stock);
        }
    };

    const value = { stocks, selectedStock, setSelectedStockByCode, loading };

    return <StockContext.Provider value={value}>{children}</StockContext.Provider>;
};
import React, { createContext, useState, useEffect } from 'react';
import finalReportData from '../../../data/raws/sentiment_report.json';

const StockContext = createContext();
export { StockContext };

export const StockProvider = ({ children }) => {
    const [stocks, setStocks] = useState([]);
    const [selectedStock, setSelectedStock] = useState(null);
    const [loading, setLoading] = useState(true);
    const [userHasManuallySelected, setUserHasManuallySelected] = useState(false);

    useEffect(() => {
        const initializeStocks = async () => {
            setLoading(true);
            const uniqueStocks = Array.from(
                new Map(finalReportData.map(stock => [stock.stockCode, stock])).values()
            );
            const initialStocks = uniqueStocks.map(stock => ({ ...stock }));

            // 변동폭 절대값 기준으로 주식 정렬
            const sortedStocks = [...initialStocks].sort((a, b) => Math.abs(b.changePercent || 0) - Math.abs(a.changePercent || 0));

            // 정렬된 리스트로 stocks 상태 설정
            setStocks(sortedStocks);

            // 초기 선택된 주식 설정 (1등 주식)
            if (sortedStocks.length > 0 && !selectedStock) {
                setSelectedStock(sortedStocks[0]);
            }

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

    const value = { stocks, selectedStock, setSelectedStockByCode, loading, userHasManuallySelected, setUserHasManuallySelected };

    return <StockContext.Provider value={value}>{children}</StockContext.Provider>;
};
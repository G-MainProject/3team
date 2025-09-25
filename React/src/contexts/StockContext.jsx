import React, { createContext, useState, useEffect } from 'react';
import finalReportData from '../../../data/sentiment_report.json';
import { getStockSummary } from '../services/yahooFinanceApi';

export const StockContext = createContext();

export const StockProvider = ({ children }) => {
    const [stocks, setStocks] = useState([]);
    const [selectedStock, setSelectedStock] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const initializeStocks = async () => {
            setLoading(true);
            const initialStocks = finalReportData.map(stock => ({ ...stock }));

            if (initialStocks.length > 0 && !selectedStock) {
                setSelectedStock(initialStocks[0]);
            }

            const fetchStockData = async () => {
                try {
                    const promises = initialStocks.map(stock => getStockSummary(stock.stockCode));
                    const results = await Promise.all(promises);

                    const updatedStocks = initialStocks.map((stock, index) => ({
                        ...stock,
                        ...(results[index] || {}),
                    }));

                    setStocks(updatedStocks);

                    // Update selected stock with new data
                    if (selectedStock) {
                        const updatedSelected = updatedStocks.find(s => s.stockCode === selectedStock.stockCode);
                        if (updatedSelected) {
                            setSelectedStock(updatedSelected);
                        }
                    }
                } catch (error) {
                    console.error("Error fetching real-time stock data:", error);
                    setStocks(initialStocks); // On error, revert to initial data
                } finally {
                    setLoading(false);
                }
            };

            fetchStockData();
            const interval = setInterval(fetchStockData, 60000);

            return () => clearInterval(interval);
        };

        initializeStocks();
    }, []); // Run only once on mount

    const setSelectedStockByCode = (stockCode) => {
        const stock = stocks.find(s => s.stockCode === stockCode);
        if (stock) {
            setSelectedStock(stock);
        }
    };

    const value = { stocks, selectedStock, setSelectedStockByCode, loading };

    return <StockContext.Provider value={value}>{children}</StockContext.Provider>;
};

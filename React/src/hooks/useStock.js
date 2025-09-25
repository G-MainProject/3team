import { useContext } from 'react';
import { StockContext } from '../contexts/StockContext';

export const useStock = () => {
    const context = useContext(StockContext);
    if (!context) {
        throw new Error('useStock must be used within a StockProvider');
    }
    return context;
};
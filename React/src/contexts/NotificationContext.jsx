import React, { createContext, useContext, useState, useCallback } from 'react';

const NotificationContext = createContext();

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [notificationCount, setNotificationCount] = useState(0);
  const [notificationHistory, setNotificationHistory] = useState([]);

  const addNotification = useCallback((notification) => {
    const newNotification = {
      id: Date.now(),
      ...notification,
      time: new Date().toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    };
    
    setNotificationHistory(prev => [newNotification, ...prev]);
    setNotificationCount(prev => prev + 1);
  }, []);

  const clearNotifications = useCallback(() => {
    setNotificationCount(0);
  }, []);

  const removeNotification = useCallback((id) => {
    setNotificationHistory(prev => prev.filter(notification => notification.id !== id));
    setNotificationCount(prev => Math.max(0, prev - 1));
  }, []);

  const value = {
    notificationCount,
    notificationHistory,
    addNotification,
    clearNotifications,
    removeNotification,
    setNotificationCount,
    setNotificationHistory
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

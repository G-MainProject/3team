import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './Chart.css';

// 30일간의 주식 데이터를 생성합니다.
const generateDummyData = () => {
  const data = [];
  let price = 10000; // 시작 가격
  for (let i = 30; i > 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    // 가격 변동을 좀 더 현실적으로 만듭니다.
    const fluctuation = (Math.random() - 0.45) * 2000;
    price += fluctuation;
    price = Math.max(price, 5000); // 최소 가격
    data.push({
      date: date.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }),
      price: Math.round(price),
    });
  }
  return data;
};

const Chart = () => {
  const data = generateDummyData();

  // Y축 단위를 '원'으로 포맷팅하는 함수
  const formatYAxis = (tickItem) => {
    return `${tickItem.toLocaleString()}원`;
  };

  return (
    <div className="chart-container">
      <h2>주식 시세</h2>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={data}
          margin={{
            top: 20,
            right: 30,
            left: 50, // Y축 레이블 공간 확보
            bottom: 5,
          }}
        >
          {/* 차트 그리드 라인 */}
          <CartesianGrid strokeDasharray="3 3" stroke="#555" />
          {/* X축 (날짜) */}
          <XAxis dataKey="date" stroke="#ccc" padding={{ left: 20, right: 20 }} />
          {/* Y축 (가격) */}
          <YAxis stroke="#ccc" tickFormatter={formatYAxis} domain={['dataMin - 1000', 'dataMax + 1000']} allowDataOverflow={true} padding={{ top: 20, bottom: 20 }} />
          {/* 마우스 호버 시 정보 표시 */}
          <Tooltip
            contentStyle={{ backgroundColor: '#333', border: '1px solid #555' }}
            labelStyle={{ color: '#fff' }}
            itemStyle={{ color: '#FFFFFF' }}
            formatter={(value) => [`${value.toLocaleString()}원`, '가격']}
          />
          {/* 범례 */}
          <Legend wrapperStyle={{ color: '#fff' }} />
          {/* 가격 라인 */}
          <Line type="monotone" dataKey="price" stroke="#FFFFFF" strokeWidth={2} activeDot={{ r: 8 }} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Chart;
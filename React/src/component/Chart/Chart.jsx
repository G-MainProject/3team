import React from 'react';
// recharts 라이브러리에서 필요한 컴포넌트들을 가져옵니다.
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
// 차트 스타일을 위한 CSS 파일을 가져옵니다.
import './Chart.css';

// 상세한 더미 주식 데이터를 생성하는 함수
const generateDummyData = (numPoints) => {
  const data = [];
  let lastPrice = 50000; // 시작 가격
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - numPoints); // 오늘부터 numPoints일 전을 시작 날짜로 설정

  for (let i = 0; i < numPoints; i++) {
    const newDate = new Date(startDate);
    newDate.setDate(newDate.getDate() + i);
    
    // 가격 변동 시뮬레이션
    const fluctuation = (Math.random() - 0.48) * 2000;
    lastPrice += fluctuation;
    lastPrice = Math.max(lastPrice, 10000); // 가격이 너무 낮아지지 않도록 최소값 설정

    data.push({
      date: `${newDate.getMonth() + 1}/${newDate.getDate()}`,
      price: Math.round(lastPrice), // 반올림된 가격
    });
  }
  return data;
};

// 상세한 그래프를 위해 100개의 데이터 포인트를 생성합니다.
const dummyData = generateDummyData(100);

const Chart = () => {
  // Y축 눈금을 원화(₩) 형식으로 포맷하는 함수
  const formatYAxis = (tickItem) => {
    return `₩${tickItem.toLocaleString()}`; // 숫자에 1000단위 콤마와 '₩' 기호를 추가
  };

  // 커스텀 툴팁 컴포넌트
  const CustomTooltip = ({ active, payload, label }) => {
    // 툴팁이 활성화되고 내용(payload)이 있을 때만 표시
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="label">{`날짜 : ${label}`}</p>
          <p className="intro">{`가격 : ₩${payload[0].value.toLocaleString()}`}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <h3 className="chart-title">주식 데이터 시뮬레이션</h3>
      {/* ResponsiveContainer는 차트가 부모 컨테이너의 크기에 맞게 반응형으로 조절되도록 합니다. */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={dummyData} // 차트에 사용될 데이터
          margin={{ // 차트 여백 설정
            top: 5,
            right: 30,
            left: 40,
            bottom: 5,
          }}
        >
          {/* 차트 배경에 격자무늬를 추가합니다. */}
          <CartesianGrid strokeDasharray="3 3" stroke="#555" />
          {/* X축을 설정합니다. dataKey는 데이터에서 x축으로 사용할 값의 키입니다. */}
          <XAxis dataKey="date" stroke="#ccc" />
          {/* Y축을 설정합니다. tickFormatter로 축의 값을 포맷합니다. */}
          <YAxis 
            stroke="#ccc"
            tickFormatter={formatYAxis} 
            domain={['dataMin - 5000', 'dataMax + 5000']} // Y축의 범위를 데이터의 최소/최대값보다 약간 넓게 설정
          />
          {/* 마우스를 올렸을 때 표시될 툴팁을 설정합니다. content 속성에 커스텀 컴포넌트를 전달합니다. */}
          <Tooltip content={<CustomTooltip />} />
          {/* 라인(그래프)을 설정합니다. */}
          <Line 
            type="monotone" // 라인을 부드러운 곡선으로 만듭니다.
            dataKey="price" // 데이터에서 y축으로 사용할 값의 키입니다.
            stroke="#2ecc71" // 라인 색상 (긍정적인 느낌의 녹색)
            strokeWidth={2} // 라인 두께
            dot={false} // 각 데이터 포인트에 점을 표시하지 않습니다.
            activeDot={{ r: 6 }} // 마우스를 올렸을 때 활성화되는 점의 반지름을 6으로 설정합니다.
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Chart;

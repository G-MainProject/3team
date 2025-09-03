# C:\Users\3CLASS_008\Documents\GitHub\3team\Python\Prediction\sales_predictor.py
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler

class SalesPredictor:
    """
    과거 분기별 매출 데이터를 기반으로 다음 분기 매출을 예측하는 클래스.
    TensorFlow/Keras의 LSTM 모델을 사용합니다.
    """
    def __init__(self, look_back=4):
        """
        예측기 초기화
        :param look_back: 예측에 사용할 과거 데이터의 기간 (분기 수). 예: 4 -> 과거 4분기 데이터로 다음 1분기를 예측
        """
        self.look_back = look_back
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def _create_dataset(self, dataset):
        """
        시계열 데이터를 LSTM 학습용 데이터셋으로 변환
        """
        data_x, data_y = [], []
        for i in range(len(dataset) - self.look_back):
            data_x.append(dataset[i:(i + self.look_back), 0])
            data_y.append(dataset[i + self.look_back, 0])
        return np.array(data_x), np.array(data_y)

    def train(self, sales_data, epochs=100, batch_size=1, verbose=0):
        """
        주어진 매출 데이터로 LSTM 모델을 학습시킵니다.
        :param sales_data: 분기별 매출 데이터 (list or pandas Series)
        :param epochs: 학습 반복 횟수
        :param batch_size: 배치 크기
        :param verbose: 학습 과정 출력 여부
        """
        # 1. 데이터 전처리 (Scaling)
        sales_data = np.array(sales_data).reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(sales_data)

        # 2. 학습 데이터셋 생성
        train_x, train_y = self._create_dataset(scaled_data)

        # LSTM 입력 형식에 맞게 데이터 형태 변경: [samples, time steps, features]
        train_x = np.reshape(train_x, (train_x.shape[0], train_x.shape[1], 1))

        # 3. LSTM 모델 구축
        self.model = Sequential()
        self.model.add(LSTM(units=50, input_shape=(self.look_back, 1)))
        self.model.add(Dense(units=1))
        self.model.compile(optimizer='adam', loss='mean_squared_error')

        # 4. 모델 학습
        self.model.fit(train_x, train_y, epochs=epochs, batch_size=batch_size, verbose=verbose)

    def predict_next_quarter(self, last_quarters_data):
        """
        학습된 모델로 다음 분기 매출을 예측합니다.
        :param last_quarters_data: 예측에 사용할 직전 분기들의 매출 데이터 (look_back 개수만큼 필요)
        :return: 예측된 다음 분기 매출액
        """
        if self.model is None:
            raise Exception("모델이 학습되지 않았습니다. train() 메소드를 먼저 호출해주세요.")
        
        if len(last_quarters_data) != self.look_back:
            raise ValueError(f"입력 데이터는 {self.look_back}개의 분기 데이터여야 합니다.")

        # 1. 입력 데이터 전처리
        input_data = np.array(last_quarters_data).reshape(-1, 1)
        scaled_input = self.scaler.transform(input_data)

        # 2. 예측
        # LSTM 입력 형식에 맞게 데이터 형태 변경
        reshaped_input = np.reshape(scaled_input, (1, self.look_back, 1))
        predicted_scaled_value = self.model.predict(reshaped_input)

        # 3. 예측 결과 역정규화 (원래 스케일로 복원)
        predicted_value = self.scaler.inverse_transform(predicted_scaled_value)

        return predicted_value[0][0]

# --- 예제 사용법 ---
if __name__ == '__main__':
    # 가상의 16분기(4년) 매출 데이터 (단위: 억 원)
    # 실제로는 API를 통해 특정 종목의 과거 재무 데이터를 가져와야 합니다.
    sample_sales = [
        100, 110, 105, 120,  # 1년차
        130, 145, 135, 150,  # 2년차
        160, 170, 165, 180,  # 3년차
        190, 205, 195, 210   # 4년차
    ]

    # 1. 예측기 생성 (과거 4분기 데이터 사용)
    predictor = SalesPredictor(look_back=4)

    # 2. 모델 학습
    print("매출 예측 모델을 학습 중입니다...")
    predictor.train(sample_sales)
    print("모델 학습 완료.")

    # 3. 다음 분기(5년차 1분기) 매출 예측
    # 예측을 위해 가장 최근 4분기 데이터(4년차 1~4분기)를 입력으로 사용
    last_4_quarters = sample_sales[-4:]
    predicted_sales = predictor.predict_next_quarter(last_4_quarters)

    print("\n--- 매출 예측 결과 ---")
    print(f"과거 4분기 매출: {last_4_quarters}")
    print(f"예측된 다음 분기 매출: {predicted_sales:.2f} (억 원)")
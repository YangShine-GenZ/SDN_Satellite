import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
import tensorflow
from keras.models import Sequential
from keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error

df=pd.read_csv('Geant.csv')

data_columns = list(df.columns.values)
data_columns.remove('Column1')
dataset = df[data_columns].values.astype('float32')
print(dataset)

scaler = MinMaxScaler(feature_range=(0, 1))
dataset = scaler.fit_transform(dataset)
train_size = int(len(dataset) * 0.8)
train_size=263
test_size = len(dataset) - train_size
train_data = dataset[0:train_size,:]
test_data = dataset[train_size:len(dataset),:]
print(test_data)

def create_dataset(dataset):
    dataX, dataY = [], []
    for i in range(len(dataset)-10):
	    a = dataset[i:i+10, :]
	    dataX.append(a)
	    dataY.append(dataset[i + 10, :])
    return np.array(dataX), np.array(dataY)


trainX, trainY = create_dataset(train_data)
print(trainX)
testX, testY = create_dataset(test_data)


lstm_model = Sequential()
lstm_model.add(LSTM(500,input_shape=(trainX.shape[1], trainX.shape[2]), activation='relu'))
lstm_model.add(Dense(500, activation='relu'))
lstm_model.add(Dense(500, activation='relu'))
lstm_model.add(Dense(500, activation='relu'))
lstm_model.add(Dense(500, activation='relu'))
lstm_model.add(Dense(500, activation='relu'))
lstm_model.add(Dense(529, activation='relu'))
lstm_model.compile(loss='mean_squared_error', optimizer='adam')
print(lstm_model.summary())

lstm_3=lstm_model.fit(trainX, trainY, epochs=20, validation_split=0.2)


plt.rcParams["figure.figsize"] = (20,10)
plt.rcParams.update({'font.size': 10, 'font.weight' : 'bold'})
plt.plot(lstm_3.history['loss'], label='train')
plt.plot(lstm_3.history['val_loss'], label='validation')
plt.ylabel('Loss', fontweight='bold', fontsize=10)
plt.xlabel('Epoch', fontweight='bold', fontsize = 10)
plt.xticks(range(0,21))
plt.legend()
plt.show()


predY = lstm_model.predict(testX)
mse = mean_squared_error(predY, testY)
print('MSE: %.5f' % mse)

inv_predY=scaler.inverse_transform(predY)
inv_predY.shape
inv_testY=scaler.inverse_transform(testY)
inv_predY_0 = inv_predY[10,:]
inv_predY_0.shape

inv_testY_0 = inv_testY[10, :]
inv_testY_0.shape

plt.rcParams["figure.figsize"] = (80,30)
plt.rcParams.update({'font.size': 10, 'font.weight' : 'bold'})
plt.plot(inv_predY_0[0:600], label = "Prediction")
plt.plot(inv_testY_0[0:600], label = "Ground-truth")
plt.xlabel('Time(s)', fontweight='bold', fontsize=10)
plt.ylabel('Throughput (kB/s)', fontweight='bold', fontsize = 10)
plt.legend()
plt.show()
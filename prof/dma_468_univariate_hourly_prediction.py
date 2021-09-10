# -*- coding: utf-8 -*-
"""DMA_468_univariate_hourly prediction.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19pAT1W62-CNvwTp4M_e_0sXjfjE6JgZK
"""

pip install pmdarima

from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession

config = ConfigProto()
config.gpu_options.allow_growth = True
session = InteractiveSession(config=config)

# Commented out IPython magic to ensure Python compatibility.
# importing libraries
import pandas as pd
import matplotlib.pyplot as plt
# %matplotlib inline
import numpy as np
import seaborn as sns
import matplotlib as mpl
from datetime import datetime
import plotly.express as px
import tensorflow as tf
from tensorflow import keras
from keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import Activation
from math import sqrt
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error

np.random.seed(42)
tf.random.set_seed(42)

# Mounting the drive
from google.colab import drive
drive.mount('/content/gdrive')

ls'/content/gdrive/My Drive/Thesis'

data = pd.read_csv("/content/gdrive/My Drive/Thesis/DMA_468.csv")
data['Date-time'] = pd.to_datetime(data['Date-time'], dayfirst=True, errors='coerce')
data.rename( columns={'Flow':'DMA_468','Date-time':'Date_time'}, inplace=True )
data_DMA468 = data[['Date_time','DMA_468']]

figure = px.line(data_DMA468,x="Date_time",y="DMA_468",title="DMA_468 with slider")
figure.update_xaxes(rangeselector=dict(
            buttons=list([
                dict(count=1,
                     label="12m",
                     step="month",
                     stepmode="backward"),
                dict(count=2,
                     label="8m",
                     step="month",
                     stepmode="backward"),
                dict(count=3,
                     label="4m",
                     step="month",
                     stepmode="backward"),
                dict(step="all")
            ])
        ),
        rangeslider=dict(
            visible=True
        )
    )
figure.show()

data_DMA468.dropna(subset = ["DMA_468"], inplace=True)

data_DMA468_indexed = data_DMA468.set_index('Date_time')
# Making hourly data 
hourly_data = data_DMA468_indexed.resample('h').sum()
hourly_data.shape
hourly_data_index = hourly_data.reset_index()

from sklearn.ensemble import IsolationForest
model =  IsolationForest()
model.fit(hourly_data_index[['DMA_468']])

score=model.decision_function(hourly_data_index[['DMA_468']])

hourly_data_index['scores'] = score
hourly_data_index_final = hourly_data_index[hourly_data_index.scores >-0.25]
final_df = hourly_data_index_final[['Date_time','DMA_468']]

hourly_data_index_final.shape

final_df.shape

figure = px.line(final_df,x="Date_time",y="DMA_468",title="DMA_468 with slider")
figure.update_xaxes(rangeselector=dict(
            buttons=list([
                dict(count=1,
                     label="12m",
                     step="month",
                     stepmode="backward"),
                dict(count=2,
                     label="8m",
                     step="month",
                     stepmode="backward"),
                dict(count=3,
                     label="4m",
                     step="month",
                     stepmode="backward"),
                dict(step="all")
            ])
        ),
        rangeslider=dict(
            visible=True
        )
    )
figure.show()

#Statistical information
final_df.describe()

final_df1 = final_df.set_index('Date_time')
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import kpss

# Augmented Dickey-Fuller test
#Null Hypothesis (H0): If failed to be rejected, meaning it is non-stationary. It has some time dependent structure.
#Alternate Hypothesis (H1): The null hypothesis is rejected;  meaning it is stationary. It does not have time-dependent structure.

ADF_Check_Stationary = adfuller(final_df1)
print('ADF Statistic: %f' % ADF_Check_Stationary[0])
print('p-value: %f' % ADF_Check_Stationary[1])
print('Critical Values:')
for key, value in ADF_Check_Stationary[4].items():
	print('\t%s: %.3f' % (key, value))

"""Observation :

1.The ADF statistic value of -10.7. The more negative this statistic, the more likely we are to reject the null hypothesis (we have a stationary dataset).

2.p value - 0.000 < 0.05 ; Data is stationary
"""

#Kwiatkowski-Phillips-Schmidt-Shin test
#Null Hypothesis (H0): stationary.
#Alternate Hypothesis (H1): non-stationary

KPSS_Check_Stationary = kpss(final_df1)
KPSS_Check_Stationary

"""Observation : 1.The ADF statistic value of 0.17. The positive value is statistic, and hence we have a stationary dataset"""

import statsmodels.api as sm
res=sm.tsa.seasonal_decompose(final_df1,period=24)
fig = res.plot()
fig.set_figheight(10)
fig.set_figwidth(18)
plt.show()

"""# Baseline model"""

# Making a df
Original = final_df1["DMA_468"].to_frame().rename(columns = {"DMA_468": "Original" })
Forecast  = final_df1["DMA_468"].to_frame().shift(1).rename(columns = {"DMA_468": "Forecast" })
baseline = pd.concat([Original,Forecast],axis=1)
final = baseline[1:]#there is no prediction for first row due to shifting.
# Calculate the RMSE
rmse = np.sqrt(mean_squared_error(final.Original, final.Forecast))
rmse = round(rmse, 3)
print (" The root mean square value on dataset: ",rmse)

baseline_model = final[['Forecast']]
baseline_model.plot(grid=True)
plt.figure(figsize=(22,10))

final.plot(figsize=(20,10))

final.iloc[-2620:]

baseline_graph = final[-2620:]
rmse1 = np.sqrt(mean_squared_error(baseline_graph.Original, baseline_graph.Forecast))
rmse1 = round(rmse1, 3)
print (" The root mean square value on dataset using baseline model: ",rmse1)
baseline_graph.plot(figsize=(12,8))

"""# LSTM"""

# Split train data and test data
train_size = int(len(final_df1)*0.7)

#train_data = df.WC.loc[:train_size] -----> it gives a series
# Do not forget use iloc to select a number of rows
train_data = final_df1.iloc[:train_size]
test_data = final_df1.iloc[train_size:]

train_data.shape

test_data.shape

scaler = MinMaxScaler(feature_range=(0, 1))
train_scaled = scaler.fit_transform(train_data)
test_scaled = scaler.fit_transform(test_data)

def data_preparation(array_dataset, look_back=1, future=1, index=0):
    features = array_dataset.shape[1]
    arr_X, arr_Y = [], []
    if len(array_dataset) - look_back <= 0:
        arr_X.append(array_dataset)
    else:
        for i in range(len(array_dataset) - look_back - future):
            arr_Y.append(array_dataset[(i + look_back):(i + look_back + future), index])
            arr_X.append(array_dataset[i:(i + look_back)])
    arr_X, arr_Y = np.array(arr_X), np.array(arr_Y)
    arr_X = np.reshape(arr_X, (arr_X.shape[0], look_back, features))
    return arr_X, arr_Y

look_back = 12
features = 1
X_train1, Y_train1 = data_preparation(train_scaled, look_back=12, future=24, index=0)
X_test1, Y_test1 = data_preparation(test_scaled, look_back=12, future=24, index=0)

X_train = X_train1.reshape((X_train1.shape[0],X_train1.shape[1],1))
X_test = X_test1.reshape( (X_test1.shape[0],X_test1.shape[1],1))

print('X_train shape:',X_train.shape)
print('Y_train shape:',Y_train.shape)
print('X_test shape:',X_test.shape)
print('Y_test shape:',Y_test.shape)

model8 = tf.keras.Sequential()
model8.add(LSTM(150,return_sequences=True,input_shape=(look_back,features)))
model8.add(Dropout(0.45))
model8.add(LSTM(120,return_sequences=True))
model8.add(Dropout(0.35))
model8.add(LSTM(100))
model8.add(Dropout(0.25))
model8.add(Dense(24))
model8.compile(loss='mean_squared_error', optimizer='adam')
history8=model8.fit(X_train,Y_train,validation_data=(X_test,Y_test),epochs=200,batch_size=100)

# Plot train loss and validation loss
def plot_loss (history, model_name):
    plt.figure(figsize = (10, 6))
    plt.plot(history8.history['loss'])
    plt.plot(history8.history['val_loss'])
    plt.title('Model Train vs Validation Loss for ' + model_name)
    plt.ylabel('Loss')
    plt.xlabel('epoch')
    plt.legend(['Train loss', 'Validation loss'], loc='upper right')

plot_loss(history8,'LSTM')

# Generate predictions
train_pred = model8.predict(X_train)
#evaluation = model.evaluate(x=X_test, y=y_test, verbose=1)
test_pred = model8.predict(X_test)
predictions = test_pred

final_df2= final_df1.reset_index()

# To make a dataframe of original and predicted value:
lstm_df=[]
for i in range (0, len(predictions)):
  lstm_df.append((predictions[i][0]))
#final_df = pd.DataFrame((y_test[0]))
final_data = pd.DataFrame((Y_test))
final_data.rename(columns = {0:'original_value'}, inplace = True)
final_data['predicted_value'] = lstm_df

import math
from sklearn.metrics import mean_squared_error
testset = math.sqrt(mean_squared_error(final_data['original_value'], final_data['predicted_value']))
print("The RMSE prediction value on testset: ",testset)

# Comparing the forecasts with the actual values
yhat = [x[0] for x in model2.predict(X_test)]
y = [y[0] for y in Y_test]
# Creating the frame to store both predictions
days = final_df2[['Date_time']].values[-len(y):]
df = pd.DataFrame(days,columns = ['Date_time'])
result = pd.concat([df, final_data], axis=1, join='inner')
result.shape

# Plotting original and predicted graph:
plt.figure(figsize=(20, 12))
plt.plot(result.Date_time, result.original_value, color='red', label='original')
plt.plot(result.Date_time, result.predicted_value, color='blue', label='forecast', alpha=0.7)
plt.title('Originial vs forecast')
plt.legend()
plt.show()

df.to_csv('raw_data.csv', index=False)
df.to_excel('raw_data.xls', index=False)

from google.colab import files

# e.g. save pandas output as csv
result.to_csv('DMA_468_ULSTM_hp.csv')

# or any other file as usual
# with open('example.csv', 'w') as f:
#   f.write('your strings here')

files.download('DMA_468_ULSTM_hp.csv')
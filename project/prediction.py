import datetime
import pandas as pd
import numpy as np
import math

from statsmodels.tsa.api import VAR
from statsmodels.tsa.ar_model import AutoReg, ar_select_order
from statsmodels.tools.eval_measures import mse
from influxdb_client import InfluxDBClient

from constants import INFLUXDB




def __get_data():
    query = ' from(bucket: "' + INFLUXDB['BUCKET'] + '")\
            |> range(start: -24h)\
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")\
            |> keep(columns: ["_time", "weight", "temperature", "humidity"]) '
    
    query_api = InfluxDBClient(url=INFLUXDB['URL'], token=INFLUXDB['TOKEN'], org=INFLUXDB['ORG']).query_api()

    result = query_api.query_data_frame(org=INFLUXDB['ORG'], query=query)

    result['_time'] = result['_time'].apply(lambda x: x.replace(microsecond=0))
    result = result.drop(['result', 'table'], axis=1)
    result = result.set_index('_time')
    result.index.name = 'time'
    result = result.sort_index()
    
    return result

def __delete_data():
    start = "1970-01-01T00:00:00Z"
    stop = "2030-01-01T00:00:00Z"
    client = InfluxDBClient(url=INFLUXDB['URL'], token=INFLUXDB['TOKEN'])
    delete_api = client.delete_api()
    delete_api.delete(start, stop, '_measurement="water_bowl"', bucket=INFLUXDB['FORECAST_BUCKET'], org=INFLUXDB['ORG'])
    client.close()




def __insert_forecast_on_weight(df_weight):
    df_weight_freq = pd.infer_freq(pd.to_datetime(df_weight.index))
    if df_weight_freq is None:
        df_weight_pred_len = math.ceil(pd.to_timedelta("1D") / pd.to_timedelta(np.diff(df_weight.index).min()))
    else:
        df_weight_pred_len = math.ceil(pd.to_timedelta("1D") / pd.to_timedelta(df_weight_freq if df_weight_freq[0].isdecimal() else '1' + df_weight_freq))
        df_weight = df_weight.asfreq(df_weight_freq)

    auto_lags = ar_select_order(df_weight, int(len(df_weight)/2-1)).ar_lags
    model = AutoReg(df_weight, auto_lags).fit()

    predictions = model.predict(start=len(df_weight), end=len(df_weight) + df_weight_pred_len)
    if df_weight_freq is None:
        df_predict_time = [ df_weight.index[-1] + i * pd.to_timedelta(np.diff(df_weight.index).min()) for i in range(len(predictions)) ]
        df_predictions = pd.DataFrame({'weight': predictions.values}, df_predict_time)
    else:
        df_predictions = pd.DataFrame({'weight': predictions.values}, predictions.index)
    df_predictions.index.name = 'time'
    
    print(df_predictions)

    with InfluxDBClient(url=INFLUXDB['URL'], token=INFLUXDB['TOKEN'], org=INFLUXDB['ORG']) as _client:
        with _client.write_api() as _write_api:
            _write_api.write(INFLUXDB['FORECAST_BUCKET'], INFLUXDB['ORG'], record=df_predictions, data_frame_measurement_name="water_bowl")

def __insert_forecast_on_all(df_all):
    if len(df_all) < 20: return None

    df_all_freq = pd.infer_freq(pd.to_datetime(df_all.index))
    if df_all_freq is not None:
        df_all_pred_len = math.ceil(pd.to_timedelta("1D") / pd.to_timedelta(df_all_freq if df_all_freq[0].isdecimal() else '1' + df_all_freq))
        df_all = df_all.asfreq(df_all_freq)
    else:
        df_all_pred_len = math.ceil(pd.to_timedelta("1D") / pd.to_timedelta(np.diff(df_all.index).min()))

    model = VAR(df_all)
    results = model.fit(maxlags=int(len(df_all)/7))
    forecast = results.forecast(df_all.values, df_all_pred_len)

    df_all_freq = pd.infer_freq(df_all.index)
    df_forecast_time = [ df_all.index[-1] + i * pd.to_timedelta(np.diff(df_all.index).min()) for i in range(len(forecast)) ]
    df_forecast = pd.DataFrame(forecast, columns=df_all.columns, index=df_forecast_time)
    df_forecast = df_forecast.drop(['temperature', 'humidity'], axis=1)
    df_forecast.index.name = 'time'

    print(df_forecast)
    
    with InfluxDBClient(url=INFLUXDB['URL'], token=INFLUXDB['TOKEN'], org=INFLUXDB['ORG']) as _client:
        with _client.write_api() as _write_api:
            _write_api.write(INFLUXDB['FORECAST_BUCKET'], INFLUXDB['ORG'], record=df_forecast, data_frame_measurement_name="water_bowl")




def __predict_refill_on_weight(alarm_level, df_weight):
    if df_weight['weight'].iloc[-1] <= alarm_level:
        t = datetime.datetime.strptime("00:00:00","%H:%M:%S")
        return datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    
    auto_lags = ar_select_order(df_weight, int(len(df_weight)/2-1)).ar_lags
    model = AutoReg(df_weight, auto_lags).fit()

    initial_time = df_weight.index[-1].to_pydatetime()
    curr_time = initial_time
    it = 0
    while (curr_time - initial_time).total_seconds() < 86400:
        predictions = model.predict(start=it*10+len(df_weight), end=it*10+9+len(df_weight))
        for i, pred in predictions.items():
            if pred <= alarm_level:
                return i.to_pydatetime() - initial_time
        
        it += 1
        curr_time = list(predictions.items())[-1][0].to_pydatetime()

    t = datetime.datetime.strptime("23:59:59","%H:%M:%S")
    return datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


def __predict_refill_on_all(alarm_level, df_all):
    if df_all['weight'].iloc[-1] <= alarm_level:
        t = datetime.datetime.strptime("00:00:00","%H:%M:%S")
        return datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    
    if len(df_all) < 20: return None
    
    model = VAR(df_all)
    #model.select_order(int(len(df_all)/20))
    results = model.fit(maxlags=int(len(df_all)/7))
    freq = pd.to_timedelta(np.diff(df_all.index).min()).total_seconds()
    forecast = results.forecast(df_all.values, int(86400 / freq))
    df_forecast = pd.DataFrame(forecast, columns=df_all.columns)

    sec = freq
    for i, pred in df_forecast['weight'].items():
        if pred <= alarm_level:
            return datetime.timedelta(0, sec)
        sec += freq

    t = datetime.datetime.strptime("23:59:59","%H:%M:%S")
    return datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)




def __mse_predict_on_weight(df_weight):
    df_train = df_weight.iloc[:int(0.8*len(df_weight))]
    df_test = df_weight.iloc[int(0.8*len(df_weight)):]

    auto_lags = ar_select_order(df_train, int(len(df_train)/2-1)).ar_lags
    model = AutoReg(df_train, auto_lags).fit()
    predictions = model.predict(start=len(df_train), end=len(df_weight)-1)
    
    return mse(predictions.array, df_test['weight'].array)

def __mse_predict_on_all(df_all):
    if len(df_all) < 20: return None

    df_train = df_all.iloc[:int(0.8*len(df_all))]
    df_test = df_all.iloc[int(0.8*len(df_all)):]
    
    model = VAR(df_all)
    #model.select_order(int(len(df_all)/20))
    results = model.fit(maxlags=int(len(df_train)/7))
    forecast = results.forecast(df_train.values, len(df_all)-len(df_train))
    df_forecast = pd.DataFrame(forecast, columns=df_train.columns)

    return mse(df_forecast['weight'].array, df_test['weight'].array)


if __name__ == "__main__":
    ### Generate dummy data
    #alarm_level = 200
    #curr_time = datetime.datetime.now()
    #time = [ curr_time + datetime.timedelta(0, t*60) for t in range(20) ]
    #weight = [ w for w in range(2500, 500, -100) ]
    #temperature = [ t for t in range(40 , 20, -1) ]
    #humidity = [ h for h in range(50, 30, -1) ]
    #df_all = pd.DataFrame({'weight': weight, 'temperature': temperature, 'humidity': humidity}, time)
    #df_all = df_all.asfreq(pd.infer_freq(df_all.index))

    ### Get real data
    df_all = __get_data()

    print(df_all)

    ### Write forecasted data to InfluxDB
    #__insert_forecast_on_all(df_all)
    #__insert_forecast_on_weight(df_all.drop(['temperature', 'humidity'], axis=1))

    ### Delete forecasted data from InfluxDB
    #__delete_data()

    ### Get MSE of forecast
    #__mse_predict_on_all(df_all)
    #__mse_predict_on_weight(df_all.drop(['temperature', 'humidity'], axis=1))

    ### Get forecasted time to next refill
    #__predict_refill_on_all(df_all)
    #__predict_refill_on_weight(df_all.drop(['temperature', 'humidity'], axis=1))

import requests
import zipfile
import io
import datetime
import numpy as np
import pandas as pd
import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting import Baseline, NBeats, TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer,NaNLabelEncoder
from pytorch_forecasting.metrics import *
from pytorch_forecasting.models.temporal_fusion_transformer.tuning import optimize_hyperparameters
import tensorflow as tf 
import tensorboard as tb 
from pytorch_forecasting.models.temporal_fusion_transformer.tuning import optimize_hyperparameters
import pickle
tf.io.gfile = tb.compat.tensorflow_stub.io.gfile

def get_forecasted_data():
    housing = pd.read_csv('MLS_Datasets/all_cities.csv', index_col=0).reset_index(drop=True)
    # preprocess the data
    month = [x[0] for x in housing['Date'].str.split("'")]
    year = [x[1] for x in housing['Date'].str.split("'")]
    year = ['19'+x if x[0] == '9' else '20'+x for x in year]
    housing['Date'] = pd.to_datetime(pd.Series(month).str.strip() + '/' + pd.Series(year))
    housing['Month'] = housing['Date'].dt.month
    housing['Year'] = housing['Date'].dt.year
    df = housing[housing['HomeType'] != 'All values']

    df.loc[df["Average SP/LP"] == 770000, ['Average SP/LP']] = 1 # change apparent outlier

    # it's possible that the median would be the more appropriate metric for these features especially if there is skew
    # this would highly depend on the city+hometype combination
    df_medians = df.groupby(['Geography','HomeType','Year'])[['Sales','Average Price','New Listings','SNLR','Active Listings','MOI','Average DOM','Average SP/LP']].transform('median')
    df['Median Sales of Year'] = df_medians['Sales']
    df['Sales YoY'] = df['Median Sales of Year'].pct_change(12)
    df['Median Price of Year'] = df_medians['Average Price']
    df['Price YoY'] = df['Median Price of Year'].pct_change(12)
    df['Median New Listings of Year'] =  df_medians['New Listings']
    df['New Listings YoY'] = df['Median New Listings of Year'].pct_change(12)
    df['Median SNLR of Year'] = df_medians['SNLR']
    df['SNLR YoY'] = df['Median SNLR of Year'].pct_change(12)
    df['Median Active Listings of Year'] =  df_medians['Active Listings']
    df['Active Listings YoY'] = df['Median Active Listings of Year'].pct_change(12)
    df['Median MOI of Year'] =  df_medians['MOI']
    df['MOI YoY'] = df['Median MOI of Year'].pct_change(12)
    df['Median DOM of Year'] =  df_medians['Average DOM']
    df['DOM YoY'] = df['Median DOM of Year'].pct_change(12)
    df['Median SP/LP of Year'] =  df_medians['Average SP/LP']
    df['SP/LP YoY'] = df['Median SP/LP of Year'].pct_change(12)
    # need to impute 0's for beginning year 1996
    df.loc[df['Year'] == 1996, ['Sales YoY', 'Price YoY', 'New Listings YoY', 'SNLR YoY', 'Active Listings YoY', 'MOI YoY', 'DOM YoY', 'SP/LP YoY']] = 0

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    # add additional data
    url = 'https://www150.statcan.gc.ca/n1/tbl/csv/34100145-eng.zip'
    request = requests.get(url)
    file_ = zipfile.ZipFile(io.BytesIO(request.content))
    file_.extractall('MLS_Datasets')
    # read additional datasets
    # lending rates data
    rates_df = pd.read_csv('MLS_Datasets/34100145.csv', usecols=['REF_DATE','VALUE'])
    rates_df['REF_DATE'] = pd.to_datetime(rates_df['REF_DATE']) # change to datetime format
    rates_df.rename(columns={'REF_DATE':'Date','VALUE':'Lending Rate'}, inplace=True)

    df = df.merge(rates_df, on='Date', how='left') # left join to add the extra column 
    df['Lending Rate'].fillna(method='ffill',inplace=True)

    # population projections dataset
    pop_df = pd.read_excel('MLS_Datasets/ministry_of_finance_population_projections_for_ontario_census_divisions_2020-2046.xlsx',engine='openpyxl',skiprows=4).dropna().reset_index(drop=True)
    pop_df['REGION NAME'] = pop_df['REGION NAME'].str.strip()  # remove whitespaces
    pop_df.rename(columns={'REGION NAME':'Municipality','TOTAL':'Population Projection 2020','YEAR (JULY 1)':'Year'}, inplace=True)
    df['Municipality'] = df['Municipality'].str.upper()
    pop_df['Municipality'] = pop_df['Municipality'].str.upper() # conform names
    pop_df = pop_df[(pop_df['Municipality'].isin(df['Municipality'].unique())) & (pop_df['SEX'] == 'TOTAL') & (pop_df['Year'] == 2020)].reset_index(drop=True)
    pop_df = pop_df[['Municipality','Population Projection 2020']]
    df = df.merge(pop_df,on=['Municipality'], how = 'left') # the added variable will be a static real since it is only for 2020 however 2021 can be added once the data is uploaded 

    # add time index
    df['time_idx'] = df['Date'].dt.year *12 + df['Date'].dt.month
    df['time_idx'] -= df['time_idx'].min()
    # create feature to get count of time_idx in case of missing time sequences
    df['count_idx'] = df.groupby(['Geography','HomeType'])['time_idx'].transform('count')
    # filter out time series with missing sequences
    df = df[df['count_idx'] >= df.count_idx.max()] # set a threshold of missing sequences
    df['Month'] = df['Month'].astype(str).astype('category')
    df['Year'] = df['Year'].astype(str).astype('category')
    df["avg_price_by_munic"] = df.groupby(["time_idx", "Municipality"], observed=True)['Average Price'].transform("mean")
    df["avg_price_by_hometype"] = df.groupby(["time_idx", "HomeType"], observed=True)['Average Price'].transform("mean")
    df["avg_price_by_geo"] = df.groupby(["time_idx", "Geography"], observed=True)['Average Price'].transform("mean")
    df.reset_index(drop=True, inplace=True)

    start_date = df.Date.dt.date.max()
    end_date = datetime.date(df.Date.dt.year.max(), 12, 1)
    max_prediction_length = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) # remaining number of months in the year

    # max_prediction_length = 12
    max_encoder_length = 48
    training_cutoff = df["time_idx"].max() - max_prediction_length

    training = TimeSeriesDataSet(
        df[lambda x: x.time_idx <= training_cutoff],
        time_idx="time_idx",
        target="Average Price",
        group_ids=["Municipality","Geography", "HomeType"],
        min_encoder_length=max_encoder_length // 2,  # keep encoder length long (as it is in the validation set)
        max_encoder_length=max_encoder_length,
        min_prediction_length=1,
        max_prediction_length=max_prediction_length,
        # lags={'Sales':[4],'Average DOM':[4],'New Listings':[4]},
        static_categoricals=["Municipality","Geography", "HomeType"],
        static_reals=["Population Projection 2020"],
        time_varying_known_categoricals=["Month"],
        variable_groups={},  # group of categorical variables can be treated as one variable
        time_varying_known_reals=["time_idx"],
        time_varying_unknown_categoricals=[],
        time_varying_unknown_reals=[
            "Sales",
            "Median Sales of Year",
            "Average Price",
            "Median Price of Year",
            "Dollar Volume",
            "New Listings",
            'Median New Listings of Year',
            "SNLR",
            'Median SNLR of Year',
            "Active Listings",
            'Median Active Listings of Year',
            "MOI",
            "Median MOI of Year",
            "Average DOM",
            'Median DOM of Year',
            "Average SP/LP",
            'Median SP/LP of Year',
            'Lending Rate',
            # "log_price"
            "avg_price_by_munic",
            "avg_price_by_hometype",
            "avg_price_by_geo"
        ],
        # target_normalizer=GroupNormalizer(
        #     groups=["Municipality","Geography", "HomeType"], transformation="softplus"
        # ),  # use softplus and normalize by group
        allow_missings = True,
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True
        
    )

    # create validation set (predict=True) which means to predict the last max_prediction_length points in time
    # for each series
    validation = TimeSeriesDataSet.from_dataset(dataset=training, data=df, predict=True, stop_randomization=True)

    # create dataloaders for model
    batch_size = 32  # set this between 32 to 128
    train_dataloader = training.to_dataloader(train=True, batch_size=batch_size, num_workers=0)
    val_dataloader = validation.to_dataloader(train=False, batch_size=batch_size, num_workers=0)

    # configure network and trainer
    pl.seed_everything(42)
    trainer = pl.Trainer(
        gpus=1,
        # clipping gradients is a hyperparameter and important to prevent divergance
        # of the gradient for recurrent neural networks
        gradient_clip_val=0.1,
    )


    tft = TemporalFusionTransformer.from_dataset(
        training,
        # not meaningful for finding the learning rate but otherwise very important
        learning_rate=0.03,
        hidden_size=16,  # most important hyperparameter apart from learning rate
        # number of attention heads. Set to up to 4 for large datasets
        attention_head_size=1,
        dropout=0.1,  # between 0.1 and 0.3 are good values
        hidden_continuous_size=8,  # set to <= hidden_size
        output_size=7,  # 7 quantiles by default
        loss=QuantileLoss(),
        # reduce learning rate if no improvement in validation loss after x epochs
        reduce_on_plateau_patience=4,
    )
    print(f"Number of parameters in network: {tft.size()/1e3:.1f}k")
    # configure network and trainer
    early_stop_callback = EarlyStopping(monitor="val_loss", verbose=False, mode="min")
    lr_logger = LearningRateMonitor()  # log the learning rate
    logger = TensorBoardLogger("/content/drive/MyDrive/data/Housing Data/lightning_logs")  # logging results to a tensorboard

    trainer = pl.Trainer(
        # default_root_dir = '/content/drive/MyDrive/data/Housing Data/checkpoints',
        max_epochs=60,
        gpus=1,
        weights_summary="top",
        gradient_clip_val=0.1,
        limit_train_batches=30,  # comment in for training, running valiation every 30 batches
        # fast_dev_run=True,  # comment in to check that networkor dataset has no serious bugs
        callbacks=[lr_logger, early_stop_callback],
        logger=logger,
    )


    tft = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=0.004,
        hidden_size=16,
        attention_head_size=1,
        dropout=0.1,
        hidden_continuous_size=8,
        output_size=7,  # 7 quantiles by default
        loss=QuantileLoss(),
        # log_interval=10,  # uncomment for learning rate finder and otherwise, e.g. to 10 for logging every 10 batches
        reduce_on_plateau_patience=4,
    )

    # fit network
    trainer.fit(
        tft,
        train_dataloader=train_dataloader,
        val_dataloaders=val_dataloader,
    )

    # create forecasted dataset
    # select last 24 months from data (max_encoder_length is 24)
    encoder_data = df[lambda x: x.time_idx > x.time_idx.max() - max_encoder_length]

    # select last known data point and create decoder data from it by repeating it and incrementing the month
    last_data = df[lambda x: x.time_idx == x.time_idx.max()]
    decoder_data = pd.concat(
        [last_data.assign(date=lambda x: x.Date + pd.offsets.MonthBegin(i)) for i in range(1, max_prediction_length + 1)],
        ignore_index=True,
    )

    # add time index consistent with "data"
    decoder_data["time_idx"] = decoder_data["Date"].dt.year * 12 + decoder_data["Date"].dt.month
    decoder_data["time_idx"] += encoder_data["time_idx"].max() + 1 - decoder_data["time_idx"].min()

    # adjust additional time feature(s)
    decoder_data["Month"] = decoder_data.Date.dt.month.astype(str).astype("category")  # categories have be strings

    # combine encoder and decoder data
    new_prediction_data = pd.concat([encoder_data, decoder_data], ignore_index=True)

    forecast,forecast_index = best_tft.predict(new_prediction_data, mode="prediction", return_index=True)
    new_df = pd.concat([forecast_index.drop(columns='time_idx'),pd.DataFrame(forecast.numpy())],axis=1,ignore_index=True)
    new_df.columns = ['Municipality','Geography','HomeType']+decoder_data['date'].dt.date.unique().tolist()

    df_2020 = df[df['Year'] == '2020'][['Municipality','Geography','HomeType','Median Price of Year']].drop_duplicates()
    df_2021 = df[df['Year'] == '2021'][['Date','Municipality','Geography','HomeType','Average Price']].drop_duplicates()
    df_2021 = df_2021.groupby(['Municipality','Geography','HomeType'])['Average Price'].apply(list).reset_index()
    new_df['all values'] = new_df[new_df.columns[3:]].apply(lambda x: list(x),axis=1)
    forecast_2021 = df_2021.merge(new_df[['Geography','HomeType','all values']], on = ['Geography','HomeType'])
    forecast_2021['full year'] = (forecast_2021['Average Price'] + forecast_2021['all values'])
    forecast_2021['Median Price of 2021'] = np.median(forecast_2021['full year'].tolist(), axis=1)
    # new_df['Median Price of 2021'] = new_df[new_df.columns[3:]].median(axis=1)

    forecast_merge = df_2020.merge(forecast_2021[['Municipality','Geography','HomeType','Median Price of 2021']], on =['Geography','HomeType'])
    forecast_merge['Price YoY'] = forecast_merge[['Median Price of Year','Median Price of 2021']].pct_change(axis=1)['Median Price of 2021']
    forecast_merge.sort_values(by='Price YoY', ascending=False).reset_index(drop=True).to_csv('forecast_merge.csv')
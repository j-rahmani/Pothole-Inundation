import pandas as pd
import numpy as np
import os
import datetime as dt
import copy
from scipy.stats import spearmanr,pearsonr

# from osgeo import gdal
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy
# import cartopy.feature

import cartopy.feature as cfeature

import matplotlib.pyplot as plt
import matplotlib.cm as cm 
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.gridspec import GridSpec 
from matplotlib import colors as mcolors  
from matplotlib.colors import ListedColormap
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.ticker import FormatStrFormatter

import warnings
warnings.filterwarnings("ignore")
import zipfile
#%% Unzip input datas

# unzip streamflow csv files
if not os.path.exists(os.path.join(os.getcwd(), "Data", "Streamflow")):
    with zipfile.ZipFile(os.path.join(os.getcwd(), "Data", "Streamflow.zip"), 'r') as zip_ref:
        zip_ref.extractall(os.path.join(os.getcwd(), "Data", "Streamflow"))


# unzip PPR boundary shapfile
if not os.path.exists(os.path.join(os.getcwd(), "Data", "PPR_shapefile")):
    with zipfile.ZipFile(os.path.join(os.getcwd(), "Data", "PPR_shapefile.zip"), 'r') as zip_ref:
        zip_ref.extractall(os.path.join(os.getcwd(), "Data", "PPR_shapefile"))

#%% Stations

station_df = pd.read_csv( os.path.join(os.getcwd(), "Data", "stations.txt"), delimiter='\t' )
stations = station_df['Station_code'].values
station_df.set_index('Station_code', inplace=True)


outdir = os.path.join(os.getcwd(), "Outputs")
if not os.path.exists(outdir):
    os.makedirs(outdir)


os.environ["SHAPE_RESTORE_SHX"] = "YES"
prairie_watershed = gpd.read_file( os.path.join(os.getcwd(), "Data", "PPR_shapefile", "PPR_Watershed.shp") )
prairie_watershed = prairie_watershed.to_crs(epsg=4326) # Reproject shapefile to EPSG:4326
#%% Climatic Data Reading
attrs_df = pd.read_csv( os.path.join(os.getcwd(), "Data",'Features_USGS_HYDAT.txt'), delimiter='\t')

#Prec
prec_df = pd.read_csv(os.path.join(os.getcwd(), "Data",'tp_daily_USGS_HYDAT.txt'), delimiter='\t')
prec_df['date'] = pd.to_datetime(prec_df[['year', 'month', 'day']])
prec_df.set_index('date', inplace=True)
prec_df.drop(columns=['year', 'month', 'day'], inplace=True)

prec_df = prec_df* 1000  #convert m to mm


#PET
pet_df = pd.read_csv(os.path.join(os.getcwd(), "Data",'pet_USGS_HYDAT_daily.txt'), delimiter='\t')
pet_df['date'] = pd.to_datetime(pet_df[['year', 'month', 'day']])
pet_df.set_index('date', inplace=True)
pet_df.drop(columns=['year', 'month', 'day'], inplace=True)


#Temp
temp_df = pd.read_csv(os.path.join(os.getcwd(), "Data",'t2m_daily_USGS_HYDAT.txt'), delimiter='\t')
temp_df['date'] = pd.to_datetime(temp_df[['year', 'month', 'day']])
temp_df.set_index('date', inplace=True)
temp_df.drop(columns=['year', 'month', 'day'], inplace=True)


# Rain/Snow Seperation
rainfall_df = prec_df.copy(deep=True)
rainfall_snowfall_T = temp_df < 0  #Snow mask
rainfall_df[rainfall_snowfall_T] = 0
snowfall_df = prec_df - rainfall_df



#%% Annual Climatic signatures 

#Prec
annual_mean_prec_df = prec_df.resample('YE').mean()
annual_max_prec_df = prec_df.resample('YE').max()
annual_P95_prec_df = prec_df.resample('YE').quantile(0.95)

#PET
annual_mean_pet_df = pet_df.resample('YE').mean()

#Temp
annual_mean_temp_df = prec_df.resample('YE').mean()

#Snow
annual_mean_snow_df = snowfall_df.resample('YE').mean()
annual_P95_snow_df = snowfall_df.resample('YE').quantile(0.95)
annual_Snow_Fraction = annual_mean_snow_df/annual_mean_prec_df

#Rain
annual_mean_rain_df = rainfall_df.resample('YE').mean()
annual_max_rain_df = rainfall_df.resample('YE').max()
annual_P95_rain_df = rainfall_df.resample('YE').quantile(0.95)

#Aridity
annual_Aridity = annual_mean_pet_df/annual_mean_prec_df


#%%  Streamflow Dataframe
TrainStartDate = dt.datetime(1984, 1, 1)  # Year, Month, Day # Training
TrainEndDate   = dt.datetime(2021, 12, 31)  # Year, Month, Day # Training

Train_range = [(TrainStartDate + dt.timedelta(days=x)).strftime('%Y/%m/%d') for x in range((TrainEndDate - TrainStartDate).days)]

streamflow_dir = os.path.join(os.getcwd(), "Data",'Streamflow')


discharge_df = pd.DataFrame({'date': Train_range}) # Create a DataFrame with the date column
discharge_df.set_index('date', inplace=True)


for i, st in enumerate(stations):

    strm_path = streamflow_dir + '/' + stations[i]+'_Daily_Flow_ts.csv'

    strmflw = pd.read_csv(strm_path, encoding='ISO-8859-1')  
    strmflw['Date'] = pd.to_datetime(strmflw['Date'], format='mixed')
    strmflw['Date'] = strmflw['Date'].dt.strftime('%Y/%m/%d')
    
    obs_df = pd.DataFrame({'Date': Train_range}) # Create a DataFrame with the date column
    obs_df_merged = pd.merge(obs_df, strmflw, how='left',on = 'Date' )
    
    try:    #HYDAT
        streamflow = obs_df_merged['Flow(m³/s)'].values
    except:    #USGS
        streamflow = obs_df_merged['Streamflow_cms'].values
        
    area = attrs_df[attrs_df['st_code'] == stations[i]]['Area_SqM'].values # m2
    
    
    discharge_df[st] = streamflow * (24 * 3600) / area * 1000 # convert cms to mm/day
    



discharge_df.index = pd.to_datetime(discharge_df.index)

annual_mean_discharge_df = discharge_df.resample('YE').mean()
annual_P95_discharge_df = discharge_df.resample('YE').quantile(0.95)
annual_P05_discharge_df = discharge_df.resample('YE').quantile(0.05)

recorded_obs_per_yr = discharge_df.resample('YE').count()
Minimum_annual_obs_filter = recorded_obs_per_yr[recorded_obs_per_yr>345]
num_of_yrs_with_minimum_obs= Minimum_annual_obs_filter.count()
St_with_at_least_20_yrs_obs = num_of_yrs_with_minimum_obs[num_of_yrs_with_minimum_obs>=20]

stations = St_with_at_least_20_yrs_obs.index.values
#%% Spot Annual

Inundation = pd.read_csv( os.path.join(os.getcwd(), "Data",'Inundation_USGS_HYDAT.txt'), delimiter='\t')
Inundation['month'] = 12
Inundation['day'] = 31
Inundation['date'] = pd.to_datetime(Inundation[['year', 'month', 'day']])
Inundation = Inundation.set_index('date')
Inundation = Inundation.drop(columns=['year', 'month', 'day'])


#%%% Monthly Net Precipitation (Rainfall + SnowMelt - AET)

ERA5_Monthly_SnowFall = pd.read_csv(os.path.join(os.getcwd(), "Data",'PPR_ERA5_SnowFall_Monthly_weighted_timeseries.csv'))
ERA5_Monthly_SnowMelt = pd.read_csv(os.path.join(os.getcwd(), "Data",'PPR_ERA5_SnowMelt_Monthly_weighted_timeseries.csv'))
ERA5_Monthly_AET = pd.read_csv(os.path.join(os.getcwd(), "Data",'PPR_ERA5_AET_Monthly_weighted_timeseries.csv'))
ERA5_Monthly_Total_Prec = pd.read_csv(os.path.join(os.getcwd(), "Data",'PPR_ERA5_TotalPrec_Monthly_weighted_timeseries.csv'))

ERA5_Monthly_SnowFall['date'] = pd.to_datetime(ERA5_Monthly_SnowFall['date'], format='%Y-%m-%d')
ERA5_Monthly_SnowMelt['date'] = pd.to_datetime(ERA5_Monthly_SnowMelt['date'], format='%Y-%m-%d')
ERA5_Monthly_AET['date'] = pd.to_datetime(ERA5_Monthly_AET['date'], format='%Y-%m-%d')
ERA5_Monthly_Total_Prec['date'] = pd.to_datetime(ERA5_Monthly_Total_Prec['date'], format='%Y-%m-%d')


ERA5_Monthly_SnowFall.set_index('date', inplace=True)
ERA5_Monthly_SnowMelt.set_index('date', inplace=True)
ERA5_Monthly_AET.set_index('date', inplace=True)
ERA5_Monthly_Total_Prec.set_index('date', inplace=True)

ERA5_Monthly_RainFall = ERA5_Monthly_Total_Prec - ERA5_Monthly_SnowFall

# Net Precipitation: Rainfall + Snowmelt - AET
ERA5_Monthly_NWI = ERA5_Monthly_RainFall + ERA5_Monthly_SnowMelt - ERA5_Monthly_AET
ERA5_Monthly_NWI = ERA5_Monthly_NWI[ERA5_Monthly_NWI.index <= TrainEndDate]

ERA5_Monthly_NWI_Max = ERA5_Monthly_NWI.resample('YE').max()
ERA5_Monthly_NWI_April =  ERA5_Monthly_NWI[ERA5_Monthly_NWI.index.month.isin([4])].resample('YE').mean()
ERA5_Monthly_NWI_Spring = ERA5_Monthly_NWI[ERA5_Monthly_NWI.index.month.isin([4, 5, 6])].resample('YE').mean() #April, May, June


# Net Input: Rainfall + Snowmelt
ERA5_Monthly_NetInput = ERA5_Monthly_RainFall + ERA5_Monthly_SnowMelt 
ERA5_Monthly_NetInput = ERA5_Monthly_NetInput[ERA5_Monthly_NetInput.index <= TrainEndDate]

ERA5_Monthly_NetInput_Max = ERA5_Monthly_NetInput.resample('YE').max()
ERA5_Monthly_NetInput_April =  ERA5_Monthly_NetInput[ERA5_Monthly_NetInput.index.month.isin([4])].resample('YE').mean()
ERA5_Monthly_NetInput_Spring = ERA5_Monthly_NetInput[ERA5_Monthly_NetInput.index.month.isin([4, 5, 6])].resample('YE').mean() #April, May, Jun


del ERA5_Monthly_SnowFall, ERA5_Monthly_SnowMelt, ERA5_Monthly_AET, ERA5_Monthly_Total_Prec
#%% Static features 
static_features_PPR = pd.read_csv(os.path.join(os.getcwd(), "Data","Static_Features.csv") , dtype=str)
static_features_PPR.rename(columns={'Unnamed: 0': 'st_code'}, inplace=True)
static_features_PPR = static_features_PPR.set_index('st_code')
static_features_PPR = static_features_PPR.astype(float)


#%% Snow presence
annual_Snow_Presence = pd.read_csv(os.path.join(os.getcwd(), "Data",'SnowPersistence.csv'))
annual_Snow_Presence['month'] = 12
annual_Snow_Presence['day'] = 31
annual_Snow_Presence['date'] = pd.to_datetime(annual_Snow_Presence[['year', 'month', 'day']])
annual_Snow_Presence = annual_Snow_Presence.set_index('date')
annual_Snow_Presence = annual_Snow_Presence.drop(columns=['year', 'month', 'day'])

#%% Long Term

long_term_mean_Prec = np.mean(prec_df, axis=0)
long_term_mean_Prec = long_term_mean_Prec[stations]

long_term_mean_PET = np.mean(pet_df, axis=0)
long_term_mean_PET = long_term_mean_PET[stations]

long_term_mean_discharge = np.mean(discharge_df, axis = 0)
long_term_mean_discharge = long_term_mean_discharge[stations]

long_term_Aridity = long_term_mean_PET/long_term_mean_Prec
long_term_Aridity=long_term_Aridity[stations]

long_term_Runoff_Ratio = long_term_mean_discharge/long_term_mean_Prec
long_term_Runoff_Ratio = long_term_Runoff_Ratio[stations]

long_term_Prec_95 = prec_df.quantile(0.95)
long_term_Prec_95 = long_term_Prec_95[stations]

long_term_discharge_95 = discharge_df.quantile(0.95)
long_term_discharge_95 = long_term_discharge_95[stations]

long_term_Runoff_Ratio_95 = long_term_discharge_95/long_term_Prec_95
long_term_Runoff_Ratio_95 = long_term_Runoff_Ratio_95[stations]


long_term_mean_Pekel = np.mean(Inundation*100, axis=0)
long_term_mean_Pekel = long_term_mean_Pekel[stations]

long_term_cv_Pekel = np.std(Inundation*100, axis=0) / np.mean(Inundation*100, axis=0) #Coeeficient of variation
long_term_cv_Pekel = long_term_cv_Pekel[stations]

long_term_atv_Pekel = np.ptp(Inundation*100, axis=0)  # absolute_total_variation: ptp() function calculates range (max - min)
long_term_atv_Pekel = long_term_atv_Pekel[stations]

long_term_Snow_Presence = np.mean(annual_Snow_Presence, axis=0)
long_term_Snow_Presence = long_term_Snow_Presence[stations]



#%% Filters

# Retain stations with long-term Runoff Ratio values less than 1.0
Runoff_Ratio_Filter = long_term_Runoff_Ratio[long_term_Runoff_Ratio < 1.0].to_frame(name='Runoff_Ratio')

# Retain stations with long-term inundation percentage values more than 0.1
Avg_Filter = long_term_mean_Pekel[long_term_mean_Pekel>0.1].to_frame(name='Inundation_Ave')

# Retain stations with long-term coefficient_of_variation more than 0.33
CV_Filter = long_term_cv_Pekel[long_term_cv_Pekel>0.00].to_frame(name='Inundation_CV')

# Merge the DataFrames based on their index and Retain only rows in both sets
Filtered_Stations = pd.merge(Avg_Filter, CV_Filter, how='inner', left_index=True, right_index=True)

Filtered_Stations = pd.merge(Filtered_Stations, Runoff_Ratio_Filter, how='inner', left_index=True, right_index=True)
#%% classification based on lonr-term inundation area percentage
class_A = Filtered_Stations[ (Filtered_Stations['Inundation_Ave']<1.0) & (Filtered_Stations['Inundation_Ave']>0.1) ]
class_B = Filtered_Stations[(Filtered_Stations['Inundation_Ave']>= 1.0) ]

class_A_stations = class_A.index.values
class_B_stations = class_B.index.values


#%% Partial Spearman Correlation
from sklearn.linear_model import LinearRegression

def Par_Spear_Corr(x, y, z):
    # Ensure z is reshaped for fitting with sklearn
    if z.ndim == 1:
        z = z.reshape((-1, 1))

    # Create linear regression models
    model_x = LinearRegression()
    model_y = LinearRegression()

    # Fit the models
    model_x.fit(z, x)
    model_y.fit(z, y)

    # Make predictions
    x_pred = model_x.predict(z)
    y_pred = model_y.predict(z)

    # Compute residuals
    x_residual = x - x_pred
    y_residual = y - y_pred

    # Compute the Spearman correlation
    pearson_corr, pearson_pval = pearsonr(x, y)
    partial_pearson_corr, partial_pearson_pval  = pearsonr(x_residual, y_residual)
    spearman_corr, spearman_pval = spearmanr(x, y)
    partial_spearman_corr, partial_spearman_pval = spearmanr(x_residual, y_residual)
    
    return pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr

#%% Fit curve
import numpy as np
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score

def linear_func(x, a, b):
    return a * x + b
    

def logarithmic_func(x, a, b):
    return a * np.log(x) + b

def exponential_func(x, a, b):
    return a * np.exp(b * x)

def fit_models_and_evaluate(xdata, ydata):
    R2 = 0
    # Fit each model and compute R^2 score
    for model_func, model_name in [(linear_func, "linear"), (logarithmic_func, "logarithmic"), (exponential_func, "exponential")]:
        # Fit the model
        try:
            params, _ = curve_fit(model_func, xdata, ydata, maxfev=2000)
            # Predict using the fitted model
            y_pred = model_func(xdata, *params)
            # Calculate R^2 score
            r2 = r2_score(ydata, y_pred)
            
            
            if r2 > R2:
                best_model = model_name
                best_params = params
                best_r2 = r2
                best_y_pred = y_pred
                R2 = r2
            
        except Exception as e:
            print(f"Error fitting {model_name}: {e}")
            params, r2 = (None, None)
    
    return best_model, best_params, best_r2, best_y_pred


#%% Power-Law Equation Normalized 3 parameter
def power_law_func (x,a,b,c):
    return a * (x ** b) + c


def fit_power_law_func(xdata, ydata):
    
    #Normalizing
    x_max = np.max(xdata)
    y_max = np.max(ydata)
    xdata_normalized = xdata / x_max
    ydata_normalized = ydata / y_max
    
    try:
        
        c_upper_limit = np.percentile(ydata_normalized, 5)
        bounds = ([0, 0, 0], [np.inf, np.inf, c_upper_limit])
        
        # Fit the model
        params, _ = curve_fit(power_law_func,  xdata_normalized, ydata_normalized, p0=[1, 0.5, 0], bounds=bounds, maxfev=5000)  # Initial guess for a, b, c
        # Predict using the fitted model
        y_pred_normalized = power_law_func(xdata_normalized, *params) 
        y_pred =y_pred_normalized * y_max
        # Calculate R^2 score
        r2 = r2_score(ydata, y_pred)
        
    except Exception as e:
        print(f"Error fitting power-law: {e}")
        params, r2, y_pred = (None, None, None)
    
    return params, r2, y_pred, xdata_normalized, ydata_normalized, y_pred_normalized




#%% correlation_df
if 'correlation_df' in globals():
    del  correlation_df

if 'Best_fit_df' in globals():
    del  Best_fit_df
    
if 'PowerLaw_fit_df' in globals():
    del  PowerLaw_fit_df

correlation_df = pd.DataFrame(columns= ['Class'])


Best_fit_df = pd.DataFrame(columns= ['Pek_ROR_best_model', 'Pek_ROR_best_r2','Pek_ROR_best_a','Pek_ROR_best_b',
                                     'Arid_ROR_best_model', 'Arid_ROR_best_r2','Arid_ROR_best_a','Arid_ROR_best_b',
                                     'SP_ROR_best_model', 'SP_ROR_best_r2','SP_ROR_best_a','SP_ROR_best_b',
                                     'LastArid_ROR_best_model', 'LastArid_ROR_best_r2','LastArid_ROR_best_a','LastArid_ROR_best_b'
                                     ])


PowerLaw_fit_df = pd.DataFrame(columns= ['PowerLaw_Pek_ROR_r2', 'PowerLaw_Pek_ROR_a','PowerLaw_Pek_ROR_b','PowerLaw_Pek_ROR_c'])
#%% Aridity Lag time 
annual_Last_Aridity = annual_Aridity.copy(deep=True)
annual_Last_Aridity.index = annual_Aridity.index - pd.DateOffset(years=-1)
annual_Last_Aridity = annual_Last_Aridity[annual_Last_Aridity.index.year < 2022] # 1985-2021


LA_Matched_Inundation = Inundation[1:]
LA_Matched_annual_mean_discharge_df = annual_mean_discharge_df[1:]
LA_Matched_annual_mean_prec_df = annual_mean_prec_df[1:]

LA_Matched_annual_P95_discharge_df = annual_P95_discharge_df[1:]
LA_Matched_annual_P95_prec_df = annual_P95_prec_df[1:]

#Last Year, Current Year Aridity (LYCYA)
#LYCYA_mean = (annual_Aridity[1:] + annual_Last_Aridity )/2

#%% Match data with SP (2001 to 2019)
SP_Matched_Inundation = Inundation[Inundation.index.isin(annual_Snow_Presence.index)]
SP_Matched_Aridity = annual_Aridity[annual_Aridity.index.isin(annual_Snow_Presence.index)]
SP_Matched_LYAridity = annual_Last_Aridity[annual_Last_Aridity.index.isin(annual_Snow_Presence.index)]
SP_Matched_annual_mean_discharge_df = annual_mean_discharge_df[annual_mean_discharge_df.index.isin(annual_Snow_Presence.index)]
SP_Matched_annual_mean_prec_df = annual_mean_prec_df[annual_mean_prec_df.index.isin(annual_Snow_Presence.index)]
SP_Matched_annual_NWI_Max_df = ERA5_Monthly_NWI_Max[ERA5_Monthly_NWI_Max.index.isin(annual_Snow_Presence.index)]

SP_Matched_annual_P95_discharge_df = annual_P95_discharge_df[annual_P95_discharge_df.index.isin(annual_Snow_Presence.index)]
SP_Matched_annual_P95_prec_df = annual_P95_prec_df[annual_P95_prec_df.index.isin(annual_Snow_Presence.index)]

#%% Annual Seasonality

# Non-linear model for temperature and precipitation
def temp_model(x, delta_t, s_t):
    return np.mean(temp) + delta_t * np.sin(2 * np.pi * (x - s_t) / 365)

def prec_model(x, delta_p, s_p):
    return np.mean(prec) * (1 + delta_p * np.sin(2 * np.pi * (x - s_p) / 365))


annual_Seasonality = pd.DataFrame(index=sorted(temp_df.index.year.unique()), columns=stations)

for st in stations:
    # Extract data for this station
    prec = prec_df[st]
    temp = temp_df[st]
    
    # Group by year
    for yr, temp_year in temp.groupby(temp.index.year):
        prec_year = prec[prec.index.year == yr]
        
        # Julian day of year
        t_julian = temp_year.index.dayofyear
        
        # Skip years with missing data
        if len(temp_year) < 300 or len(prec_year) < 300:
            continue
        
        # Fit seasonal models
        try:
            popt_temp, _ = curve_fit(temp_model, t_julian, temp_year, p0=[5, -90])
            popt_prec, _ = curve_fit(prec_model, t_julian, prec_year, p0=[0.4, 90], bounds=([-1, 0], [1, 365]))
        except RuntimeError:
            continue  # fitting failed
        
        delta_t, s_t = popt_temp
        delta_p, s_p = popt_prec
        
        # Annual precipitation seasonality relative to temperature
        delta_p_star = delta_p * np.sign(delta_t) * np.cos(2 * np.pi * (s_p - s_t) / 365.25)
        
        # Save result into dataframe
        annual_Seasonality.loc[yr, st] = delta_p_star
        



annual_Seasonality.index = pd.to_datetime(annual_Seasonality.index.astype(str) + "-12-31")



#%% correlations


for i, st in enumerate(stations):
    if st in class_B_stations:    ######## Update #######
        correlation_df.at[st, 'Class'] = 'B'   ######## Update #######
        
    elif st in class_A_stations:    ######## Update #######
        correlation_df.at[st, 'Class'] = 'A'   ######## Update #######
        
    else:
        continue
    

    masked_aridity        = np.ma.masked_invalid(annual_Aridity[st])
    masked_Pekel          = np.ma.masked_invalid(Inundation[st]*100)
    masked_discharge_prec = np.ma.masked_invalid(annual_mean_discharge_df[st]/annual_mean_prec_df[st])
    masked_discharge_prec_95 = np.ma.masked_invalid(annual_P95_discharge_df[st]/annual_P95_prec_df[st])
    masked_annual_P95_rain = np.ma.masked_invalid(annual_P95_rain_df[st])
    masked_annual_max_rain = np.ma.masked_invalid(annual_max_rain_df[st])
    masked_Snow_Fraction = np.ma.masked_invalid(annual_Snow_Fraction[st]) 
    
    masked_NWI_April = np.ma.masked_invalid(ERA5_Monthly_NWI_April[st])
    masked_NWI_Max = np.ma.masked_invalid(ERA5_Monthly_NWI_Max[st])
    masked_NWI_Spring = np.ma.masked_invalid(ERA5_Monthly_NWI_Spring[st])
    
    masked_NetInput_April = np.ma.masked_invalid(ERA5_Monthly_NetInput_April[st])
    masked_NetInput_Max = np.ma.masked_invalid(ERA5_Monthly_NetInput_Max[st])
    masked_NetInput_Spring = np.ma.masked_invalid(ERA5_Monthly_NetInput_Spring[st])
    
    
    
    
    
    # Snow Fraction vs ROR
    mask = ~masked_discharge_prec.mask & ~masked_Snow_Fraction.mask 
    
    pearson_corr, pearson_pval = pearsonr(masked_Snow_Fraction[mask],  masked_discharge_prec[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Snow_Fraction[mask], masked_discharge_prec[mask])
    
    correlation_df.at[st, 'Pearson_Corr_SF_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_SF_ROR']  = spearman_corr 
    
    # Snow Fraction vs ROR for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_Snow_Fraction.mask 
    
    pearson_corr, pearson_pval = pearsonr(masked_Snow_Fraction[mask],  masked_discharge_prec_95[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Snow_Fraction[mask], masked_discharge_prec_95[mask])
    
    correlation_df.at[st, 'Pearson_Corr_SF_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_SF_ROR95']  = spearman_corr 
    
    #Inund-SF
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_Snow_Fraction[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_Snow_Fraction[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_SF']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_SF']  = spearman_corr
    
    
    
    
    
    # Extream Rainfall vs ROR
    mask = ~masked_discharge_prec.mask & ~masked_annual_P95_rain.mask
    
    pearson_corr, pearson_pval = pearsonr(masked_annual_P95_rain[mask], masked_discharge_prec[mask])
    spearman_corr, spearman_pval = spearmanr(masked_annual_P95_rain[mask], masked_discharge_prec[mask])

    correlation_df.at[st, 'Pearson_Corr_Rain95_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Rain95_ROR'] = spearman_corr
    
    # Extream Rainfall vs ROR for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_annual_P95_rain.mask
    
    pearson_corr, pearson_pval = pearsonr(masked_annual_P95_rain[mask], masked_discharge_prec_95[mask])
    spearman_corr, spearman_pval = spearmanr(masked_annual_P95_rain[mask], masked_discharge_prec_95[mask])

    correlation_df.at[st, 'Pearson_Corr_Rain95_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Rain95_ROR95'] = spearman_corr
    
    #Inund-Rain95
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_annual_P95_rain[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_annual_P95_rain[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_Rain95']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_Rain95']  = spearman_corr
    
    
    
    # Max Rainfall vs ROR
    mask = ~masked_discharge_prec.mask & ~masked_annual_max_rain.mask
    
    pearson_corr, pearson_pval = pearsonr(masked_annual_max_rain[mask], masked_discharge_prec[mask])
    spearman_corr, spearman_pval = spearmanr(masked_annual_max_rain[mask], masked_discharge_prec[mask])

    correlation_df.at[st, 'Pearson_Corr_RainMax_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_RainMax_ROR'] = spearman_corr
    
    # Max Rainfall vs ROR for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_annual_max_rain.mask
    
    pearson_corr, pearson_pval = pearsonr(masked_annual_max_rain[mask], masked_discharge_prec_95[mask])
    spearman_corr, spearman_pval = spearmanr(masked_annual_max_rain[mask], masked_discharge_prec_95[mask])

    correlation_df.at[st, 'Pearson_Corr_RainMax_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_RainMax_ROR95'] = spearman_corr
    
    #Inund-RainMax
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_annual_max_rain[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_annual_max_rain[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_RainMax']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_RainMax']  = spearman_corr
    
    
    
    
    # Inundation-ROR-Aridity 1984-2021
    mask = ~masked_Pekel.mask & ~masked_discharge_prec.mask & ~masked_aridity.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_aridity[mask])
    
    correlation_df.at[st, 'Pearson_Corr_Inund_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_ROR'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_Aridity']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_Aridity']  = partial_spearman_corr
    
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_Pekel[mask], masked_discharge_prec[mask])
    Best_fit_df.at[st, 'Pek_ROR_best_model'] = best_model
    Best_fit_df.at[st, 'Pek_ROR_best_r2'] = best_r2
    Best_fit_df.at[st, 'Pek_ROR_best_a'] = best_params[0]
    Best_fit_df.at[st, 'Pek_ROR_best_b'] = best_params[1]
    
    # Inundation-ROR-Aridity 1984-2021 for ROR95
    mask = ~masked_Pekel.mask & ~masked_discharge_prec_95.mask & ~masked_aridity.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_aridity[mask])
    
    correlation_df.at[st, 'Pearson_Corr_Inund_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_ROR95'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_Aridity']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_Aridity']  = partial_spearman_corr
    
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_Pekel[mask], masked_discharge_prec_95[mask])
    Best_fit_df.at[st, 'Pek_ROR95_best_model'] = best_model
    Best_fit_df.at[st, 'Pek_ROR95_best_r2'] = best_r2
    Best_fit_df.at[st, 'Pek_ROR95_best_a'] = best_params[0]
    Best_fit_df.at[st, 'Pek_ROR95_best_b'] = best_params[1]
    
    
    
    
    
    # Power law equation between Inundation and ROR
    params, r2, y_pred, _,_,_ = fit_power_law_func(masked_Pekel[mask], masked_discharge_prec[mask])

    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR_r2'] = r2
    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR_a'] = params[0]
    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR_b'] = params[1]
    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR_c'] = params[2]
    
    # Power law equation between Inundation and ROR for ROR95
    params, r2, y_pred, _,_,_ = fit_power_law_func(masked_Pekel[mask], masked_discharge_prec_95[mask])

    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR95_r2'] = r2
    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR95_a'] = params[0]
    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR95_b'] = params[1]
    PowerLaw_fit_df.at[st, 'PowerLaw_Pek_ROR95_c'] = params[2]
    
    
    
    
    
    # Aridity-ROR-Inundation 1984-2021
    mask = ~masked_Pekel.mask & ~masked_discharge_prec.mask & ~masked_aridity.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_discharge_prec[mask], masked_aridity[mask], masked_Pekel[mask])
    correlation_df.at[st, 'Pearson_Corr_Aridity_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Aridity_ROR'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_Aridity_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Aridity_ROR_Inund']  = partial_spearman_corr
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_aridity[mask], masked_discharge_prec[mask])
    Best_fit_df.at[st, 'Arid_ROR_best_model'] = best_model
    Best_fit_df.at[st, 'Arid_ROR_best_r2'] = best_r2
    Best_fit_df.at[st, 'Arid_ROR_best_a'] = best_params[0]
    Best_fit_df.at[st, 'Arid_ROR_best_b'] = best_params[1]
    
    # Aridity-ROR-Inundation 1984-2021 for ROR95
    mask = ~masked_Pekel.mask & ~masked_discharge_prec_95.mask & ~masked_aridity.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_discharge_prec_95[mask], masked_aridity[mask], masked_Pekel[mask])
    correlation_df.at[st, 'Pearson_Corr_Aridity_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Aridity_ROR95'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_Aridity_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Aridity_ROR95_Inund']  = partial_spearman_corr
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_aridity[mask], masked_discharge_prec_95[mask])
    Best_fit_df.at[st, 'Arid_ROR95_best_model'] = best_model
    Best_fit_df.at[st, 'Arid_ROR95_best_r2'] = best_r2
    Best_fit_df.at[st, 'Arid_ROR95_best_a'] = best_params[0]
    Best_fit_df.at[st, 'Arid_ROR95_best_b'] = best_params[1]
    
    #Inund-Aridity
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_aridity[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_aridity[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_Aridity']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_Aridity']  = spearman_corr
    
    
    
    
    
        
    # Max_Monthly_NWI - ROR - Inundation  1984-2021
    mask = ~masked_discharge_prec.mask & ~masked_NWI_Max.mask & ~masked_Pekel.mask
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NWI_Max[mask], masked_discharge_prec[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NWIMax_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NWIMax_ROR']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NWIMax_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NWIMax_ROR_Inund']  = partial_spearman_corr
    
    
    # Max_Monthly_NWI - ROR - Inundation  1984-2021 for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_NWI_Max.mask & ~masked_Pekel.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NWI_Max[mask], masked_discharge_prec_95[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NWIMax_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NWIMax_ROR95']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NWIMax_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NWIMax_ROR95_Inund']  = partial_spearman_corr
    
    
    # Inundation - ROR - Max_Monthly_Net_Prec  1984-2021 
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_NWI_Max[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_NWIMax']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_NWIMax']  = partial_spearman_corr
    
    
    # Inundation - ROR - Max_Monthly_Net_Prec  1984-2021 for ROR95
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_NWI_Max[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_NWIMax']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_NWIMax']  = partial_spearman_corr
    
    
    #Inund-NWIMax
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_NWI_Max[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_NWI_Max[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_NWIMax']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_NWIMax']  = spearman_corr
    
    
    
    
    
    # Spring_Monthly_Net_Prec - ROR - Inundation  1984-2021
    mask = ~masked_discharge_prec.mask & ~masked_NWI_Spring.mask & ~masked_Pekel.mask
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NWI_Spring[mask], masked_discharge_prec[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NWISpring_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NWISpring_ROR']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NWISpring_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NWISpring_ROR_Inund']  = partial_spearman_corr
    
    
    # Spring_Monthly_Net_Prec - ROR - Inundation  1984-2021 for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_NWI_Spring.mask & ~masked_Pekel.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NWI_Spring[mask], masked_discharge_prec_95[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NWISpring_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NWISpring_ROR95']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NWISpring_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NWISpring_ROR95_Inund']  = partial_spearman_corr
    
    
    # Inundation - ROR - Spring_Monthly_Net_Prec  1984-2021 
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_NWI_Spring[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_NWISpring']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_NWISpring']  = partial_spearman_corr
    
    # Inundation - ROR - Spring_Monthly_Net_Prec  1984-2021 for ROR95
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_NWI_Spring[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_NWISpring']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_NWISpring']  = partial_spearman_corr
    
    #Inund-NWISpring
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_NWI_Spring[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_NWI_Spring[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_NWISpring']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_NWISpring']  = spearman_corr
    
    
    
    # April Net Prec vs ROR
    mask = ~masked_discharge_prec.mask & ~masked_NWI_April.mask 
    
    pearson_corr, pearson_pval = pearsonr(masked_NWI_April[mask],  masked_discharge_prec[mask])
    spearman_corr, spearman_pval = spearmanr(masked_NWI_April[mask], masked_discharge_prec[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NWIApril_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NWIApril_ROR']  = spearman_corr 

    
    # April Net Prec vs ROR for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_NWI_April.mask 
    
    pearson_corr, pearson_pval = pearsonr(masked_NWI_April[mask],  masked_discharge_prec_95[mask])
    spearman_corr, spearman_pval = spearmanr(masked_NWI_April[mask], masked_discharge_prec_95[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NWIApril_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NWIApril_ROR95']  = spearman_corr  
    
    #Inund-NWIApril
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_NWI_April[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_NWI_April[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_NWIApril']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_NWIApril']  = spearman_corr
    
    
    
    
    
    
    # Max_Monthly_Net_Input - ROR - Inundation  1984-2021
    mask = ~masked_discharge_prec.mask & ~masked_NetInput_Max.mask & ~masked_Pekel.mask
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NetInput_Max[mask], masked_discharge_prec[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NetInputMax_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NetInputMax_ROR']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NetInputMax_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NetInputMax_ROR_Inund']  = partial_spearman_corr
    
    
    # Max_Monthly_Net_Input - ROR - Inundation  1984-2021 for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_NetInput_Max.mask & ~masked_Pekel.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NetInput_Max[mask], masked_discharge_prec_95[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NetInputMax_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NetInputMax_ROR95']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NetInputMax_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NetInputMax_ROR95_Inund']  = partial_spearman_corr
    
    
    # Inundation - ROR - Max_Monthly_Net_Input  1984-2021 
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_NetInput_Max[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_NetInputMax']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_NetInputMax']  = partial_spearman_corr
    
    # Inundation - ROR - Max_Monthly_Net_Input  1984-2021 for ROR95
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_NetInput_Max[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_NetInputMax']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_NetInputMax']  = partial_spearman_corr
    
    
    
    
    
    # Spring_Monthly_Net_Input - ROR - Inundation  1984-2021
    mask = ~masked_discharge_prec.mask & ~masked_NetInput_Spring.mask & ~masked_Pekel.mask
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NetInput_Spring[mask], masked_discharge_prec[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NetInputSpring_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NetInputSpring_ROR']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NetInputSpring_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NetInputSpring_ROR_Inund']  = partial_spearman_corr
    
    
    # Spring_Monthly_Net_Input - ROR - Inundation  1984-2021 for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_NetInput_Spring.mask & ~masked_Pekel.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NetInput_Spring[mask], masked_discharge_prec_95[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NetInputSpring_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NetInputSpring_ROR95']  = spearman_corr 
    correlation_df.at[st, 'Par_Pearson_Corr_NetInputSpring_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_NetInputSpring_ROR95_Inund']  = partial_spearman_corr
    
    
    # Inundation - ROR - Spring_Monthly_Net_Prec  1984-2021 
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_NetInput_Spring[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_NetInputSpring']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_NetInputSpring']  = partial_spearman_corr
    
    # Inundation - ROR - Spring_Monthly_Net_Prec  1984-2021 for ROR95
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_NetInput_Spring[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_NetInputSpring']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_NetInputSpring']  = partial_spearman_corr
    
    
    
    
    
    # April Net Input vs ROR
    mask = ~masked_discharge_prec.mask & ~masked_NetInput_April.mask 
    
    pearson_corr, pearson_pval = pearsonr(masked_NetInput_April[mask],  masked_discharge_prec[mask])
    spearman_corr, spearman_pval = spearmanr(masked_NetInput_April[mask], masked_discharge_prec[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NetInputApril_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NetInputApril_ROR']  = spearman_corr 

    
    # April Net Input vs ROR for ROR95
    mask = ~masked_discharge_prec_95.mask & ~masked_NetInput_April.mask 
    
    pearson_corr, pearson_pval = pearsonr(masked_NetInput_April[mask],  masked_discharge_prec_95[mask])
    spearman_corr, spearman_pval = spearmanr(masked_NetInput_April[mask], masked_discharge_prec_95[mask])
    
    correlation_df.at[st, 'Pearson_Corr_NetInputApril_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_NetInputApril_ROR95']  = spearman_corr
    
    
    
    
    
    # SP-ROR-Inund 2001-2019
    masked_Pekel          = np.ma.masked_invalid(SP_Matched_Inundation[st]*100)
    masked_Snow_Presence          = np.ma.masked_invalid(annual_Snow_Presence[st])
    masked_discharge_prec = np.ma.masked_invalid(SP_Matched_annual_mean_discharge_df[st]/SP_Matched_annual_mean_prec_df[st])
    
    mask = ~masked_Snow_Presence.mask & ~masked_discharge_prec.mask & ~masked_Pekel.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Snow_Presence[mask], masked_discharge_prec[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_SP_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_SP_ROR'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_SP_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_SP_ROR_Inund']  = partial_spearman_corr
    
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_Snow_Presence[mask], masked_discharge_prec[mask])
    Best_fit_df.at[st, 'SP_ROR_best_model'] = best_model
    Best_fit_df.at[st, 'SP_ROR_best_r2'] = best_r2
    Best_fit_df.at[st, 'SP_ROR_best_a'] = best_params[0]
    Best_fit_df.at[st, 'SP_ROR_best_b'] = best_params[1]
    
    # SP-ROR-Inund 2001-2019 for ROR95
    masked_Pekel          = np.ma.masked_invalid(SP_Matched_Inundation[st]*100)
    masked_Snow_Presence          = np.ma.masked_invalid(annual_Snow_Presence[st])
    masked_discharge_prec_95 = np.ma.masked_invalid(SP_Matched_annual_P95_discharge_df[st]/SP_Matched_annual_P95_prec_df[st])
    
    mask = ~masked_Snow_Presence.mask & ~masked_discharge_prec_95.mask & ~masked_Pekel.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Snow_Presence[mask], masked_discharge_prec_95[mask], masked_Pekel[mask])
    
    correlation_df.at[st, 'Pearson_Corr_SP_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_SP_ROR95'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_SP_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_SP_ROR95_Inund']  = partial_spearman_corr
    
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_Snow_Presence[mask], masked_discharge_prec_95[mask])
    Best_fit_df.at[st, 'SP_ROR95_best_model'] = best_model
    Best_fit_df.at[st, 'SP_ROR95_best_r2'] = best_r2
    Best_fit_df.at[st, 'SP_ROR95_best_a'] = best_params[0]
    Best_fit_df.at[st, 'SP_ROR95_best_b'] = best_params[1]
    
    
    
    
    
    # Inund-ROR-SP
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_Snow_Presence[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_SP']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_SP']  = partial_spearman_corr
    
    # Inund-ROR-SP for ROR95
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_Snow_Presence[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_SP']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_SP']  = partial_spearman_corr
    
    
    
    
    
    #Inund-SP
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_Snow_Presence[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_Snow_Presence[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_SP']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_SP']  = spearman_corr
    
    
    
    
    
    # LA-ROR-Inund
    masked_LYaridity        = np.ma.masked_invalid(annual_Last_Aridity[st])
    masked_Pekel          = np.ma.masked_invalid(LA_Matched_Inundation[st]*100)
    masked_discharge_prec = np.ma.masked_invalid(LA_Matched_annual_mean_discharge_df[st]/LA_Matched_annual_mean_prec_df[st])
    
    
    mask = ~masked_Pekel.mask & ~masked_discharge_prec.mask & ~masked_LYaridity.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_discharge_prec[mask], masked_LYaridity[mask], masked_Pekel[mask])
    correlation_df.at[st, 'Pearson_Corr_LA_ROR']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_LA_ROR'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_LA_ROR_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_LA_ROR_Inund']  = partial_spearman_corr
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_LYaridity[mask], masked_discharge_prec[mask])
    Best_fit_df.at[st, 'LastArid_ROR_best_model'] = best_model
    Best_fit_df.at[st, 'LastArid_ROR_best_r2'] = best_r2
    Best_fit_df.at[st, 'LastArid_ROR_best_a'] = best_params[0]
    Best_fit_df.at[st, 'LastArid_ROR_best_b'] = best_params[1]
    
    # LA-ROR-Inund for ROR95
    masked_LYaridity        = np.ma.masked_invalid(annual_Last_Aridity[st])
    masked_Pekel          = np.ma.masked_invalid(LA_Matched_Inundation[st]*100)
    masked_discharge_prec_95 = np.ma.masked_invalid(LA_Matched_annual_P95_discharge_df[st]/LA_Matched_annual_P95_prec_df[st])
    
    
    mask = ~masked_Pekel.mask & ~masked_discharge_prec_95.mask & ~masked_LYaridity.mask

    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_discharge_prec_95[mask], masked_LYaridity[mask], masked_Pekel[mask])
    correlation_df.at[st, 'Pearson_Corr_LA_ROR95']  = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_LA_ROR95'] = spearman_corr
    correlation_df.at[st, 'Par_Pearson_Corr_LA_ROR95_Inund']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_LA_ROR95_Inund']  = partial_spearman_corr
    
    best_model, best_params, best_r2, y_pred = fit_models_and_evaluate(masked_LYaridity[mask], masked_discharge_prec_95[mask])
    Best_fit_df.at[st, 'LastArid_ROR95_best_model'] = best_model
    Best_fit_df.at[st, 'LastArid_ROR95_best_r2'] = best_r2
    Best_fit_df.at[st, 'LastArid_ROR95_best_a'] = best_params[0]
    Best_fit_df.at[st, 'LastArid_ROR95_best_b'] = best_params[1]
    
    
    
    
    
    # Inund-ROR-LA
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], masked_LYaridity[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR_LA']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR_LA']  = partial_spearman_corr 
    
    # Inund-ROR-LA for ROR95
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], masked_LYaridity[mask])
    correlation_df.at[st, 'Par_Pearson_Corr_Inund_ROR95_LA']  = partial_pearson_corr
    correlation_df.at[st, 'Par_Spearman_Corr_Inund_ROR95_LA']  = partial_spearman_corr
    
    
    
    
    
    #Inund-LA
    pearson_corr, pearson_pval = pearsonr(masked_Pekel[mask], masked_LYaridity[mask])
    spearman_corr, spearman_pval = spearmanr(masked_Pekel[mask], masked_LYaridity[mask])
    correlation_df.at[st, 'Pearson_Corr_Inund_LA']   = pearson_corr
    correlation_df.at[st, 'Spearman_Corr_Inund_LA']  = spearman_corr
    
    
    
    
    
    # More than one covariates: All over 2001-2019
    masked_Pekel          = np.ma.masked_invalid(SP_Matched_Inundation[st]*100)
    masked_aridity        = np.ma.masked_invalid(SP_Matched_Aridity[st])
    masked_LYaridity      = np.ma.masked_invalid(SP_Matched_LYAridity[st])
    masked_Snow_Presence  = np.ma.masked_invalid(annual_Snow_Presence[st])
    masked_NWI_Max        = np.ma.masked_invalid(SP_Matched_annual_NWI_Max_df[st])
    masked_discharge_prec = np.ma.masked_invalid(SP_Matched_annual_mean_discharge_df[st]/SP_Matched_annual_mean_prec_df[st])

    

    
    
    mask = ~masked_Pekel.mask & ~masked_aridity.mask & ~masked_LYaridity.mask & ~masked_Snow_Presence.mask & ~masked_discharge_prec.mask & ~masked_NWI_Max.mask
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec[mask], np.column_stack((masked_LYaridity[mask], masked_Snow_Presence[mask], masked_NWI_Max[mask] )))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_Inund_ROR_[LA_SP_NWIMax]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_Inund_ROR_[LA_SP_NWIMax]']  = partial_spearman_corr
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Snow_Presence[mask], masked_discharge_prec[mask], np.column_stack((masked_LYaridity[mask], masked_Pekel[mask], masked_NWI_Max[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_SP_ROR_[LA_Inund_NWIMax]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_SP_ROR_[LA_Inund_NWIMax]']  = partial_spearman_corr
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_LYaridity[mask], masked_discharge_prec[mask], np.column_stack((masked_Pekel[mask], masked_Snow_Presence[mask], masked_NWI_Max[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_LA_ROR_[Inund_SP_NWIMax]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_LA_ROR_[Inund_SP_NWIMax]']  = partial_spearman_corr
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NWI_Max[mask], masked_discharge_prec[mask], np.column_stack((masked_Pekel[mask], masked_Snow_Presence[mask], masked_LYaridity[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_NWIMax_ROR_[Inund_SP_LA]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_NWIMax_ROR_[Inund_SP_LA]']  = partial_spearman_corr
    
    
    # More than one covariates: All over 2001-2019 for ROR95
    masked_Pekel          = np.ma.masked_invalid(SP_Matched_Inundation[st]*100)
    masked_aridity        = np.ma.masked_invalid(SP_Matched_Aridity[st])
    masked_LYaridity      = np.ma.masked_invalid(SP_Matched_LYAridity[st])
    masked_Snow_Presence  = np.ma.masked_invalid(annual_Snow_Presence[st])
    masked_NWI_Max        = np.ma.masked_invalid(SP_Matched_annual_NWI_Max_df[st])
    masked_discharge_prec_95 = np.ma.masked_invalid(SP_Matched_annual_P95_discharge_df[st]/SP_Matched_annual_P95_prec_df[st])
    
    
    mask = ~masked_Pekel.mask & ~masked_aridity.mask & ~masked_LYaridity.mask & ~masked_Snow_Presence.mask & ~masked_discharge_prec_95.mask & ~masked_NWI_Max.mask
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Pekel[mask], masked_discharge_prec_95[mask], np.column_stack((masked_LYaridity[mask], masked_Snow_Presence[mask], masked_NWI_Max[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_Inund_ROR95_[LA_SP_NWIMax]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_Inund_ROR95_[LA_SP_NWIMax]']  = partial_spearman_corr
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_Snow_Presence[mask], masked_discharge_prec_95[mask], np.column_stack((masked_LYaridity[mask], masked_Pekel[mask], masked_NWI_Max[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_SP_ROR95_[LA_Inund_NWIMax]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_SP_ROR95_[LA_Inund_NWIMax]']  = partial_spearman_corr
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_LYaridity[mask], masked_discharge_prec_95[mask], np.column_stack((masked_Pekel[mask], masked_Snow_Presence[mask], masked_NWI_Max[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_LA_ROR95_[Inund_SP_NWIMax]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_LA_ROR95_[Inund_SP_NWIMax]']  = partial_spearman_corr
    
    
    pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr = Par_Spear_Corr(masked_NWI_Max[mask], masked_discharge_prec_95[mask], np.column_stack((masked_Pekel[mask], masked_Snow_Presence[mask], masked_LYaridity[mask])))
    correlation_df.at[st, 'Total_Par_Pearson_Corr_NWIMax_ROR95_[Inund_SP_LA]']  = partial_pearson_corr
    correlation_df.at[st, 'Total_Par_Spearman_Corr_NWIMax_ROR95_[Inund_SP_LA]']  = partial_spearman_corr

    
del best_model, best_params, best_r2, y_pred
del pearson_corr, spearman_corr, partial_pearson_corr, partial_spearman_corr
del mask, masked_Pekel, masked_aridity, masked_LYaridity, masked_Snow_Presence, masked_discharge_prec

# Add Lat and Lon
correlation_df = pd.merge(correlation_df,station_df,how='inner', left_index=True, right_index=True)

# print(correlation_df.columns)

#%%  subclassification based on partial correlation for mean

df_copy = correlation_df.copy(deep=True)

df_copy = correlation_df[['Par_Pearson_Corr_Inund_ROR_Aridity',
                          'Par_Spearman_Corr_Inund_ROR_Aridity','Par_Spearman_Corr_Aridity_ROR_Inund', 
                          'Par_Spearman_Corr_Inund_ROR_LA', 'Par_Spearman_Corr_LA_ROR_Inund',
                          'Par_Spearman_Corr_Inund_ROR_SP', 'Par_Spearman_Corr_SP_ROR_Inund',
                          'Par_Spearman_Corr_Inund_ROR_NWIMax', 'Par_Spearman_Corr_NWIMax_ROR_Inund' ]]


Inund_par_Spearman_cor   = correlation_df[['Par_Spearman_Corr_Inund_ROR_Aridity','Par_Spearman_Corr_Inund_ROR_LA', 
                                         'Par_Spearman_Corr_Inund_ROR_SP', 'Par_Spearman_Corr_Inund_ROR_NWIMax']]

climate_par_Spearman_cor = correlation_df[['Par_Spearman_Corr_Aridity_ROR_Inund','Par_Spearman_Corr_LA_ROR_Inund',
                           'Par_Spearman_Corr_SP_ROR_Inund','Par_Spearman_Corr_NWIMax_ROR_Inund' ]]

binary_df = climate_par_Spearman_cor.copy(deep=True)
binary_df = abs(binary_df)
binary_df = (binary_df.eq(binary_df.max(axis=1), axis=0)).astype(int)

Inund_Pearson_binary_df = binary_df.copy(deep=True)
Inund_Spearman_binary_df = binary_df.copy(deep=True)

Inund_Spearman_binary_df.columns = Inund_par_Spearman_cor.columns


climate_par_Spearman_cor = climate_par_Spearman_cor*binary_df
Inund_par_Spearman_cor = Inund_par_Spearman_cor*Inund_Spearman_binary_df

climate_par_Spearman_cor_greatest = climate_par_Spearman_cor.sum(axis=1)
Inund_par_Spearman_cor_greatest = Inund_par_Spearman_cor.sum(axis=1) 



subclass_1 = df_copy[(Inund_par_Spearman_cor_greatest > 0.5) & (Inund_par_Spearman_cor_greatest > abs(climate_par_Spearman_cor_greatest) )]
subclass_1['sub_class'] = 1
subclass_1 = subclass_1[['sub_class']]


subclass_2 = df_copy[ (Inund_par_Spearman_cor_greatest < abs(climate_par_Spearman_cor_greatest))  &  (abs(climate_par_Spearman_cor_greatest) > 0.5)]
subclass_2['sub_class'] = 2
subclass_2 = subclass_2[['sub_class']]


subclass_4 = df_copy[ (Inund_par_Spearman_cor_greatest < 0.5)  &  (abs(climate_par_Spearman_cor_greatest) < 0.5)]
subclass_4['sub_class'] = 4
subclass_4 = subclass_4[['sub_class']]

subclasses = pd.concat([subclass_2, subclass_1, subclass_4], axis=0)
subclasses = subclasses[~subclasses.index.duplicated(keep='first')]


del subclass_1, subclass_2, subclass_4, df_copy
del binary_df, Inund_Pearson_binary_df, Inund_Spearman_binary_df, climate_par_Spearman_cor
del Inund_par_Spearman_cor
del climate_par_Spearman_cor_greatest, Inund_par_Spearman_cor_greatest, 


#%% total-dataset
if 'total_dataset' in globals():
    del  total_dataset

total_dataset = pd.merge(subclasses, correlation_df, how='left', left_index=True, right_index=True)
total_dataset = pd.merge(total_dataset, Best_fit_df, how='left', left_index=True, right_index=True)

total_dataset = pd.merge(total_dataset, PowerLaw_fit_df, how='left', left_index=True, right_index=True)

total_dataset.loc[total_dataset['Pek_ROR_best_r2'] < 0.5, 'Pek_ROR_best_model'] = 'R² < 0.5'
total_dataset.loc[total_dataset['Arid_ROR_best_r2'] < 0.5, 'Arid_ROR_best_model'] = 'R² < 0.5'

total_dataset.loc[total_dataset['Pek_ROR95_best_r2'] < 0.5, 'Pek_ROR95_best_model'] = 'R² < 0.5'
total_dataset.loc[total_dataset['Arid_ROR95_best_r2'] < 0.5, 'Arid_ROR95_best_model'] = 'R² < 0.5'



long_term_Runoff_Ratio = long_term_Runoff_Ratio.rename("ROR")
long_term_Runoff_Ratio_95 = long_term_Runoff_Ratio_95.rename("ROR_95")
long_term_mean_Pekel = long_term_mean_Pekel.rename("long_term_mean_Annual_Inundation")

total_dataset = pd.merge(total_dataset, long_term_Runoff_Ratio, how='left', left_index=True, right_index=True)
total_dataset = pd.merge(total_dataset, long_term_Runoff_Ratio_95, how='left', left_index=True, right_index=True)
total_dataset = pd.merge(total_dataset, long_term_mean_Pekel, how='left', left_index=True, right_index=True)



# Add Stitic Feature (over 38 years)
total_dataset = pd.merge(total_dataset, static_features_PPR, how='left', left_index=True, right_index=True)
total_dataset['MAXPA'] = total_dataset['MAXPA']*100 # Convert to percentage


total_dataset.to_csv(outdir + '/00_total_dataset.csv', index=True)


############################ Plots ############################  


#%% Figure 02

Inundation_Dominated = total_dataset.loc[total_dataset['sub_class'].values == 1]


Par_cors = ['Spearman_Corr_Inund_ROR', 'Spearman_Corr_Aridity_ROR', 'Par_Spearman_Corr_Inund_ROR_Aridity', 'Par_Spearman_Corr_Aridity_ROR_Inund',
            'Spearman_Corr_Rain95_ROR', 'Spearman_Corr_LA_ROR', 'Par_Spearman_Corr_Inund_ROR_LA', 'Par_Spearman_Corr_LA_ROR_Inund',     
            'Spearman_Corr_SF_ROR', 'Spearman_Corr_SP_ROR','Par_Spearman_Corr_Inund_ROR_SP', 'Par_Spearman_Corr_SP_ROR_Inund',
            'Spearman_Corr_NWIApril_ROR', 'Spearman_Corr_NWIMax_ROR','Par_Spearman_Corr_Inund_ROR_NWIMax','Par_Spearman_Corr_NWIMax_ROR_Inund']

Names = ['MIWA vs. ROR', 'Aridity vs. ROR','MIWA vs. ROR, conditioned on Aridity ', 'Aridity vs. ROR, conditioned on MIWA',
         'Rainfall-95 vs. ROR', 'PY-Aridity vs. ROR',  'MIWA vs. ROR, conditioned on PY-Aridity ', 'PY-Aridity vs. ROR, conditioned on MIWA',
         'Snow Fraction vs. ROR', 'Snow Persistence (SP) vs. ROR', 'MIWA vs. ROR, conditioned on SP', 'SP vs. ROR, conditioned on MIWA',
         r'NWI$_{April}$ vs. ROR', r'NWI$_{MAX}$ vs. ROR',r'MIWA vs. ROR, conditioned on NWI$_{MAX}$', r'NWI$_{MAX}$ vs. ROR, conditioned on MIWA', ]


# Create a single figure with six subplots (3 rows, 2 columns)
fig, axes = plt.subplots(nrows=4, ncols=4, figsize=(18, 16), subplot_kw={'projection': ccrs.PlateCarree()})

# Flatten the 2D axes array for easy iteration
axes = axes.flatten()

for i, metric in enumerate(Par_cors):
    ax = axes[i]  # Select the subplot
    
    prairie_watershed.plot(ax=ax, edgecolor='black', facecolor='none')

    # Add coastlines and borders
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS)
    
    # Define color levels
    minn = 0 #np.percentile(correlation_df[metric], 5)
    maxx = 1 #np.percentile(correlation_df[metric], 95)
    color_levels = np.linspace(minn, maxx, 11)
    
    # Define colormap and normalization
    cmap = plt.get_cmap('coolwarm')
    norm = BoundaryNorm(color_levels, ncolors=cmap.N, clip=True)
    
    # Scatter plot
    sc = ax.scatter(correlation_df['lon'], correlation_df['lat'], 
                    c=np.abs(correlation_df[metric]), cmap=cmap, norm=norm, 
                    s=50, edgecolors='k', transform=ccrs.PlateCarree())
    
    # txt = f"Median= {np.median(correlation_df[metric]):.2f} \nMean= {np.mean(correlation_df[metric]):.2f}"
    txt = f"Median= {np.median(correlation_df[metric]):.2f} ({np.median(Inundation_Dominated[metric]):.2f}) \nMean= {np.mean(correlation_df[metric]):.2f} ({np.mean(Inundation_Dominated[metric]):.2f})"
    ax.text(0.05, 0.05, txt, transform=ax.transAxes, fontsize=13, fontname='Arial', 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    # Title
    title_name = Names[i]
    ax.set_title(f"{title_name}", loc='left', fontsize=13.5, fontname='Arial')
    


# Add a single horizontal colorbar below all subplots
cbar_ax = fig.add_axes([0.11, - 0.02, 0.68, 0.015])  # Position: (left, bottom, width, height)
cbar = plt.colorbar(sc, cax=cbar_ax, orientation="horizontal",  ticks=color_levels, norm=norm)
cbar.ax.tick_params(labelsize=10)
cbar.ax.set_xlabel("Spearman Correlation", fontsize=13, fontname='Arial') # font size of the colorbar label

cbar.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%0.2f'))


# Adjust layout
plt.tight_layout(rect=[0, 0, 0.9, 1])  # Leave space for colorbar
plt.savefig(outdir + '/Figure_02' + '.png', dpi=600, bbox_inches='tight')

# plt.show(block=False)
plt.close()

del txt, title_name, sc, cmap, norm, cbar_ax, minn, maxx, color_levels, ax, fig, axes, 
del Par_cors, Names, i, metric 


#%% Figure 03

plt.figure(figsize=(10, 6))
ax = plt.axes(projection=ccrs.PlateCarree())
prairie_watershed.plot(ax=ax, edgecolor='black', facecolor='none')

min_lon, max_lon = -116.0, -92  # Example longitude range
min_lat, max_lat = 41.5, 55      # Example latitude range
ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

# Add coastlines and borders
ax.coastlines()
ax.add_feature(cartopy.feature.BORDERS)

# Define a dictionary mapping equation types to shapes
# point_shapes = {'exponential': 'o', 'linear': '^', 'logarithmic': 'X', 'R² < 0.5': '*'}
face_colors = {1:'yellowgreen', 2:'violet', 4:'silver'}
face_colors = {1:'red', 2:'green', 4:'silver'}
edge_colors = {'A':'black', 'B':'black'}


# Plot each point with the specified attributes
for (lon, lat, subcls, clss) in zip(total_dataset['lon'], total_dataset['lat'], total_dataset['sub_class'], total_dataset['Class']):   ######## Update ####### 
    edge_color = edge_colors[clss] 
    facecolor=face_colors[subcls]
    ax.scatter(lon, lat,  color=facecolor, edgecolors=edge_color, transform=ccrs.PlateCarree(), s=40, linewidths=1)


# Class edge colors legend
class_legend_handles = [
    plt.Line2D([0], [0], marker='o', color='white', markerfacecolor='white', markeredgewidth=2, markeredgecolor='firebrick', label='Small Inundation (Red edges)'),
    plt.Line2D([0], [0], marker='o', color='white', markerfacecolor='white', markeredgewidth=2, markeredgecolor='black', label='Large Inundation (Black edges)')
]
leg2 = ax.legend(handles=class_legend_handles, loc='lower left', bbox_to_anchor=(0.0, 0.25, 1, 1))

# sub_Class face colors legend
face_colors = {1:'yellowgreen', 2:'violet', 4:'silver'}
subclass_legend_handles = [
    plt.Line2D([0], [0], marker='o', color='white', markerfacecolor='red', label='Fill-spill dominated'),
    plt.Line2D([0], [0], marker='o', color='white', markerfacecolor='green', label='Climate dominated'),
    # plt.Line2D([0], [0], marker='o', color='white', markerfacecolor='royalblue', label='Jointly dominated'),
    plt.Line2D([0], [0], marker='o', color='white', markerfacecolor='Silver', label='Neither dominated')
]
leg3 = ax.legend(handles=subclass_legend_handles, loc='lower left', title="Classes")

# Manually add the function type legend back after creating the class legend
# ax.add_artist(leg2)

plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('Classification')  ######## Update #######

plt.savefig(outdir + '/Figure_03' + '.png', dpi=600, bbox_inches='tight')

# plt.show(block=False)
plt.close()

#%% Figure 04

sleceted_stations = ['05JE006','05123400','05MH005' ,'05053000','05059700','05051300']
province = ['Saskatchewan', 'North Dakota', 'Manitoba', 'North Dakota', 'North Dakota','Minnesota' ]



fig = plt.figure(figsize=(18, 15))  # Adjust figsize as needed
gs = GridSpec(5, 6, width_ratios=[1,1,1,1,1,1])
   
for i, st in enumerate(sleceted_stations):
    
    
    
    # First Row: Aridity
    ax = fig.add_subplot(gs[0, i])
    ax.scatter(annual_Aridity[st],  annual_mean_discharge_df[st]/annual_mean_prec_df[st])
    #ax.set_ylabel('ROR', color='k', fontsize=13, fontname='Arial')
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
        
    ax.set_xlabel('Aridity', color='k', fontsize=15, fontname='Arial')
    txt = f"PC= {correlation_df.loc[st, 'Pearson_Corr_Aridity_ROR']:.2f} \nSC= {correlation_df.loc[st, 'Spearman_Corr_Aridity_ROR']:.2f}"
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Aridity_ROR']:.2f}"
    ax.text(0.55, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    title = st + '\n' + province[i] 
    title = st + ' (' + province[i] + ')'
    ax.set_title(title,fontsize=14, fontname='Arial')
    
    
    
    
    # Second Row: PY-Aridity
    ax = fig.add_subplot(gs[1, i])
    ax.scatter(annual_Last_Aridity[st],  LA_Matched_annual_mean_discharge_df[st]/LA_Matched_annual_mean_prec_df[st])
    #ax.set_ylabel('ROR', color='k', fontsize=13, fontname='Arial')
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
        
    ax.set_xlabel('PY-Aridity', color='k', fontsize=15, fontname='Arial')
    txt = f"PC= {correlation_df.loc[st, 'Pearson_Corr_LA_ROR']:.2f} \nSC= {correlation_df.loc[st, 'Spearman_Corr_LA_ROR']:.2f}"
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_LA_ROR']:.2f}"
    ax.text(0.55, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    
    
    
    # third Row: SP
    ax = fig.add_subplot(gs[2, i])
    ax.scatter(annual_Snow_Presence[st],  SP_Matched_annual_mean_discharge_df[st]/SP_Matched_annual_mean_prec_df[st])
    #ax.set_ylabel('ROR', color='k', fontsize=13, fontname='Arial')
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
        
    ax.set_xlabel('Snow Persistence ', color='k', fontsize=15, fontname='Arial')
    txt = f"PC= {correlation_df.loc[st, 'Pearson_Corr_SP_ROR']:.2f} \nSC= {correlation_df.loc[st, 'Spearman_Corr_SP_ROR']:.2f}"
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_SP_ROR']:.2f}"
    ax.text(0.05, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    
    
    
    
    # fourth Row: NWIMax
    ax = fig.add_subplot(gs[3, i])
    ax.scatter(ERA5_Monthly_NWI_Max[st],  annual_mean_discharge_df[st]/annual_mean_prec_df[st])
    #ax.set_ylabel('ROR', color='k', fontsize=13, fontname='Arial')
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
        
    ax.set_xlabel(r'NWI$_{MAX}$', color='k', fontsize=15, fontname='Arial')
    txt = f"PC= {correlation_df.loc[st, 'Pearson_Corr_NWIMax_ROR']:.2f} \nSC= {correlation_df.loc[st, 'Spearman_Corr_NWIMax_ROR']:.2f}"
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_NWIMax_ROR']:.2f}"
    ax.text(0.05, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    
    
    
    
    # fifth Row: Inundation
    ax = fig.add_subplot(gs[4, i])
    ax.scatter(Inundation[st]*100,  annual_mean_discharge_df[st]/annual_mean_prec_df[st])

    
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
    
    ax.set_xlabel('MIWA(%)', color='k', fontsize=15, fontname='Arial')
    
    txt = f"PC= {correlation_df.loc[st, 'Pearson_Corr_Inund_ROR']:.2f} \nSC= {correlation_df.loc[st, 'Spearman_Corr_Inund_ROR']:.2f}"
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_ROR']:.2f}"
    ax.text(0.05, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))

        
        
# Adjust spacing between subplots to fit the title
plt.tight_layout(rect=[0, 0, 1, 1])

plt.savefig(outdir + '/Figure_04.png', dpi=600, bbox_inches='tight')    
      
# plt.show(block=False) 
plt.close()

#%% Figure 5

#Inundation_Dominated
Inundation_Dominated = total_dataset.loc[total_dataset['sub_class'].values == 1]

plt.figure(figsize=(7, 5))
ax = plt.axes(projection=ccrs.PlateCarree())
prairie_watershed.plot(ax=ax, edgecolor='black', facecolor='none')

# Add coastlines and borders
ax.coastlines()
ax.add_feature(cartopy.feature.BORDERS)



# Define your boundaries and your custom colors for each bin
boundaries = [0, 0.75, 1.25, 2.5, 5, 10, 38]
custom_colors = ['green','lightgreen', 'deeppink', 'orange', 'yellow','gray']  # Matches number of bins

# Create discrete colormap and normalization
cmap = ListedColormap(custom_colors)
norm = mcolors.BoundaryNorm(boundaries, cmap.N)


# Plot the data
sc = ax.scatter(Inundation_Dominated['lon'], 
                Inundation_Dominated['lat'], 
                c=Inundation_Dominated['PowerLaw_Pek_ROR_b'], 
                cmap=cmap, 
                norm=norm,
                s=50,
                edgecolors='k', 
                transform=ccrs.PlateCarree())

# Colorbar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)  
sm.set_array([])  

cbar = plt.colorbar(sm, label='b value', ax=ax, shrink=0.5, ticks=[0, 0.75, 1.25, 2.5, 5, 10]) #Position of labels on colorbar 
cbar.set_ticklabels(['0', '0.75', '1.25', '2.5', '5.0', '10.0']) 


# plt.title(metric+', Median= '+"{:.2f}".format(np.median(evaDict[metric])) +', Mean= '+ "{:.2f}".format(np.mean(evaDict[metric])) )
plt.xlabel('Longitude')
plt.ylabel('Latitude')

plt.savefig(outdir + '/Figure_05.png' , dpi=600, bbox_inches='tight')

# plt.show(block=False)
plt.close()


##################### Supplementary Figures ##################

#%% Supplementary Figure 1

Inundation_Dominated = total_dataset.loc[total_dataset['sub_class'].values == 1]


Par_cors = ['Spearman_Corr_Inund_ROR95', 'Spearman_Corr_Aridity_ROR95', 'Par_Spearman_Corr_Inund_ROR95_Aridity', 'Par_Spearman_Corr_Aridity_ROR95_Inund',
            'Spearman_Corr_Rain95_ROR95', 'Spearman_Corr_LA_ROR95', 'Par_Spearman_Corr_Inund_ROR95_LA', 'Par_Spearman_Corr_LA_ROR95_Inund',     
            'Spearman_Corr_SF_ROR95', 'Spearman_Corr_SP_ROR95','Par_Spearman_Corr_Inund_ROR95_SP', 'Par_Spearman_Corr_SP_ROR95_Inund',
            'Spearman_Corr_NWIApril_ROR95', 'Spearman_Corr_NWIMax_ROR95','Par_Spearman_Corr_Inund_ROR95_NWIMax','Par_Spearman_Corr_NWIMax_ROR95_Inund']

Names = ['MIWA vs. HFR', 'Aridity vs. HFR','MIWA vs. HFR, conditioned on Aridity ', 'Aridity vs. HFR, conditioned on MIWA',
         'Rainfall-95 vs. HFR', 'PY-Aridity vs. HFR',  'MIWA vs. HFR, conditioned on PY-Aridity ', 'PY-Aridity vs. HFR, conditioned on MIWA',
         'Snow Fraction vs. HFR', 'Snow Persistence (SP) vs. HFR', 'MIWA vs. HFR, conditioned on SP', 'SP vs. HFR, conditioned on MIWA',
         r'NWI$_{April}$ vs. HFR', r'NWI$_{MAX}$ vs. HFR', r'MIWA vs. HFR, conditioned on NWI$_{MAX}$', r'NWI$_{MAX}$ vs. HFR, conditioned on MIWA']



# Create a single figure with six subplots (3 rows, 2 columns)
fig, axes = plt.subplots(nrows=4, ncols=4, figsize=(18, 16), subplot_kw={'projection': ccrs.PlateCarree()})

# Flatten the 2D axes array for easy iteration
axes = axes.flatten()

for i, metric in enumerate(Par_cors):
    ax = axes[i]  # Select the subplot
    
    prairie_watershed.plot(ax=ax, edgecolor='black', facecolor='none')

    # Add coastlines and borders
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS)
    
    # Define color levels
    minn = 0 #np.percentile(correlation_df[metric], 5)
    maxx = 1 #np.percentile(correlation_df[metric], 95)
    color_levels = np.linspace(minn, maxx, 11)
    
    # Define colormap and normalization
    cmap = plt.get_cmap('coolwarm')
    norm = BoundaryNorm(color_levels, ncolors=cmap.N, clip=True)
    
    # Scatter plot
    sc = ax.scatter(correlation_df['lon'], correlation_df['lat'], 
                    c=np.abs(correlation_df[metric]), cmap=cmap, norm=norm, 
                    s=50, edgecolors='k', transform=ccrs.PlateCarree())
    
    # txt = f"Median= {np.median(correlation_df[metric]):.2f} \nMean= {np.mean(correlation_df[metric]):.2f}"
    txt = f"Median= {np.median(correlation_df[metric]):.2f} ({np.median(Inundation_Dominated[metric]):.2f}) \nMean= {np.mean(correlation_df[metric]):.2f} ({np.mean(Inundation_Dominated[metric]):.2f})"
    ax.text(0.05, 0.05, txt, transform=ax.transAxes, fontsize=13, fontname='Arial', 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    # Title
    title_name = Names[i]
    ax.set_title(f"{title_name}", loc='left', fontsize=13.5, fontname='Arial')
    


# Add a single horizontal colorbar below all subplots
cbar_ax = fig.add_axes([0.11, - 0.02, 0.68, 0.015])  # Position: (left, bottom, width, height)
cbar = plt.colorbar(sc, cax=cbar_ax, orientation="horizontal",  ticks=color_levels, norm=norm)
cbar.ax.tick_params(labelsize=10)
cbar.ax.set_xlabel("Spearman Correlation", fontsize=13, fontname='Arial') # font size of the colorbar label

cbar.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%0.2f'))


# Adjust layout
plt.tight_layout(rect=[0, 0, 0.9, 1])  # Leave space for colorbar
plt.savefig(outdir + '/Figure_S_01' + '.png', dpi=600, bbox_inches='tight')

# plt.show(block=False)
plt.close()

del txt, title_name, sc, cmap, norm, cbar_ax, minn, maxx, color_levels, ax, fig, axes, 
del Par_cors, Names, i, metric 




#%% Supplementary Figure 2

sleceted_stations = ['05JE006','05123400','05MH005' ,'05053000','05059700','05051300']
province = ['Saskatchewan', 'North Dakota', 'Manitoba', 'North Dakota', 'North Dakota','Minnesota' ]

n = len (sleceted_stations )

fig = plt.figure(figsize=(20, 14))  # Adjust figsize as needed
gs = GridSpec(n, 8, width_ratios=[1,1,1,1,1,  1,1,1])
   
for i, st in enumerate(sleceted_stations):
    
    # first column: Inundation
    ax = fig.add_subplot(gs[i, 0])
    ax.scatter(Inundation[st]*100,  annual_P95_discharge_df[st]/annual_P95_prec_df[st])
    ax.set_ylabel('HFR', color='k', fontsize=18, fontname='Arial')
    if i == n-1:
        ax.set_xlabel('MIWA (%)', color='k', fontsize=18, fontname='Arial')
        
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_ROR95']:.2f}"
    ax.text(0.05, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    
    # Second column: Aridity
    ax = fig.add_subplot(gs[i, 1])
    ax.scatter(annual_Aridity[st],  annual_P95_discharge_df[st]/annual_P95_prec_df[st])
    #ax.set_ylabel('HFR', color='k', fontsize=13, fontname='Arial')
    if i == n-1:
        ax.set_xlabel('Aridity', color='k', fontsize=18, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Aridity_ROR95']:.2f}"
    ax.text(0.43, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        
    
    # Third column: Last year Aridity
    ax = fig.add_subplot(gs[i, 2])
    ax.scatter(annual_Last_Aridity[st],  LA_Matched_annual_P95_discharge_df[st]/LA_Matched_annual_P95_prec_df[st])
    #ax.set_ylabel('HFR', color='k', fontsize=13, fontname='Arial') 
    if i == n-1:
        ax.set_xlabel('Previous Year Aridity', color='k', fontsize=18, fontname='Arial')
        
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_LA_ROR95']:.2f}"
    ax.text(0.43, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        
        
        
    # fourth column: Snow Presenece
    ax = fig.add_subplot(gs[i, 3])
    ax.scatter(annual_Snow_Presence[st],  SP_Matched_annual_P95_discharge_df[st]/SP_Matched_annual_P95_prec_df[st])
    #ax.set_ylabel('HFR', color='k', fontsize=13, fontname='Arial') 
    if i == n-1:
        ax.set_xlabel('Snow Persistence', color='k', fontsize=18, fontname='Arial')
        
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_SP_ROR95']:.2f}"
    ax.text(0.05, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    
    
    # fourth column: NWI_MAX
    ax = fig.add_subplot(gs[i, 4])
    ax.scatter(ERA5_Monthly_NWI_Max[st],  annual_P95_discharge_df[st]/annual_P95_prec_df[st])
    #ax.set_ylabel('HFR', color='k', fontsize=13, fontname='Arial') 
    if i == n-1:
        ax.set_xlabel(r'NWI$_{MAX}$', color='k', fontsize=18, fontname='Arial')
        
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_NWIMax_ROR95']:.2f}"
    ax.text(0.05, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        
    
    
    # fifth column: LA-Inund
    ax = fig.add_subplot(gs[i, 5])
    ax.scatter(annual_Last_Aridity[st],  LA_Matched_Inundation[st]*100)
    ax.set_ylabel('MIWA (%)', color='k', fontsize=18, fontname='Arial') 
    if i == n-1:
        ax.set_xlabel('Previous Year Aridity', color='k', fontsize=18, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_LA']:.2f}"
    ax.text(0.43, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        
    
    
    # sixth column: SP-Inund
    ax = fig.add_subplot(gs[i, 6])
    ax.scatter(annual_Snow_Presence[st],  SP_Matched_Inundation[st]*100)
    # ax.set_ylabel('Inundation (%)', color='k', fontsize=13, fontname='Arial') 
    if i == n-1:
        ax.set_xlabel('Snow Persistence', color='k', fontsize=18, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_SP']:.2f}"
    ax.text(0.05, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    
    
    # fourth column: NWI_MAX
    ax = fig.add_subplot(gs[i, 7])
    ax.scatter(ERA5_Monthly_NWI_Max[st],  Inundation[st]*100)
    #ax.set_ylabel('HFR', color='k', fontsize=13, fontname='Arial') 
    if i == n-1:
        ax.set_xlabel(r'NWI$_{MAX}$', color='k', fontsize=18, fontname='Arial')
        
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_NWIMax']:.2f}"
    ax.text(0.05, 0.88, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    
    
        
        
# Adjust spacing between subplots to fit the title
plt.tight_layout(rect=[0, 0, 1, 1])

plt.savefig(outdir + '/Figure_S_02.png', dpi=600, bbox_inches='tight')    
      
# plt.show(block=False)
plt.close()  


#%% Supplementary Figure 3

Inundation_Dominated = total_dataset.loc[total_dataset['sub_class'].values == 1]


Par_cors = [ 'Spearman_Corr_Inund_SP', 'Spearman_Corr_Inund_LA', 'Spearman_Corr_Inund_NWIMax', 
             'Spearman_Corr_Inund_SF', 'Spearman_Corr_Inund_Aridity', 'Spearman_Corr_Inund_NWIApril',
              'Spearman_Corr_Inund_Rain95', 'Spearman_Corr_Inund_RainMax', 
            ]

Names = ['(a) MIWA vs. Snow Persistence', '(b) MIWA vs. PY-Aridity', r'(c) MIWA vs. NWI$_{MAX}$',
         '(d) MIWA vs. Snow Fraction', '(e) MIWA vs. Aridity', r'(c) MIWA vs. NWI$_{April}$',
          '(g) MIWA vs. Rainfall-95', '(h) MIWA vs. Maximum Rainfall', 
          ]


# Create a single figure with six subplots (3 rows, 2 columns)
fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(15, 12), subplot_kw={'projection': ccrs.PlateCarree()})

# Flatten the 2D axes array for easy iteration
axes = axes.flatten()

for i, metric in enumerate(Par_cors):
    ax = axes[i]  # Select the subplot
    
    prairie_watershed.plot(ax=ax, edgecolor='black', facecolor='none')

    # Add coastlines and borders
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS)
    
    # Define color levels
    minn = 0 #np.percentile(correlation_df[metric], 5)
    maxx = 1 #np.percentile(correlation_df[metric], 95)
    color_levels = np.linspace(minn, maxx, 11)
    
    # Define colormap and normalization
    cmap = plt.get_cmap('coolwarm')
    norm = BoundaryNorm(color_levels, ncolors=cmap.N, clip=True)
    
    # Scatter plot
    sc = ax.scatter(correlation_df['lon'], correlation_df['lat'], 
                    c=np.abs(correlation_df[metric]), cmap=cmap, norm=norm, 
                    s=50, edgecolors='k', transform=ccrs.PlateCarree())
    
    # txt = f"Median= {np.median(correlation_df[metric]):.2f} \nMean= {np.mean(correlation_df[metric]):.2f}"
    txt = f"Median= {np.median(correlation_df[metric]):.2f} ({np.median(Inundation_Dominated[metric]):.2f}) \nMean= {np.mean(correlation_df[metric]):.2f} ({np.mean(Inundation_Dominated[metric]):.2f})"
    ax.text(0.05, 0.05, txt, transform=ax.transAxes, fontsize=13, fontname='Arial', 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    # Title
    title_name = Names[i]
    ax.set_title(f"{title_name}", loc='left', fontsize=13.5, fontname='Arial')
    


# Add a single horizontal colorbar below all subplots
cbar_ax = fig.add_axes([0.11, - 0.02, 0.68, 0.015])  # Position: (left, bottom, width, height)
cbar = plt.colorbar(sc, cax=cbar_ax, orientation="horizontal",  ticks=color_levels, norm=norm)
cbar.ax.tick_params(labelsize=10)
cbar.ax.set_xlabel("Spearman Correlation", fontsize=13, fontname='Arial') # font size of the colorbar label

cbar.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%0.2f'))


# Adjust layout
plt.tight_layout(rect=[0, 0, 0.9, 1])  # Leave space for colorbar
plt.savefig(outdir + '/Figure_S_03.png', dpi=600, bbox_inches='tight')

# plt.show(block=False)
plt.close()

del txt, title_name, sc, cmap, norm, cbar_ax, minn, maxx, color_levels, ax, fig, axes, 
del Par_cors, Names, i, metric 


#%% Supplementary Figure 4

sleceted_stations = ['05JE006','05123400','05MH005' ]
province = ['Saskatchewan', 'North Dakota', 'Manitoba']



fig = plt.figure(figsize=(18, 8))  # Adjust figsize as needed
gs = GridSpec(3, 7, width_ratios=[1,1,1,0.0,1,1,1])
   
for i, st in enumerate(sleceted_stations):
    
    # First Row: PY-Aridity
    ax = fig.add_subplot(gs[0, i])

    ax.scatter(annual_Last_Aridity[st],  LA_Matched_annual_mean_discharge_df[st]/LA_Matched_annual_mean_prec_df[st])
    #ax.set_ylabel('ROR', color='k', fontsize=13, fontname='Arial') 
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
    ax.set_xlabel('PY-Aridity', color='k', fontsize=15, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_LA_ROR']:.2f}"
    ax.text(0.5, 0.9, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    title = st + ' (' + province[i] + ')'
    ax.set_title(title,fontsize=14, fontname='Arial')
    
    
    
    # Second Row: Inundation
    ax = fig.add_subplot(gs[1, i])
    ax.scatter(Inundation[st]*100,  annual_mean_discharge_df[st]/annual_mean_prec_df[st])

    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
    
    ax.set_xlabel('MIWA(%)', color='k', fontsize=15, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_ROR']:.2f}"
    ax.text(0.05, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    
    # Third Row: PYA-MIWA
    ax = fig.add_subplot(gs[2, i])
    ax.scatter(annual_Last_Aridity[st],  LA_Matched_Inundation[st]*100)
     
    if i == 0:
        ax.set_ylabel('MIWA (%)', color='k', fontsize=15, fontname='Arial')
    
    ax.set_xlabel('PY-Aridity', color='k', fontsize=15, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_LA']:.2f}"
    ax.text(0.5, 0.9, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    

sleceted_stations = ['05053000','05059700','05051300']
province = ['North Dakota', 'North Dakota','Minnesota' ]

for i, st in enumerate(sleceted_stations):
    
    # First Row: SP-ROR
    ax = fig.add_subplot(gs[0, i+4])

    ax.scatter(annual_Snow_Presence[st],  SP_Matched_annual_mean_discharge_df[st]/SP_Matched_annual_mean_prec_df[st])
    #ax.set_ylabel('ROR', color='k', fontsize=13, fontname='Arial') 
    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
    ax.set_xlabel('Snow Persistence', color='k', fontsize=15, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_SP_ROR']:.2f}"
    ax.text(0.05, 0.9, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    title = st + ' (' + province[i] + ')'
    ax.set_title(title,fontsize=14, fontname='Arial')
    
    
    
    
    # Second Row: Inundation
    ax = fig.add_subplot(gs[1, i+4])
    ax.scatter(Inundation[st]*100,  annual_mean_discharge_df[st]/annual_mean_prec_df[st])

    if i == 0:
        ax.set_ylabel('ROR', color='k', fontsize=15, fontname='Arial')
    
    ax.set_xlabel('MIWA(%)', color='k', fontsize=15, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_ROR']:.2f}"
    ax.text(0.05, 0.90, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))
    
    
    # Third Row: PYA-MIWA
    ax = fig.add_subplot(gs[2, i+4])
    ax.scatter(annual_Snow_Presence[st],  SP_Matched_Inundation[st]*100)
     
    if i == 0:
        ax.set_ylabel('MIWA (%)', color='k', fontsize=15, fontname='Arial')
    
    ax.set_xlabel('Snow Persistence', color='k', fontsize=15, fontname='Arial')
    
    txt = f"SC= {correlation_df.loc[st, 'Spearman_Corr_Inund_SP']:.2f}"
    ax.text(0.05, 0.9, txt, transform=ax.transAxes, fontsize=12, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='white'))  

    
    
      
        
# Adjust spacing between subplots to fit the title
plt.tight_layout(rect=[0, 0, 1, 1])

plt.savefig(outdir + '/Figure_S_04.png', dpi=600, bbox_inches='tight')    
      
# plt.show(block=False)  
plt.close() 















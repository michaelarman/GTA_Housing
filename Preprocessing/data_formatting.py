import pandas as pd
import os
import glob

# format data and save to csv
def format_excel(path):
  # path = "C://Users//Michael//MLS//MLS_Datasets"
  os.chdir(path)
  cities = os.listdir(path)
  if not os.path.exists('Housing csvs'):
      os.makedirs('Housing csvs')
  [os.makedirs(os.path.join(os.getcwd(),'Housing csvs', city)) for city in cities if not os.path.exists(os.path.join(os.getcwd(),'MLS_Datasets', city))]
  for city in cities:
    for dataset in os.listdir(path+'//'+city):
  # get first table and use values as features for the real table
      xl = pd.ExcelFile(path+'//'+city +'//'+ dataset,engine='xlrd')
      nrows = xl.book.sheet_by_index(0).nrows
      df = pd.read_excel(path+'//'+city +'//'+dataset, skiprows=3, usecols=[0,1], skipfooter=nrows - 6, engine='xlrd')
      geog = df['Value'].iloc[0]
      hometype = df['Value'].iloc[1].replace('/','_')
      df = pd.read_excel(path+'//'+city +'//'+ dataset, skiprows=8)
      df['Municipality'] = city
      df['Geography'] = geog
      df['HomeType'] = hometype
      df.to_csv(path+'//Housing csvs//'+ city +'//' + geog + '_' + hometype + '.csv')
  # overwrite file to same place 

  ## concatenate all csv files
  PATH = path+'//Housing csvs'
  EXT = "*.csv"
  all_csv_files = [file
                  for path, subdir, files in os.walk(PATH)
                  for file in glob.glob(os.path.join(path, EXT))]
  print(len(all_csv_files))

  df_from_each_file = (pd.read_csv(f) for f in all_csv_files)
  concatenated_df   = pd.concat(df_from_each_file, ignore_index=True)

  concatenated_df.to_csv(path+'/all_cities.csv', index=False)
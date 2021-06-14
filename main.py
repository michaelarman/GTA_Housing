import os
import subprocess
from Forecasting.model import get_forecasted_data
from Preprocessing.mls_download import *
from Preprocessing.data_formatting import format_excel


if __name__ == '__main__':
    # first obtain the data. This data is updated monthly and the way they set it up makes it very slow to scrape
    # and you can't use multithreading since a web driver (web driver's aren't thread-safe) 
    # is needed and it should be sequential. This could take up to 3 hours. Unfortunately even once you have data and 
    # want to update it, you'll still need to run the whole script
    path = '' # run this on the path you want the data to be in
    os.chdir(path)
    username = '' # username for treb
    password = '' # password for treb
    authenticator = '' # authentication code for treb
    login(username,password,authenticator)
    navigate()
    areas = ['Dufferin','Durham','Halton','Peel','Simcoe','Toronto','York']
    [os.makedirs(os.path.join(os.getcwd(),'MLS_Datasets', area)) for area in areas if not os.path.exists(os.path.join(os.getcwd(),'MLS_Datasets', area))]
    get_data()
    # after the data is collected we need to format it from ugly excel files to csv and then concatenate all of them
    format_excel(path+'/MLS_Datasets')
    # now we are ready for EDA. The ipynb is already done and so it just needs to be executed for the new data
    # this can possibly take a while too since it's quite an in depth analysis
    subprocess.run('jupyter nbconvert  --to notebook --execute "Housing exploration.ipynb"', shell = True)
    get_forecasted_data()
    

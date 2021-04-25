# -*- coding: utf-8 -*-

# Run this app with `python dash_app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
import dash_table
from dash_table.Format import Format, Group, Scheme, Symbol
import dash_table.FormatTemplate as FormatTemplate
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pyproj
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import geopandas 

external_stylesheets = [dbc.themes.LITERA]

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],external_stylesheets=external_stylesheets
)
server = app.server
# load and preprocess dataset
housing = pd.read_csv('webapp_data/all_cities.csv')
housing = housing.drop(columns='Unnamed: 0')
month = [x[0] for x in housing['Date'].str.split("'")]
year = [x[1] for x in housing['Date'].str.split("'")]
year = ['19'+x if x[0] == '9' else '20'+x for x in year]
housing['Date'] = pd.to_datetime(pd.Series(month).str.strip() + '/' + pd.Series(year))
housing.loc[housing["Average SP/LP"] == 770000, ['Average SP/LP']] = 1 #outlier

forecast_df = pd.read_csv('webapp_data/forecast_merge.csv')

# feature engineering for tables and plots
housing['Month'] = housing['Date'].dt.month
housing['Year'] = housing['Date'].dt.year
df_medians = housing.groupby(['Geography','HomeType','Year'])[['Sales','Average Price','New Listings','SNLR','Active Listings','MOI','Average DOM','Average SP/LP']].transform('median')

housing['Median Sales of Year'] = df_medians['Sales']
housing['Sales YoY'] = housing['Median Sales of Year'].pct_change(12)
housing['Median Price of Year'] = df_medians['Average Price']
housing['Price YoY'] = housing['Median Price of Year'].pct_change(12)
housing = housing.replace([np.inf, -np.inf], np.nan).fillna(0)
housing_without_allvals = housing[housing['HomeType'] != 'All values'] 
df = housing_without_allvals.copy()

# create lists for dropdown menus
geos = housing_without_allvals['Geography'].unique()
hometypes = housing_without_allvals['HomeType'].unique()
hometypes_including_all = housing['HomeType'].unique()
years = housing_without_allvals['Year'].unique()
# define the tables for the second tab
table = housing[(housing['HomeType'] == 'Detached')].groupby(['Municipality','Geography']).mean().reset_index()
table2 = housing[(housing['HomeType'] == 'Detached') & (housing['Date'].dt.year.isin([2015,2016,2017,2018,2019,2020]))].groupby(['Municipality','Geography']).mean().reset_index()
table3 = housing[(housing['HomeType'] == 'Detached') & (housing['Date'].dt.year.isin([2020]))].groupby(['Municipality','Geography']).mean().reset_index()
table4 = df.groupby(['Geography','HomeType'])['Price YoY'].mean().sort_values(ascending=False).reset_index()
table5 = df[df['Year'].isin([2015,2016,2017,2018,2019,2020])].groupby(['Geography','HomeType'])['Price YoY'].mean().sort_values(ascending=False).reset_index()
table6 = df[df['Year'].isin([2020])].groupby(['Geography','HomeType'])['Price YoY'].mean().sort_values(ascending=False).reset_index()

# define ROI
# example
ROI = ((df[(df['Geography'] == 'Toronto E01') & (df['HomeType'] == 'Detached')]['Median Price of Year'].iloc[-1] - df[(df['Geography'] == 'Toronto E01') & (df['HomeType'] == 'Detached')]['Median Price of Year'].iloc[0])/ df[(df['Geography'] == 'Toronto E01') & (df['HomeType'] == 'Detached')]['Median Price of Year'].iloc[0])
ROI = "{:.2%}".format(ROI)


# create folium map
df_detached_2021 = df[(df['HomeType'] == 'Detached')&(df['Year'].isin([2021]))].groupby(['Geography','HomeType']).mean().reset_index()
gdf = geopandas.read_file('webapp_data/municipal1.geojson')
gdf.rename(columns={'name':'Geography'}, inplace=True)
gdf.loc[(gdf['Geography'].str.contains('|'.join(['0','1','2','3','4','5','6','7','8','9']), case=False)), 'Geography'] = 'Toronto '+gdf['Geography']
gdf.loc[(gdf['Geography'].str.contains('Adjala')),'Geography'] = 'Adjala-Tosorontio'
joined_gdf = gdf.merge(df_detached_2021, on="Geography")
joined_gdf = joined_gdf.round(2)
joined_gdf.to_crs(pyproj.CRS.from_epsg(4326), inplace=True)
# plot base map
map_plot = px.choropleth_mapbox(joined_gdf, geojson=joined_gdf.set_index('Geography').geometry, locations='Geography', color='Average Price',
                           color_continuous_scale="sunsetdark",
                           mapbox_style="open-street-map",
                           zoom=7.8, center = {"lat": 43.9, "lon": -79.2},
                           opacity=0.5, hover_name='Geography', 
                           hover_data=['Average Price','Average SP/LP','HomeType','Sales','Average DOM','New Listings', 'SNLR', 'Active Listings', 'MOI','Price YoY'],
#                            animation_frame='Average DOM'
                           labels={'Sales':'Average Sales','New Listings':'Average New Listings','Active Listings':'Average Active Listings','SNLR':'Average SNLR','MOI':'Average MOI'}
                          )
map_plot.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
map_plot.update_geos(fitbounds="locations", visible=False)


# create figures for the first tab
fig = go.Figure()

# Add traces
fig.add_trace(
    go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Date'], 
                         y=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Average Price'],
                    mode='lines',
                    name='Average Price')
)

fig.add_trace(
    go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Date'], 
                         y=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Sales'],
                    mode='lines',
                    name='Sales', yaxis='y2'),
)


# Add figure title
fig.update_layout(
    title_text="Brampton Detached Homes"
)

# Set x-axis title
fig.update_xaxes(title_text="Date")
# Create axis objects
fig.update_layout(
    xaxis=dict(
        domain=[0.1, 1]
    ),
    yaxis=dict(
        title="Average Price",
        titlefont=dict(
            color="#1f77b4"
        ),
        tickfont=dict(
            color="#1f77b4"
        )
    ),
    yaxis2=dict(
        title="Sales",
        titlefont=dict(
            color="red"
        ),
        tickfont=dict(
            color="red"
        ),
        anchor="x",
        overlaying="y",
        side="right",
    ),


)



fig.update_xaxes(
    rangeslider_visible=True,
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
)

fig2 = go.Figure()

# Add traces
fig2.add_trace(
    go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Date'], 
                         y=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Average DOM'],
                    mode='lines',
                    name='Average DOM')
)
fig2.update_xaxes(title_text="Date")
fig2.update_yaxes(title_text="Average DOM")
fig2.update_xaxes(
    rangeslider_visible=True,
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
)

fig3 = go.Figure()
fig3.add_trace(
    go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Date'], 
                         y=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Average SP/LP'],
                    mode='lines',
                    name='Average SP/LP')
)
fig3.update_xaxes(title_text="Date")
fig3.update_yaxes(title_text="Average SP/LP")
fig3.update_xaxes(
    rangeslider_visible=True,
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
)

fig4 = go.Figure()
fig4.add_trace(
    go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Date'], 
                         y=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['MOI'],
                    mode='lines',
                    name='MOI')
)
fig4.update_xaxes(title_text="Date")
fig4.update_yaxes(title_text="MOI")
fig4.update_xaxes(
    rangeslider_visible=True,
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
)

fig5 = go.Figure()
fig5.add_trace(
    go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['Date'], 
                         y=housing_without_allvals[(housing_without_allvals['Geography'] == 'Brampton') & (housing_without_allvals['HomeType'] == 'Detached')]['SNLR'],
                    mode='lines',
                    name='SNLR')
)
fig5.update_xaxes(title_text="Date")
fig5.update_yaxes(title_text="SNLR")
fig5.update_xaxes(
    rangeslider_visible=True,
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
)

app.layout = html.Div(children=[
    html.H1(children='GTA Housing Overview'),
    html.Div(
            [
                html.A(
                    html.Button("Source Code", id="learn-more-button"),
                    href="https://plot.ly/dash/pricing/",
                )
            ],
            className="one-third column",
            id="button",
            style={'width': '10%', 'float':'right', 'display': 'inline-block'}),

    html.P(['This is a Dashboard used to gain insight on the housing market in the GTA and make comparisons with other municipalities and communities.',
    html.Br(),
    'This dashboard is aimed to help make data-driven decisions.'
    ]),
        dcc.Tabs(id='tabs', value='tab-1', children=[
        dcc.Tab(label='Plots', value='tab-1', children=[
  
    html.Div([

        html.Div([
            dcc.Dropdown(
                id='crossfilter-community',
                options=[{'label': i, 'value': i} for i in geos],
                value='Brampton',
                placeholder="Select a Community",
                clearable=False
            ),
        ],
        style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-hometypes',
                options=[{'label': i, 'value': i} for i in hometypes],
                value='Detached',
                placeholder="Select a HomeType",
                clearable=False
            ), 
        ], style={'width': '20%', 'display': 'inline-block'})
    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),

    dcc.Graph(
        id='crossfilter-indicator-scatter',
        figure=fig
    ),

    html.Div([
        html.H2("Buyers' Market vs. Sellers' Market Indicators"),
        html.Div([  
            dbc.Row([  
            dbc.Col([ 
            dcc.Markdown("The average days on the market can show quick homes are being sold. The higher the DOM is the more likely it is a buyer's market since there’ll be room to negotiate when the house does not sell quick. The inverse is true for a seller's market."),
            dcc.Graph(
            id='crossfilter-indicator-scatter2',
            figure=fig2),
                ]),
            dbc.Col([
            dcc.Markdown("Average Sold Price / Listing Price A higher ratio indicates more of a Sellers' market since people are paying more than asking. A lower ratio indicates more of a Buyers' market since people are paying less than asking."),
            dcc.Graph(id='g3', 
            figure=fig3), 
                ]),
            ]),
    ]),
    ]),
        html.Div([
        html.Div([  
            dbc.Row([  
            dbc.Col([
            dcc.Markdown("Months on Inventory shows the number of months it would take for all current listings (as of the end of each month) to sell. As the MOI moves higher, there are more Sellers than Buyers. As the MOI moves lower, there are more Buyers than Sellers (putting upward pressure on prices)."),
            dcc.Graph(
            id='g4',
            figure=fig4),
                ]),
            dbc.Col([
            dcc.Markdown("Sales to New Listing Ratio is the ratio between the number of homes sold and the number of new listings entered into the system during the month. Fifty per cent represents a balanced market. A higher ratio indicates more of a Sellers’ market; a lower ratio indicates more of a Buyers’ market."),
            dcc.Graph(id='g5', 
            figure=fig5), 
                ]),
            ]),
    ]),
    ]),
        ]),
        dcc.Tab(label='Table View', value='tab-2', children=[
        html.Div([
        
        html.Div([
            dcc.Input(
            id="input_range", type="number",value=0, placeholder="# of Sales",
            step=5, style={'width': '49%', 'height':'90%', 'display': 'inline-block'}
        ),
        ], style={'width': '49%', 'display': 'inline-block'}),
        html.Div([
            dcc.Dropdown(
                id='crossfilter-hometypes-tables',
                options=[{'label': i, 'value': i} for i in hometypes_including_all],
                value='Detached',
                placeholder="Select a HomeType",
            ), 
        ], style={'width': '49%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-hometypes-tables-year1',
                options=[{'label': i, 'value': i} for i in years],
                value=1996,
                placeholder="Select First Year",
            ), 
        ], style={'width': '49%', 'display': 'inline-block','height':'90%'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-hometypes-tables-year2',
                options=[{'label': i, 'value': i} for i in years],
                value=2021,
                placeholder="Select Second Year",
            ), 
        ], style={'width': '49%', 'display': 'inline-block'}),
    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),
    ### add price yoy maybe sales yoy
    html.Div([
        html.H2("Descriptive Statistics - Raw Data"),
            html.P('For those that would like to explore the raw data from throughout the years for the GTA housing market, below is the table that shows the historical averages per community. You can sort by any column which is useful to see which community performs best in whichever category. In the dropdown menu you can select any hometype and above that you can input a minimum number of sales since some values may be skewed when there are few number of sales. You can also choose the date range for the data and it is aggregated by mean'),
            html.Label("Averages of Home Type", style={'width': '100%', 'display': 'flex', 'align-items': 'center','font-weight':'bold','justify-content':'center'}),
            dash_table.DataTable(id='datatable-interactivity',
                    columns=[
                        {"name": "Municipality", "id": "Municipality", "type": "text"},
                        {"name": "Community", "id": "Geography", "type": "text"},
                        {"name": "Sales", "id": "Sales", "type": "numeric"},
                        {"name": "Dollar Volume ($)", "id": "Dollar Volume", "type": "numeric", 'format': FormatTemplate.money(2)},
                        {"name": "Average Price ($)", "id": "Average Price", "type": "numeric", 'format': FormatTemplate.money(2)},
                        {"name": "New Listings", "id": "New Listings", "type": "numeric"},
                        {"name": "Sales to New Listing Ratio", "id": "SNLR", "type": "numeric"},
                        {"name": "Active Listings", "id": "Active Listings", "type": "numeric"},
                        {"name": "Months on Inventory", "id": "MOI", "type": "numeric"},
                        {"name": "Average Days on Market", "id": "Average DOM", "type": "numeric"},
                        {"name": "Average Sold Price/Listing Price", "id": "Average SP/LP", "type": "numeric"},
                        {"name": "YoY Price (%)", "id": "Price YoY", "type": "numeric",'format': FormatTemplate.percentage(2)}
                    ],
                data=table.to_dict('records'),
                editable=False,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                row_selectable="multi",
                row_deletable=True,
                selected_columns=[],
                selected_rows=[],
                page_action="native",
                page_current= 0,
                page_size= 25,
            ),
            html.Div(id='datatable-interactivity-container')
        ]),
    html.Br(),
    html.H2("ROI Calculator"),
    html.Div([

        html.Div([
            dcc.Dropdown(
                id='crossfilter-community-ROI',
                options=[{'label': i, 'value': i} for i in geos],
                value='Toronto E01',
                placeholder="Select a Community",
                clearable=False
            ),
        ],
        style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-hometypes-ROI',
                options=[{'label': i, 'value': i} for i in hometypes],
                value='Detached',
                placeholder="Select a HomeType",
                clearable=False
            ), 
        ], style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-years-ROI-start',
                options=[{'label': i, 'value': i} for i in housing['Date'].dt.year.unique()],
                value=1996,
                placeholder="Select a Start Year",
                clearable=False
            ), 
        ], style={'width': '20%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-years-ROI-end',
                options=[{'label': i, 'value': i} for i in housing['Date'].dt.year.unique()],
                value=2020,
                placeholder="Select an End Year",
                clearable=False
            ), 
        ], style={'width': '20%', 'display': 'inline-block'}),

    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),
    html.Div([
        html.Br(),
        dcc.Markdown(ROI,id='roi')
    ])

    ]),
        dcc.Tab(label='Forecasts', value='tab-3', children=[
            html.Div([
                html.P('A forecast of Average Home Prices was created from the data using a Deep Learning Time Series model called the Temporal Fusion Transformer. See the source code for more details.'),
                html.P('In the table below is a summary of the results which show the year over year price change and the forecasted median price of the year.'),
                html.Label("Forecast of 2021", style={'width': '100%', 'display': 'flex', 'align-items': 'center','font-weight':'bold','justify-content':'center'}),
            dash_table.DataTable(id='datatable-interactivity-forecast',
                    columns=[
                        {"name": "Municipality", "id": "Municipality", "type": "text"},
                        {"name": "Community", "id": "Geography", "type": "text"},
                        {"name": "Home Type", "id": "HomeType", "type": "text"},
                        {"name": "Median Price of 2020","id": "Median Price of Year", "type": "numeric", "format": FormatTemplate.money(2)},
                        {"name": "Median Price of 2021", "id": "Median Price of 2021", "type": "numeric", "format": FormatTemplate.money(2)},
                        {"name": "YoY Price (%)", "id": "Price YoY", "type": "numeric",'format': FormatTemplate.percentage(2)}
                    ],
                data=forecast_df.to_dict('records'),
                editable=False,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                row_selectable="multi",
                row_deletable=True,
                selected_columns=[],
                selected_rows=[],
                page_action="native",
                page_current= 0,
                page_size= 25,
            ),
            html.Div(id='datatable-interactivity-container-forecast')
        ])
        ]),
        dcc.Tab(label='Map',value='tab-4', children=[
        html.Div([
                    html.Div([
            dcc.Dropdown(
            id="map-cross-filter-criteria",
            options=[{'label': i, 'value': i} for i in ['Average Price','Average SP/LP','Sales','Average DOM','New Listings', 'SNLR', 'Active Listings', 'MOI','Price YoY']], 
            value='Average Price',placeholder="Select Column For Legend",
        ),
        ], style={'width': '49%', 'display': 'inline-block'}),
        html.Div([
            dcc.Dropdown(
                id='map-crossfilter-hometypes',
                options=[{'label': i, 'value': i} for i in hometypes_including_all],
                value='Detached',
                placeholder="Select a HomeType",
            ), 
        ], style={'width': '49%', 'display': 'inline-block'}),

        html.Div([
            dcc.Dropdown(
                id='map-crossfilter-year1',
                options=[{'label': i, 'value': i} for i in years],
                value=2021,
                placeholder="Select Year",
            ), 
        ], style={'width': '49%', 'display': 'inline-block','height':'90%'}),

        html.Div([
            dcc.Dropdown(
                id='map-crossfilter-agg',
                options=[{'label': i, 'value': i} for i in ['mean','median','sum']],
                value='mean',
                placeholder="Select Aggregation Method",
            ), 
        ], style={'width': '49%', 'display': 'inline-block'}),
    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),
        dcc.Graph(
        id='map',
        figure=map_plot,style={'width': '100%', 'height': '90vh'},
    ),
            
        ])

        ]),
])


@app.callback(
    dash.dependencies.Output('crossfilter-indicator-scatter', 'figure'),
    [dash.dependencies.Input('crossfilter-community', 'value'),
     dash.dependencies.Input('crossfilter-hometypes', 'value')])
def callback_a(community, hometype):
    fig = go.Figure()

    # Add traces
    fig.add_trace(
        go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Date'], 
                            y=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Average Price'],
                        mode='lines',
                        name='Average Price')
    )

    fig.add_trace(
        go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Date'], 
                            y=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Sales'],
                        mode='lines',
                        name='Sales', yaxis='y2'),
    )

    # Add figure title
    fig.update_layout(
        title_text= str(community) +" "+ str(hometype) + " Homes"
    )

    # Set x-axis title
    fig.update_xaxes(title_text="Date")
    # Create axis objects
    fig.update_layout(
        xaxis=dict(
            domain=[0.1, 1]
        ),
        yaxis=dict(
            title="Average Price",
            titlefont=dict(
                color="#1f77b4"
            ),
            tickfont=dict(
                color="#1f77b4"
            )
        ),
        yaxis2=dict(
            title="Sales",
            titlefont=dict(
                color="red"
            ),
            tickfont=dict(
                color="red"
            ),
            anchor="x",
            overlaying="y",
            side="right",
            # position=0
        ),

    )

    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    return fig

@app.callback(
    dash.dependencies.Output('crossfilter-indicator-scatter2', 'figure'),
    [dash.dependencies.Input('crossfilter-community', 'value'),
     dash.dependencies.Input('crossfilter-hometypes', 'value')])
def callback_b(community, hometype):
    fig2 = go.Figure()

# Add traces
    fig2.add_trace(
        go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Date'], 
                            y=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Average DOM'],
                        mode='lines',
                        name='Average DOM')
    )
    fig2.update_layout(
        title_text= "Average Days on the Market for " + str(community) +" "+ str(hometype) + " Homes")
    fig2.update_xaxes(title_text="Date")
    fig2.update_yaxes(title_text="Average DOM")
    fig2.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    return fig2

@app.callback(
    dash.dependencies.Output('g3', 'figure'),
    [dash.dependencies.Input('crossfilter-community', 'value'),
     dash.dependencies.Input('crossfilter-hometypes', 'value')])
def callback_c(community, hometype):
    fig3 = go.Figure()

# Add traces
    fig3.add_trace(
        go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Date'], 
                            y=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Average SP/LP'],
                        mode='lines',
                        name='Average SP/LP')
    )
    fig3.update_layout(
        title_text= "Average Sales Price / Listing Price for " + str(community) +" "+ str(hometype) + " Homes")
    fig3.update_xaxes(title_text="Date")
    fig3.update_yaxes(title_text="Average SP/LP")
    fig3.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )
    return fig3

@app.callback(
    dash.dependencies.Output('g4', 'figure'),
    [dash.dependencies.Input('crossfilter-community', 'value'),
     dash.dependencies.Input('crossfilter-hometypes', 'value')])
def callback_d(community, hometype):
    fig4 = go.Figure()

# Add traces
    fig4.add_trace(
        go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Date'], 
                            y=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['MOI'],
                        mode='lines',
                        name='MOI')
    )
    fig4.update_layout(
        title_text= "Months on Inventory for " + str(community) +" "+ str(hometype) + " Homes")
    fig4.update_xaxes(title_text="Date")
    fig4.update_yaxes(title_text="MOI")
    fig4.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )
    return fig4

@app.callback(
    dash.dependencies.Output('g5', 'figure'),
    [dash.dependencies.Input('crossfilter-community', 'value'),
     dash.dependencies.Input('crossfilter-hometypes', 'value')])
def callback_e(community, hometype):
    fig5 = go.Figure()

# Add traces
    fig5.add_trace(
        go.Scatter(x=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['Date'], 
                            y=housing_without_allvals[(housing_without_allvals['Geography'] == community) & (housing_without_allvals['HomeType'] == hometype)]['SNLR'],
                        mode='lines',
                        name='SNLR')
    )
    fig5.update_layout(
        title_text= "Sales to New Listing Ratio for " + str(community) +" "+ str(hometype) + " Homes")
    fig5.update_xaxes(title_text="Date")
    fig5.update_yaxes(title_text="SNLR")
    fig5.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )
    return fig5

@app.callback(
    dash.dependencies.Output('datatable-interactivity', 'data'),
    [dash.dependencies.Input('input_range', 'value'), 
    dash.dependencies.Input('crossfilter-hometypes-tables', 'value'),
    dash.dependencies.Input('crossfilter-hometypes-tables-year1', 'value'),
    dash.dependencies.Input('crossfilter-hometypes-tables-year2', 'value')])
def callback_table1(sales_input, hometype, year1, year2):
    t = housing[(housing['HomeType'] == hometype) & (housing['Date'].dt.year.isin(list(range(int(year1),int(year2)+1))))].groupby(['Municipality','Geography']).mean().reset_index()
    table =  t.loc[t['Sales'] > sales_input].sort_values(by='Sales', ascending=False).reset_index(drop=True)
    table['Sales'] = table['Sales'].astype(int)
    table['New Listings'] = table['New Listings'].astype(int)
    table['SNLR'] = np.round(table['SNLR'],5)
    table['Active Listings'] = table['Active Listings'].astype(int)
    table['MOI'] = np.round(table['MOI'],5)
    table['Average DOM'] = np.round(table['Average DOM'],2)
    table['Average SP/LP'] = np.round(table['Average SP/LP'],5)
    table['Price YoY'] = np.round(table['Price YoY'],2)
    return table.to_dict('records')


@app.callback(
    dash.dependencies.Output('datatable-interactivity', 'style_data_conditional'),
    dash.dependencies.Input('datatable-interactivity', 'selected_columns'))
def update_styles(selected_columns):
    return [{
        'if': { 'column_id': i },
        'background_color': '#D2F3FF'
    } for i in selected_columns]

@app.callback(
    dash.dependencies.Output('datatable-interactivity-forecast', 'style_data_conditional'),
    dash.dependencies.Input('datatable-interactivity-forecast', 'selected_columns'))
def update_styles(selected_columns):
    return [{
        'if': { 'column_id': i },
        'background_color': '#D2F3FF'
    } for i in selected_columns]

@app.callback(
    dash.dependencies.Output('roi', 'children'),
    [dash.dependencies.Input('crossfilter-community-ROI', 'value'),
    dash.dependencies.Input('crossfilter-hometypes-ROI', 'value'),
    dash.dependencies.Input('crossfilter-years-ROI-start', 'value'),
    dash.dependencies.Input('crossfilter-years-ROI-end', 'value')])
def update_ROI(community,hometype,start,end):
    ROI = (df[(df['Geography'] == community) & (df['HomeType'] == hometype) & (df['Year'] == end)]['Median Price of Year'].iloc[0] - df[(df['Geography'] == community) & (df['HomeType'] == hometype) & (df['Year'] == start)]['Median Price of Year'].iloc[0]) / df[(df['Geography'] == community) & (df['HomeType'] == hometype) & (df['Year'] == start)]['Median Price of Year'].iloc[0]
    ROI = "{:.2%}".format(ROI)
    start_price = df[(df['Geography'] == community) & (df['HomeType'] == hometype) & (df['Year'] == start)]['Median Price of Year'].iloc[0]
    start_price = "${:,.2f}".format(start_price)
    end_price = df[(df['Geography'] == community) & (df['HomeType'] == hometype) & (df['Year'] == end)]['Median Price of Year'].iloc[0]
    end_price = "${:,.2f}".format(end_price)
    ROI = '''
              ### Average Price of Year {0} is {2} 
              ### Average Price of Year {1} is {3} 
              ### ROI = ( {2} - {3} ) / {3} 
              ### ROI = {4}'''.format(end,start,end_price,start_price,ROI)
    return ROI

@app.callback(
    dash.dependencies.Output('map', 'figure'),
    [dash.dependencies.Input('map-cross-filter-criteria', 'value'),
     dash.dependencies.Input('map-crossfilter-hometypes', 'value'),
     dash.dependencies.Input('map-crossfilter-year1','value'),
     dash.dependencies.Input('map-crossfilter-agg','value')])
def update_map(criteria,hometype,year,agg):
    df_map = df[(df['HomeType'] == hometype)&(df['Year'].isin([int(year)]))].groupby(['Geography','HomeType']).agg(agg).reset_index()

    joined_gdf = gdf.merge(df_map, on="Geography")
    joined_gdf = joined_gdf.round(2)
    joined_gdf.to_crs(pyproj.CRS.from_epsg(4326), inplace=True)
    # plot base map
    map_plot = px.choropleth_mapbox(joined_gdf, geojson=joined_gdf.set_index('Geography').geometry, locations='Geography', color=criteria,
                            color_continuous_scale="sunsetdark",
                            mapbox_style="open-street-map",
                            zoom=7.8, center = {"lat": 43.9, "lon": -79.2},
                            opacity=0.5, hover_name='Geography', 
                            hover_data=['Average Price','Average SP/LP','HomeType','Sales','Average DOM','New Listings', 'SNLR', 'Active Listings', 'MOI','Price YoY'],
                            labels={'Average Price':agg+' Price','Sales':agg+' Sales','Average DOM':agg+' DOM','Average SP/LP':agg+' SP/LP','New Listings':agg+' New Listings','Active Listings':agg+' Active Listings','SNLR':agg+' SNLR','MOI':agg+' MOI'}
                            )
    map_plot.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    map_plot.update_geos(fitbounds="locations", visible=False)
    return map_plot

if __name__ == '__main__':
    app.run_server()
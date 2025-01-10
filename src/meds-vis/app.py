# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.


from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
import polars as pl

app = Dash()

# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more options
# df = pl.scan_parquet("/Users/robin/Documents/datasets/meds/northwestern/data/train").select(pl.col("time").hist()).collect()
file_path = "/sc/arion/projects/hpims-hpi/projects/foundation_models_ehr/cohorts/meds/full_omop_source_concept_25_1_6/data"
# Create a lazyframe, convert the 'time' column to a datetime type, format it to year-month, convert to string, and calculate the histogram
df = (
    pl.scan_parquet(file_path)
    .filter((pl.col("time") >= pl.datetime(2000, 1, 1)) & (pl.col("time") <= pl.datetime(2025, 12, 31)))
    .with_columns(pl.col("time").dt.strftime("%Y-%m").cast(pl.String).alias("time_str"))
    .group_by("time_str")
    .agg(pl.count("time_str").alias("count"))
    .collect()
)
    #pd.DataFrame({
#     "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
#     "Amount": [4, 1, 2, 2, 4, 5],
#     "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
# }))

fig = px.histogram(df, x="time_str", y="count", nbins=len(df))

#bar(df, x="Fruit", y="Amount", color="City", barmode="group")

app.layout = html.Div(children=[
    html.H1(children='MEDS INSPECT'),

    html.Div(children='''
        Code count over the years
    '''),

    dcc.Graph(
        id='example-graph',
        figure=fig,
        style={'width': '90hh', 'height': '90vh'}
    )
])

if __name__ == '__main__':
    app.run(debug=True)

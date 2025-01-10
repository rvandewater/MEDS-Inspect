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
file_path = "/Users/robin/Documents/datasets/meds/northwestern/data/train"
# Create a lazyframe, convert the 'time' column to a datetime type, format it to year-month, convert to string, and calculate the histogram
df = (
    pl.scan_parquet(file_path)
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

fig = px.histogram(df, x="time_str", y="count")#bar(df, x="Fruit", y="Amount", color="City", barmode="group")

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])

if __name__ == '__main__':
    app.run(debug=True)

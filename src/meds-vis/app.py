import os
from pathlib import Path

import numpy as np
import polars as pl
from dash import Dash, html, dcc, Input, Output, State
import plotly.express as px
from cache_results import cache_results
from code_search import load_code_metadata, search_codes

def run_app(file_path):
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "MEDS INSPECT"

    code_count_years, code_count_subject, top_codes = cache_results(file_path)
    code_metadata = load_code_metadata(file_path + "metadata/codes.parquet")

    # Get unique patient IDs and codes
    patient_ids = code_count_subject['subject_id'].unique().to_list()
    codes = top_codes['code'].unique().to_list()

    app.layout = html.Div(children=[
        html.Div(
            children=html.Img(src='https://github.com/Medical-Event-Data-Standard/medical-event-data-standard.github.io/raw/main/static/img/logo.svg', style={'width': '200px'}),
            style={'textAlign': 'center'}
        ),
        html.H1(children='MEDS INSPECT 🔎', style={'textAlign': 'center'}),
        html.P(children='Explore and visualize your Medical Event Data Standard (MEDS) data.', style={'textAlign': 'center'}),
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Code count over the years', value='tab-1'),
            dcc.Tab(label='Code count per patient', value='tab-2'),
            dcc.Tab(label='Top most frequent codes', value='tab-3'),
            dcc.Tab(label='Codes over time for a single patient', value='tab-4'),
            dcc.Tab(label='Numerical distribution for a single code', value='tab-5'),
            dcc.Tab(label='Code Search', value='tab-6'),
        ]),
        html.Div(id='tabs-content')
    ], style={'fontFamily': 'Arial'})

    @app.callback(
        Output('tabs-content', 'children'),
        Input('tabs', 'value')
    )
    def render_content(tab):
        if tab == 'tab-1':
            fig_code_count_years = px.histogram(code_count_years, x="time_str", y="count", nbins=len(code_count_years))
            return html.Div([
                html.H2(children='Code count over the years'),
                dcc.Graph(
                    id='fig_code_count_years',
                    figure=fig_code_count_years,
                    style={'width': '90hh', 'height': '50vh'}
                )
            ])
        elif tab == 'tab-2':
            fig_code_count_subject = px.histogram(code_count_subject, y="subject_id", x="count")
            return html.Div([
                html.H2(children='Code count per patient'),
                dcc.Graph(
                    id='fig_code_count_subject',
                    figure=fig_code_count_subject,
                    style={'width': '90hh', 'height': '50vh'}
                )
            ])
        elif tab == 'tab-3':
            return html.Div([
                html.H2(children='Top most frequent codes'),
                dcc.Dropdown(
                    id='top-n-dropdown',
                    options=[
                        {'label': 'Top 10', 'value': 10},
                        {'label': 'Top 50', 'value': 50},
                        {'label': 'Top 100', 'value': 100},
                        {'label': 'Top 250', 'value': 250},
                        {'label': 'Top 500', 'value': 500}
                    ],
                    value=100,
                    placeholder='Select top N codes'
                ),
                dcc.Graph(
                    id='fig_top_codes',
                    style={'width': '90hh', 'height': '90vh'}
                )
            ])
        elif tab == 'tab-4':
            return html.Div([
                html.H2(children='Codes over time for a single patient'),
                dcc.Dropdown(
                    id='patient-dropdown',
                    options=[{'label': pid, 'value': pid} for pid in patient_ids],
                    placeholder='Select a patient ID'
                ),
                dcc.Graph(
                    id='fig_patient_codes',
                    style={'width': '90hh', 'height': '50vh'}
                )
            ])
        elif tab == 'tab-5':
            return html.Div([
                html.H2(children='Numerical distribution for a single code'),
                dcc.Dropdown(
                    id='code-dropdown',
                    options=[{'label': code, 'value': code} for code in codes],
                    placeholder='Select a code'
                ),
                dcc.Graph(
                    id='fig_code_distribution',
                    style={'width': '90hh', 'height': '50vh'}
                )
            ])
        elif tab == 'tab-6':
            return html.Div([
                html.H2(children='Code Search'),
                dcc.Input(id='search-term', type='text', placeholder='Enter code or description', n_submit=0),
                dcc.Dropdown(
                    id='search-options',
                    options=[
                        {'label': 'Code', 'value': 'code'},
                        {'label': 'Description', 'value': 'description'},
                        {'label': 'Parent Code', 'value': 'parent_codes'}
                    ],
                    value=['code', 'description', 'parent_codes'],
                    multi=True,
                    placeholder='Select search fields'
                ),
                html.Button('Search', id='search-button'),
                html.Div(id='search-results')
            ])

    @app.callback(
        Output('search-results', 'children'),
        Input('search-button', 'n_clicks'),
        Input('search-term', 'n_submit'),
        State('search-term', 'value'),
        State('search-options', 'value')
    )
    def update_search_results(n_clicks, n_submit, search_term, search_options):
        if (n_clicks is None and n_submit == 0) or not search_term:
            return "Enter a search term to find codes."

        results = search_codes(code_metadata, search_term, search_options)
        if len(results) == 0:
            return "No results found."

        return html.Table([
            html.Thead(html.Tr([html.Th(col) for col in results.columns])),
            html.Tbody([
                html.Tr([html.Td(results[col].to_list()[i]) for col in results.columns])
                for i in range(len(results))
            ])
        ])

    @app.callback(
        Output('fig_top_codes', 'figure'),
        Input('top-n-dropdown', 'value')
    )
    def update_top_codes(top_n):
        top_codes = (
            pl.scan_parquet(Path(file_path) / "data/*/*.parquet")
            .group_by("code")
            .agg(pl.count("code").alias("count"))
            .sort("count", descending=True)
            .limit(top_n)
            .collect()
        )

        fig_top_codes = px.bar(top_codes, x="count", y="code", orientation="h",
                               title=f"Top {top_n} most frequent codes")
        return fig_top_codes

    @app.callback(
        Output('fig_patient_codes', 'figure'),
        Input('patient-dropdown', 'value')
    )
    def update_patient_codes(patient_id):
        if patient_id is None:
            return {}

        patient_data = (
            pl.scan_parquet(Path(file_path) / "data/*/*.parquet")
            .filter(pl.col("subject_id") == patient_id)
            .select(pl.col("time"), pl.col("code"))
            .collect()
        )

        if patient_data.is_empty():
            return {}

        fig_patient_codes = px.scatter(patient_data, x="time", y="code",
                                       title=f"Codes over time for patient {patient_id}")
        return fig_patient_codes

    @app.callback(
        Output('fig_code_distribution', 'figure'),
        Input('code-dropdown', 'value')
    )
    def update_code_distribution(code):
        if code is None:
            return {}

        code_data = (
            pl.scan_parquet(Path(file_path) / "data/*/*.parquet")
            .filter((pl.col("code") == code) & (pl.col("numeric_value").is_not_null()))
            .select(pl.col("numeric_value"))
            .collect()
        )

        if code_data.is_empty():
            return {}

        # Calculate IQR and boundaries
        q1 = code_data['numeric_value'].quantile(0.25)
        q3 = code_data['numeric_value'].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Calculate the number of bins using the Freedman-Diaconis rule
        bin_width = 2 * iqr / np.cbrt(len(code_data))
        num_bins = int((upper_bound - lower_bound) / bin_width)

        fig_code_distribution = px.histogram(
            code_data,
            x="numeric_value",
            title=f"Numerical distribution for code {code}",
            range_x=[lower_bound, upper_bound],
            nbins=num_bins
        )
        return fig_code_distribution

    app.run(debug=True)

# Example usage
if __name__ == '__main__':
    file_path = "/Users/robin/Documents/datasets/meds/northwestern/"
    run_app(file_path)
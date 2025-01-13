import logging
import os
from pathlib import Path
import asyncio

import numpy as np
import polars as pl
from dash import Dash, html, dcc, Input, Output, State, callback_context
import plotly.express as px
from cache_results import cache_results
from code_search import load_code_metadata, search_codes
from utils import get_folder_size, is_valid_path

# Global variable to store cached results
cached_results = None


def run_app(file_path=None):
    global cached_results

    if file_path and is_valid_path(file_path):
        cached_results = cache_results(file_path)

    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "MEDS INSPECT"
    server = app.server
    app.layout = html.Div(children=[
        html.Div(
            children=html.Img(
                src='https://github.com/Medical-Event-Data-Standard/medical-event-data-standard.github.io/raw/main/static/img/logo.svg',
                style={'width': '200px'}),
            style={'textAlign': 'center'}
        ),
        html.H1(children='MEDS INSPECT 🕵️', style={'textAlign': 'center'}),
        html.P(children='Explore and visualize your Medical Event Data Standard (MEDS) data.',
               style={'textAlign': 'center', 'fontSize': '20px'}),
        dcc.Input(id='hidden-file-path', type='hidden', value=file_path,
                  style={"textAlign": "center", "fontSize": "20px"}),
        html.Div(id='path-feedback', style={'marginTop': '10px', 'color': 'green', 'textAlign': 'center'}),
        html.Div([
            dcc.Input(id='input-path', type='text', placeholder='Enter folder path',
                      style={'width': '80%', 'margin': '0 auto', 'display': 'block', 'fontSize': '20px'}),
            html.Button('Inspect 🔎', id='submit-path', n_clicks=0,
                        style={'display': 'block', 'margin': '20px auto', 'fontSize': '20px'}),
            dcc.Loading(
                id='loading-feedback',
                type='circle',
                children=[
                    html.Div(id='loading-output')
                ],
                overlay_style={"visibility": "visible", "filter": "blur(2px)"},
            )
        ], style={'marginTop': '20px'}),
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='📅 Yearly Overview', value='tab-1'),
            dcc.Tab(label='👤 Per Patient Codes', value='tab-2'),
            dcc.Tab(label='🏆 Top Codes', value='tab-3'),
            dcc.Tab(label='🕒 Patient Timeline', value='tab-4'),
            dcc.Tab(label='📊 Code Distribution', value='tab-5'),
            dcc.Tab(label='🔍 Code Search', value='tab-6'),
            dcc.Tab(label='📖 Coding Dictionary', value='tab-7')
        ]),
        dcc.Loading(
            id='loading-tabs-content',
            type='default',
            children=html.Div(id='tabs-content')
        )
    ], style={'fontFamily': 'Helvetica', 'marginLeft': '30px', 'marginRight': '30px'})

    @app.callback(
        Output('hidden-file-path', 'value'),
        Output('path-feedback', 'children'),
        Output('loading-output', 'children'),
        Input('submit-path', 'n_clicks'),
        State('input-path', 'value'),
        State('hidden-file-path', 'value')
    )
    def update_hidden_path(n_clicks, input_path, current_path):
        global cached_results

        if n_clicks == 0:
            return current_path, ('Enter the path to your MEDS data folder to get started. '
                                  'The first run will run several queries on the dataset; '
                                  'this might take a while depending on the dataset size.'), ''
        if n_clicks > 0 and is_valid_path(input_path):
            folder_size = get_folder_size(input_path)
            size_in_mb = folder_size / (1024 * 1024)
            print(f"loading cached results at: {input_path}")
            cached_results = cache_results(input_path)
            feedback_message = f'Selected folder: {input_path} (Size: {size_in_mb:.2f} MB). Caching complete.'
            return input_path, feedback_message, ''
        return current_path, 'Invalid folder path. Please try again.', ''

    @app.callback(
        Output('tabs-content', 'children'),
        Input('tabs', 'value'),
        State('hidden-file-path', 'value')
    )
    def render_content(tab, file_path):
        if not file_path:
            return html.Div('No folder selected. Please enter a valid folder path to proceed.')

        code_count_years, code_count_subject, top_codes, coding_dict = cached_results

        # Get unique patient IDs and codes
        patient_ids = code_count_subject['subject_id'].unique().to_list()
        codes = top_codes['code'].unique().to_list()

        content_style = {'border': '2px solid #007BFF', 'padding': '10px', 'borderRadius': '5px'}

        if tab == 'tab-1':
            fig_code_count_years = px.histogram(code_count_years, x="Month/Year", y="Amount of codes", nbins=len(code_count_years))
            return html.Div([
                html.H2(children='Code count over the years'),
                dcc.Loading(
                    id='loading-fig-code-count-years',
                    type='default',
                    children=dcc.Graph(
                        id='fig_code_count_years',
                        figure=fig_code_count_years,
                        style={'width': '90hh', 'height': '50vh'}
                    )
                )
            ], style=content_style)
        elif tab == 'tab-2':
            fig_code_count_subject = px.histogram(code_count_subject, y="subject_id", x="count", histfunc="count",
                                                  title="Code count distribution per patient",
                                                  labels={"count": "Code count", "count": "Amount of patients"})
            return html.Div([
                html.H2(children='Code count per patient'),
                dcc.Loading(
                    id='loading-fig-code-count-subject',
                    type='default',
                    children=dcc.Graph(
                        id='fig_code_count_subject',
                        figure=fig_code_count_subject,
                        style={'width': '90hh', 'height': '90vh'}
                    )
                )
            ], style=content_style)
        elif tab == 'tab-3':
            return html.Div([
                html.H2(children='Top most frequent codes'),
                dcc.Dropdown(
                    id='top-n-dropdown',
                    options=[
                        {'label': 'Top 10', 'value': 10},
                        {'label': 'Top 50', 'value': 50},
                        {'label': 'Top 100', 'value': 100}
                    ],
                    value=100,
                    placeholder='Select top N codes'
                ),
                dcc.Loading(
                    id='loading-fig-top-codes',
                    type='default',
                    children=dcc.Graph(
                        id='fig_top_codes',
                        style={'width': '90hh', 'height': '90vh'}
                    )
                )
            ], style=content_style)
        elif tab == 'tab-4':
            return html.Div([
                html.H2(children='Codes over time for a single patient'),
                dcc.Dropdown(
                    id='patient-dropdown',
                    options=[{'label': pid, 'value': pid} for pid in patient_ids],
                    placeholder='Select a patient ID'
                ),
                dcc.Loading(
                    id='loading-fig-patient-codes',
                    type='default',
                    children=dcc.Graph(
                        id='fig_patient_codes',
                        style={'width': '90hh', 'height': '50vh'}
                    )
                )
            ], style=content_style)
        elif tab == 'tab-5':
            return html.Div([
                html.H2(children='Numerical distribution for a single code'),
                dcc.Dropdown(
                    id='code-dropdown',
                    options=[{'label': code, 'value': code} for code in codes],
                    placeholder='Select a code'
                ),
                dcc.Loading(
                    id='loading-fig-code-distribution',
                    type='default',
                    children=dcc.Graph(
                        id='fig_code_distribution',
                        style={'width': '90hh', 'height': '50vh'}
                    )
                )
            ], style=content_style)
        elif tab == 'tab-6':
            return html.Div([
                html.H2(children='Code Search'),
                dcc.Input(id='search-term', type='text', placeholder='Enter code or description', n_submit=0),
                dcc.Dropdown(
                    id='search-options',
                    options=[
                        {'label': 'Code', 'value': 'code'},
                        {'label': 'Description', 'value': 'description'},
                        {'label': 'Parent Codes', 'value': 'parent_codes'}
                    ],
                    value=['code', 'description', 'parent_codes'],
                    multi=True,
                    placeholder='Select search fields'
                ),
                html.Button('Search', id='search-button'),
                dcc.Loading(
                    id='loading-search-results',
                    type='default',
                    children=html.Div(id='search-results')
                )
            ], style=content_style)
        elif tab == 'tab-7':
            fig_coding_dict = px.bar(coding_dict.limit(1000), x="coding_dict", y="count", title="Coding Dictionary Overview",
                                     color="coding_dict")
            return html.Div([
                html.H2(children='Coding Dictionary Overview'),
                dcc.Loading(
                    id='loading-fig-coding-dict',
                    type='default',
                    children=dcc.Graph(
                        id='fig_coding_dict',
                        figure=fig_coding_dict,
                        style={'width': '90hh', 'height': '90vh'}
                    )
                )
            ], style=content_style)

    @app.callback(
        Output('search-results', 'children'),
        Input('search-button', 'n_clicks'),
        Input('search-term', 'n_submit'),
        State('search-term', 'value'),
        State('search-options', 'value'),
        State('hidden-file-path', 'value')
    )
    def update_search_results(n_clicks, n_submit, search_term, search_options, file_path):
        if (n_clicks is None and n_submit == 0) or not search_term:
            return "Enter a search term to find codes."

        code_metadata = load_code_metadata(file_path + "/metadata/codes.parquet")
        results = search_codes(code_metadata, search_term, search_options)
        if len(results) == 0:
            return "No results found."

        return [html.Tbody([f"Found {len(results)} results" if len(results) < 1000
                            else "Showing first 1000 results found. Please refine search"]),
                html.Table([
                    html.Thead(html.Tr([html.Th(col) for col in results.columns])),
                    html.Tbody([
                        html.Tr([html.Td(results[col].to_list()[i]) for col in results.columns])
                        for i in range(len(results))
                    ])
                ])]

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
    logging.format = '%(asctime)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    file_path = "/Users/robin/Documents/datasets/meds/northwestern/"  # Set to None to prompt folder selection
    run_app(file_path)

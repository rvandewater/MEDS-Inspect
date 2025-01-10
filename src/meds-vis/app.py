import os
from pathlib import Path

import numpy as np
import polars as pl
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
from cache_results import cache_results


def run_app(file_path):
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "MEDS INSPECT"

    top_n = 100  # Adjust this value to change the number of top codes to cache
    code_count_years, code_count_subject, top_codes = cache_results(file_path, top_n)

    # Get unique patient IDs and codes
    patient_ids = code_count_subject['subject_id'].unique().to_list()
    codes = top_codes['code'].unique().to_list()

    app.layout = html.Div(children=[
        html.Div(
            children=html.Img(src='https://github.com/Medical-Event-Data-Standard/medical-event-data-standard.github.io/raw/main/static/img/logo.svg', style={'width': '200px'}),
            style={'textAlign': 'center'}
        ),
        html.H1(children='MEDS INSPECT 🔎', style={'textAlign': 'center'}),

        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Code count over the years', value='tab-1'),
            dcc.Tab(label='Code count per patient', value='tab-2'),
            dcc.Tab(label=f'Top {top_n} most frequent codes', value='tab-3'),
            dcc.Tab(label='Codes over time for a single patient', value='tab-4'),
            dcc.Tab(label='Numerical distribution for a single code', value='tab-5'),
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
            fig_top_codes = px.bar(top_codes, x="count", y="code", orientation="h")
            return html.Div([
                html.H2(children=f'Top {top_n} most frequent codes'),
                dcc.Graph(
                    id='fig_top_codes',
                    figure=fig_top_codes,
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
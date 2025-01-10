import os
from pathlib import Path
import polars as pl
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
from cache_results import cache_results


def run_app(file_path):
    app = Dash()

    top_n = 100  # Adjust this value to change the number of top codes to cache
    code_count_years, code_count_subject, top_codes = cache_results(file_path, top_n)

    fig_code_count_years = px.histogram(code_count_years, x="time_str", y="count", nbins=len(code_count_years))
    fig_code_count_subject = px.histogram(code_count_subject, y="subject_id", x="count")
    fig_top_codes = px.bar(top_codes, x="count", y="code", orientation="h")

    # Get unique patient IDs
    patient_ids = code_count_subject['subject_id'].unique().to_list()

    app.layout = html.Div(children=[
        html.H1(children='MEDS INSPECT'),

        html.H2(children='Code count over the years'),
        dcc.Graph(
            id='fig_code_count_years',
            figure=fig_code_count_years,
            style={'width': '90hh', 'height': '90vh'}
        ),
        html.H2(children='Code count per patient'),
        dcc.Graph(
            id='fig_code_count_subject',
            figure=fig_code_count_subject,
            style={'width': '90hh', 'height': '90vh'}
        ),
        html.H2(children=f'Top {top_n} most frequent codes'),
        dcc.Graph(
            id='fig_top_codes',
            figure=fig_top_codes,
            style={'width': '90hh', 'height': '90vh'}
        ),
        html.H2(children='Codes over time for a single patient'),
        dcc.Dropdown(
            id='patient-dropdown',
            options=[{'label': pid, 'value': pid} for pid in patient_ids],
            placeholder='Select a patient ID'
        ),
        dcc.Graph(
            id='fig_patient_codes',
            style={'width': '90hh', 'height': '90vh'}
        ),
    ], style={'fontFamily': 'Arial'})

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

    app.run(debug=True)


# Example usage
if __name__ == '__main__':
    file_path = "/Users/robin/Documents/datasets/meds/northwestern/"
    run_app(file_path)
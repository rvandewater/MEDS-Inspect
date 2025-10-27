import importlib.resources as pkg_resources
import logging
import os

import pandas as pd
import plotly.express as px
import polars as pl
from dash import Dash, Input, Output, State, dash_table, dcc, html
from omegaconf import DictConfig

from .cache.cache_results import cache_results, get_metadata
from .code_search import load_code_metadata, search_codes
from .utils import is_valid_path, return_data_path

package_name = "MEDS_Inspect"
sample_data_path = None
top_codes = None
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "MEDS INSPECT"
server = app.server
cached_results = None
metadata = None
card_style = {"border": "2px solid #007BFF", "padding": "10px", "borderRadius": "5px"}
standard_style = {
    "fontfamily": "Helvetica",
    # "bottom": "0",
    # "left": "0",
    "line-height": "34px",
    "padding-left": "10px",
    "padding-right": "10px",
    "right": "0",
    "top": "0",
    "max-width": "100%",
    "overflow": "hidden",
    "text-overflow": "ellipsis",
    # "white-space": "nowrap",
}


def run_app(cfg: DictConfig = None):
    global top_codes
    global cached_results
    global metadata

    sample_data_path = (
        cfg.sample_data_path
        if cfg.sample_data_path
        else f"{pkg_resources.files(package_name)}/assets/MIMIC-IV-DEMO-MEDS"
    )

    # Set the file_path to the downloaded directory
    file_path = cfg.initial_path if cfg.initial_path else sample_data_path

    # Global variable to store cached results
    cached_results = None

    # file_path=None

    # if file_path and is_valid_path(file_path):
    logging.info(f"loading cached results at: {file_path}")
    metadata = get_metadata(file_path)
    cached_results = cache_results(file_path)
    code_count_years = cached_results["code_count_years"]
    code_count_subject = cached_results["code_count_subjects"]
    top_codes = cached_results["top_codes"]
    coding_dict = cached_results["coding_dict"]
    numerical_code_data = cached_results["numerical_code_data"]
    if len(coding_dict) > cfg.limits.subject_ids:
        subject_ids = cached_results["code_count_subjects"]["Subject ID"].to_list()
    else:
        subject_ids = None
    app.layout = html.Div(
        children=[
            html.Div(
                children=html.Img(
                    src="https://github.com/Medical-Event-Data-Standard/medical-event-data-standard."
                    "github.io/raw/main/static/img/logo.svg",
                    style={"width": "200px"},
                ),
                style={"textAlign": "center"},
            ),
            html.H1(children="🕵️ MEDS-Inspect", style={"textAlign": "center"}),
            html.P(
                children="Explore and visualize your Medical Event Data Standard (MEDS) data.",
                style={"textAlign": "center", "fontSize": "20px"},
            ),
            dcc.Input(
                id="hidden-file-path",
                type="hidden",
                value=file_path,
                style={"textAlign": "center", "fontSize": "20px"},
            ),
            html.Div(
                id="path-feedback",
                style={"marginTop": "10px", "color": "green", "textAlign": "center"},
            ),
            html.Div(
                [
                    dcc.Input(
                        id="input-path",
                        type="text",
                        placeholder="Enter folder path",
                        style={
                            "width": "80%",
                            "margin": "0 auto",
                            "display": "block",
                            "fontSize": "20px",
                        },
                    ),
                    html.Button(
                        "Inspect 🔎",
                        id="submit-path",
                        n_clicks=0,
                        style={
                            "display": "block",
                            "margin": "20px auto",
                            "fontSize": "20px",
                        },
                    ),
                    dcc.Loading(
                        id="loading-feedback",
                        type="circle",
                        children=[html.Div(id="loading-output")],
                        overlay_style={"visibility": "visible", "filter": "blur(2px)"},
                    ),
                ],
                style={"marginTop": "20px"},
            ),
            html.Div(id="general-stats"),
            dcc.Tabs(
                id="tabs",
                value="tab-1",
                children=[
                    dcc.Tab(label="📅 Yearly Overview", value="tab-1"),
                    dcc.Tab(label="👤 Per subject Codes", value="tab-2"),
                    dcc.Tab(label="🏆 Top Codes", value="tab-3"),
                    dcc.Tab(label="🕒 Subject Timeline", value="tab-4"),
                    dcc.Tab(label="📊 Code Distribution", value="tab-5"),
                    dcc.Tab(label="🔍 Code Search", value="tab-6"),
                    dcc.Tab(label="📖 Coding Dictionary", value="tab-7"),
                ],
            ),
            dcc.Loading(
                id="loading-tabs-content",
                type="default",
                children=html.Div(id="tabs-content"),
            ),
        ],
        style={"fontFamily": "Helvetica", "marginLeft": "30px", "marginRight": "30px"},
    )

    @app.callback(
        Output("hidden-file-path", "value"),
        Output("path-feedback", "children"),
        Output("loading-output", "children"),
        Input("submit-path", "n_clicks"),
        State("input-path", "value"),
        State("hidden-file-path", "value"),
    )
    def update_hidden_path(n_clicks, input_path, current_path):
        global cached_results
        global metadata
        if n_clicks == 0:
            return (
                current_path,
                (
                    "Enter the path to your MEDS data folder to get started. "
                    "The first time we will run several (lazily evaluated) queries on the dataset "
                    "and cache the results; "
                    "this could take between a few seconds and a few minutes (for larger datasets)."
                ),
                "",
            )
        if n_clicks > 0 and is_valid_path(input_path):
            print(f"loading cached results at: {input_path}")
            cached_results = cache_results(input_path)
            metadata = get_metadata(input_path)
            feedback_message = f"Selected folder: {input_path}. Caching complete."
            return input_path, feedback_message, ""
        return current_path, "Invalid folder path. Please try again.", ""

    @app.callback(
        Output("tabs-content", "children"),
        Input("tabs", "value"),
        State("hidden-file-path", "value"),
    )
    def render_content(tab, file_path):
        if not file_path:
            return html.Div(
                "No folder selected. Please enter a valid folder path to proceed."
            )

        # Get unique subject IDs and codes
        # codes = top_codes['code'].unique().to_list()

        numerical_codes = (
            numerical_code_data.select("code").unique().collect()["code"].to_list()
        )

        if tab == "tab-1":
            fig_code_count_years = px.histogram(
                code_count_years,
                x="Date",
                y="Amount of codes",
                nbins=len(code_count_years),
            )
            return html.Div(
                [
                    html.H2(
                        children="Code count over time", style={"textAlign": "center"}
                    ),
                    html.P(children="Adjust the number of bins:"),
                    dcc.Slider(
                        id="bins-slider-years",
                        min=1,
                        max=len(code_count_years + 1),
                        step=1,
                        value=len(code_count_years),
                        marks={
                            i: str(i)
                            for i in range(
                                1,
                                len(code_count_years) + 1,
                                max(1, len(code_count_years) // 10),
                            )
                        },
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                    html.P(children="Select the histogram normalization:"),
                    dcc.Dropdown(
                        id="histnorm-dropdown-years",
                        options=[
                            {"label": "None", "value": ""},
                            {"label": "Probability", "value": "probability"},
                            {
                                "label": "Probability Density",
                                "value": "probability density",
                            },
                            {"label": "Density", "value": "density"},
                            {"label": "Percent", "value": "percent"},
                        ],
                        value="",
                        placeholder="Select histogram normalization",
                    ),
                    dcc.Loading(
                        id="loading-fig-code-count-years",
                        type="default",
                        children=dcc.Graph(
                            id="fig_code_count_years",
                            figure=fig_code_count_years,
                            style={"width": "90hh", "height": "50vh"},
                        ),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-2":
            fig_code_count_subject = px.histogram(
                code_count_subject,
                y="Subject ID",
                x="Code count",
                histfunc="count",
                histnorm="probability",
                title="Code count distribution per subject",
            ).update_layout(yaxis_title="Segment of Subjects")
            return html.Div(
                [
                    html.H2(
                        children="Code count per subject", style={"textAlign": "center"}
                    ),
                    html.P(children="Select the histogram normalization:"),
                    dcc.Dropdown(
                        id="histnorm-dropdown",
                        options=[
                            {"label": "None", "value": ""},
                            {"label": "Probability", "value": "probability"},
                            {
                                "label": "Probability Density",
                                "value": "probability density",
                            },
                            {"label": "Density", "value": "density"},
                            {"label": "Percent", "value": "percent"},
                        ],
                        value="",
                        placeholder="Select histogram normalization",
                    ),
                    html.P(children="Adjust the number of bins."),
                    dcc.Slider(
                        id="bins-slider",
                        min=10,
                        max=100,
                        step=5,
                        value=10,
                        marks={i: str(i) for i in range(10, 101, 10)},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                    dcc.Loading(
                        id="loading-fig-code-count-subject",
                        type="default",
                        children=dcc.Graph(
                            id="fig_code_count_subject",
                            figure=fig_code_count_subject,
                            style={"width": "90hh", "height": "90vh"},
                        ),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-3":
            return html.Div(
                [
                    html.H2(
                        children="Top most frequent codes",
                        style={"textAlign": "center"},
                    ),
                    dcc.Dropdown(
                        id="top-n-dropdown",
                        options=[
                            {"label": "Top 10", "value": 10},
                            {"label": "Top 50", "value": 50},
                            {"label": "Top 100", "value": 100},
                        ],
                        value=10,
                        placeholder="Select top N codes",
                    ),
                    html.P(children="Select the scale:"),
                    dcc.Dropdown(
                        id="scale-dropdown-top-codes",
                        options=[
                            {"label": "Linear", "value": "linear"},
                            {"label": "Log", "value": "log"},
                        ],
                        value="linear",
                        placeholder="Select scale",
                    ),
                    dcc.Loading(
                        id="loading-fig-top-codes",
                        type="default",
                        children=dcc.Graph(
                            id="fig_top_codes",
                            style={"width": "90hh", "height": "90vh"},
                        ),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-4":
            subject_input = (
                dcc.Input(
                    id="subject-input",
                    type="number",
                    placeholder="Enter a subject ID",
                    value=None,
                    style=dict({"width": "100%"}, **standard_style),
                )
                if not subject_ids
                else dcc.Dropdown(
                    id="subject-input",
                    options=[{"label": pid, "value": pid} for pid in subject_ids],
                    placeholder="Select a subject ID",
                    value=None,
                    multi=False,
                    searchable=True,
                    clearable=True,
                    style={"width": "100%"},
                )
            )
            return html.Div(
                [
                    html.H2(
                        children="Codes over time for a single subject",
                        style={"textAlign": "center"},
                    ),
                    subject_input,
                    dcc.Dropdown(
                        id="task-dropdown",
                        placeholder="Select a task",
                    ),
                    html.Button(
                        "Confirm",
                        id="confirm-button",
                        n_clicks=0,
                        style={
                            "display": "block",
                            "margin": "20px auto",
                            "fontSize": "20px",
                        },
                    ),
                    html.Div(
                        id="feedback", style={"color": "red", "marginTop": "10px"}
                    ),
                    dcc.Loading(
                        id="loading-fig-subject-codes",
                        type="default",
                        children=dcc.Graph(
                            id="fig_subject_codes",
                            style={"width": "90hh", "height": "90vh"},
                        ),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-5":
            return html.Div(
                [
                    html.H2(
                        children="Numerical distribution for a single code",
                        style={"textAlign": "center"},
                    ),
                    dcc.Dropdown(
                        id="code-dropdown",
                        options=[
                            {"label": code, "value": code} for code in numerical_codes
                        ],
                        placeholder="Select a code",
                    ),
                    html.P(children="Select the histogram normalization:"),
                    dcc.Dropdown(
                        id="histnorm-dropdown-code",
                        options=[
                            {"label": "None", "value": ""},
                            {"label": "Probability", "value": "probability"},
                            {
                                "label": "Probability Density",
                                "value": "probability density",
                            },
                            {"label": "Density", "value": "density"},
                            {"label": "Percent", "value": "percent"},
                        ],
                        value="",
                        placeholder="Select histogram normalization",
                    ),
                    html.P(children="Adjust the number of bins:"),
                    dcc.Slider(
                        id="num-bins-slider",
                        min=10,
                        max=100,
                        step=5,
                        value=10,
                        marks={i: str(i) for i in range(10, 101, 10)},
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                    dcc.Loading(
                        id="loading-fig-code-distribution",
                        type="default",
                        children=dcc.Graph(
                            id="fig_code_distribution",
                            style={"width": "90hh", "height": "50vh"},
                        ),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-6":
            return html.Div(
                [
                    html.H2(children="Code Search", style={"textAlign": "center"}),
                    dcc.Input(
                        id="search-term",
                        type="text",
                        placeholder="Enter code or description",
                        n_submit=0,
                    ),
                    dcc.Dropdown(
                        id="search-options",
                        options=[
                            {"label": "Code", "value": "code"},
                            {"label": "Description", "value": "description"},
                            {"label": "Parent Codes", "value": "parent_codes"},
                        ],
                        value=["code", "description", "parent_codes"],
                        multi=True,
                        placeholder="Select search fields",
                    ),
                    html.Button(
                        "Search",
                        id="search-button",
                        style={
                            "display": "block",
                            "margin": "20px auto",
                            "fontSize": "20px",
                        },
                    ),
                    dcc.Loading(
                        id="loading-search-results",
                        type="default",
                        children=html.Div(id="search-results"),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-7":
            return html.Div(
                [
                    html.H2(
                        children="Coding Dictionary Overview",
                        style={"textAlign": "center"},
                    ),
                    html.P(children="Select the scale:"),
                    dcc.Dropdown(
                        id="scale-dropdown",
                        options=[
                            {"label": "Linear", "value": "linear"},
                            {"label": "Log", "value": "log"},
                        ],
                        value="linear",
                        placeholder="Select scale",
                    ),
                    dcc.Loading(
                        id="loading-fig-coding-dict",
                        type="default",
                        children=dcc.Graph(
                            id="fig_coding_dict",
                            style={"width": "90hh", "height": "90vh"},
                        ),
                    ),
                ],
                style=card_style,
            )

    # Add this callback
    @app.callback(
        Output("general-stats", "children"), Input("hidden-file-path", "value")
    )
    def update_general_stats(file_path):
        if file_path:
            general_statistics = cached_results["general_statistics"]
            metadata = get_metadata(file_path)

            # Convert Polars DataFrame to Pandas DataFrame
            general_statistics_df = general_statistics.to_pandas()

            # Apply formatting only to numerical columns
            general_statistics_df[
                general_statistics_df.select_dtypes(include=["number"]).columns
            ] = general_statistics_df.select_dtypes(include=["number"]).map(
                lambda x: f"{x:,}"
            )

            # Ensure all values are of type string, number, or boolean
            general_statistics_df = general_statistics_df.astype(str)

            stats_data = general_statistics_df.to_dict(orient="records")
            stats_columns = [
                {"name": i, "id": i} for i in general_statistics_df.columns
            ]

            metadata_df = metadata.to_pandas()
            metadata_data = metadata_df.to_dict(orient="records")
            metadata_columns = [{"name": i, "id": i} for i in metadata_df.columns]

            stats_table = dash_table.DataTable(
                columns=stats_columns,
                data=stats_data,
                style_table={"width": "100%", "marginBottom": "20px"},
                style_cell={
                    "textAlign": "left",
                    "whiteSpace": "normal",
                    "overflow": "hidden",
                },
            )

            metadata_table = dash_table.DataTable(
                columns=metadata_columns,
                data=metadata_data,
                style_table={"width": "100%", "marginBottom": "20px"},
                style_cell={
                    "textAlign": "left",
                    "whiteSpace": "normal",
                    "overflow": "hidden",
                },
            )

            card = html.Div(
                [
                    html.H2("Dataset overview", style={"textAlign": "center"}),
                    html.Div(
                        metadata_table,
                        style={"display": "block", "marginBottom": "20px"},
                    ),
                    html.Div(
                        stats_table, style={"display": "block", "marginBottom": "20px"}
                    ),
                ],
                style=card_style,
            )

            return html.Div(
                card, style={"fontFamily": "Helvetica", "marginBottom": "20px"}
            )
        return "No folder selected. Please enter a valid folder path to proceed."

    @app.callback(
        Output("fig_code_count_years", "figure"),
        Input("bins-slider-years", "value"),
        Input("histnorm-dropdown-years", "value"),
    )
    def update_code_count_years(bins, histnorm):
        fig_code_count_years = px.histogram(
            code_count_years,
            x="Date",
            y="Amount of codes",
            nbins=bins,
            histnorm=histnorm,
            # title="Code count over the years"
        )
        return fig_code_count_years

    @app.callback(
        Output("fig_code_count_subject", "figure"),
        Input("bins-slider", "value"),
        Input("histnorm-dropdown", "value"),
    )
    def update_code_count_subject(bins, histnorm):
        fig_code_count_subject = px.histogram(
            code_count_subject,
            y="Subject ID",
            x="Code count",
            histfunc="count",
            histnorm=histnorm,
            # title="Code count distribution per subject",
            nbins=bins,
        ).update_layout(yaxis_title="Segment of Subjects")
        return fig_code_count_subject

    @app.callback(
        Output("search-results", "children"),
        Input("search-button", "n_clicks"),
        Input("search-term", "n_submit"),
        State("search-term", "value"),
        State("search-options", "value"),
        State("hidden-file-path", "value"),
    )
    def update_search_results(
        n_clicks, n_submit, search_term, search_options, file_path
    ):
        if (n_clicks is None and n_submit == 0) or not search_term:
            return "Enter a search term to find codes."

        code_metadata = load_code_metadata(file_path + "/metadata/codes.parquet")
        results = search_codes(code_metadata, search_term, search_options)
        if len(results) == 0:
            return "No results found."

        return [
            html.Tbody(
                [
                    (
                        f"Found {len(results)} results"
                        if len(results) < cfg.limits.search_results
                        else f"Showing first {cfg.limits.search_results} results found. Please refine search"
                    )
                ]
            ),
            html.Table(
                [
                    html.Thead(html.Tr([html.Th(col) for col in results.columns])),
                    html.Tbody(
                        [
                            html.Tr(
                                [
                                    html.Td(results[col].to_list()[i])
                                    for col in results.columns
                                ]
                            )
                            for i in range(len(results))
                        ]
                    ),
                ]
            ),
        ]

    @app.callback(
        Output("fig_top_codes", "figure"),
        Input("top-n-dropdown", "value"),
        Input("scale-dropdown-top-codes", "value"),
    )
    def update_top_codes(top_n, scale):
        top_codes_vis = top_codes.limit(top_n)
        fig_top_codes = px.bar(
            top_codes_vis,
            x="count",
            y="code",
            orientation="h",
            title=f"Top {top_n} most frequent codes",
            color="code",
            log_x=True if scale == "log" else False,
        )
        return fig_top_codes

    import plotly.graph_objects as go

    @app.callback(
        Output("fig_subject_codes", "figure"),
        Output("task-dropdown", "options"),
        Output("feedback", "children"),
        Input("confirm-button", "n_clicks"),
        State("subject-input", "value"),
        State("hidden-file-path", "value"),
        State("task-dropdown", "value"),
    )
    def update_subject_codes_and_task_dropdown(
        n_clicks, subject_id, file_path, selected_task
    ):
        if file_path:
            tasks_path = os.path.join(file_path, "tasks")
            if os.path.isdir(tasks_path):
                detected_tasks = [
                    f
                    for f in os.listdir(tasks_path)
                    if os.path.isfile(os.path.join(tasks_path, f))
                    or os.path.isdir(os.path.join(tasks_path, f))
                ]
                task_options = [
                    {"label": os.path.splitext(task)[0], "value": task}
                    for task in detected_tasks
                ]
            else:
                task_options = []
        else:
            task_options = []

        if n_clicks == 0:
            return go.Figure(), task_options, ""

        if subject_id is None:
            return go.Figure(), task_options, ""

        subject_data = (
            pl.scan_parquet(return_data_path(file_path))
            .filter(pl.col("subject_id") == subject_id)
            .select(
                pl.col("time"),
                pl.col("code"),
                pl.col("numeric_value"),
                pl.col("text_value"),
            )
            .with_columns(
                pl.col("code").str.split("/").list.first().alias("coding_dict")
            )
            .collect()
        )

        if subject_data.is_empty():
            return go.Figure(), task_options, "Subject ID not found."

        fig_subject_codes = px.scatter(
            subject_data,
            x="time",
            y="code",
            color="coding_dict",
            title=f"Codes over time for subject {subject_id}",
            labels={"coding_dict": "Code Category"},
            hover_data={"code": True, "numeric_value": True, "text_value": True},
        )

        if selected_task:
            task_file_path = os.path.join(file_path, "tasks", selected_task)
            if os.path.isfile(task_file_path) or os.path.isdir(task_file_path):
                task_data = pl.scan_parquet(task_file_path)
                task_label = task_data.filter(
                    pl.col("subject_id") == subject_id
                ).collect()
                if not task_label.is_empty():
                    for row in task_label.iter_rows(named=True):
                        prediction_time_timestamp = (
                            row["prediction_time"].timestamp() * 1000
                        )
                        task_name = os.path.splitext(selected_task)[0]
                        color = "red" if row.get("boolean_value", False) else "green"

                        hover_text = f"Task: {task_name}<br>Prediction Time: {row['prediction_time']}"
                        if "boolean_value" in row and row["boolean_value"] is not None:
                            hover_text += f"<br>Boolean Value: {row['boolean_value']}"
                        if "integer_value" in row and row["integer_value"] is not None:
                            hover_text += f"<br>Integer Value: {row['integer_value']}"
                        if "float_value" in row and row["float_value"] is not None:
                            hover_text += f"<br>Float Value: {row['float_value']}"
                        if (
                            "categorical_value" in row
                            and row["categorical_value"] is not None
                        ):
                            hover_text += (
                                f"<br>Categorical Value: {row['categorical_value']}"
                            )

                        fig_subject_codes.add_scatter(
                            x=[prediction_time_timestamp, prediction_time_timestamp],
                            y=[0, 1],
                            mode="lines",
                            line=dict(color=color, dash="dash"),
                            customdata=pd.Series(data=row),
                            hovertemplate=hover_text,
                            name=task_name + f" {row['prediction_time']}",
                            yaxis="y2",
                        )
                        fig_subject_codes.update_layout(
                            yaxis2=dict(showticklabels=False)
                        )

        return fig_subject_codes, task_options, ""

    @app.callback(
        Output("fig_code_distribution", "figure"),
        Input("code-dropdown", "value"),
        Input("num-bins-slider", "value"),
        Input("histnorm-dropdown-code", "value"),
    )
    def update_code_distribution(code, num_bins, histnorm):
        if code is None:
            return {}
        code_data = numerical_code_data.filter(pl.col("code") == code).collect()
        # Calculate IQR and boundaries
        q1 = code_data["numeric_value"].quantile(0.25)
        q3 = code_data["numeric_value"].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Calculate the number of bins using the Freedman-Diaconis rule
        # bin_width = 2 * iqr / np.cbrt(len(code_data))

        fig_code_distribution = px.histogram(
            code_data,
            x="numeric_value",
            title=f"Numerical distribution for code {code}",
            range_x=[lower_bound, upper_bound],
            nbins=num_bins,
            histnorm=histnorm,
        )
        return fig_code_distribution

    @app.callback(
        Output("fig_coding_dict", "figure"),
        Input("scale-dropdown", "value"),
    )
    def update_coding_dict(scale):
        fig_coding_dict = px.bar(
            coding_dict.limit(cfg.limits.coding_dict),
            x="coding_dict",
            y="count",
            title="Coding Dictionary Overview",
            color="coding_dict",
            log_y=True if scale == "log" else False,
        )
        return fig_coding_dict

    app.run(debug=cfg.debug, port=cfg.port)

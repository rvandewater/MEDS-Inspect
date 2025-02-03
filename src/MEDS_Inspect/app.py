import importlib.resources as pkg_resources

import plotly.express as px
import polars as pl
from dash import Dash, Input, Output, State, dash_table, dcc, html

from .cache.cache_results import cache_results, get_metadata
from .code_search import load_code_metadata, search_codes
from .utils import is_valid_path, return_data_path

# Set the ROOT_OUTPUT_DIR
package_name = "MEDS_Inspect"
sample_data_path = f"{pkg_resources.files(package_name)}/assets/MIMIC-IV-DEMO-MEDS"
top_codes = None
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "MEDS INSPECT"
server = app.server
cached_results = None
metadata = None
card_style = {"border": "2px solid #007BFF", "padding": "10px", "borderRadius": "5px"}


def run_app(initial_path=None, port=8050):
    global top_codes
    global cached_results
    global metadata
    # Set the file_path to the downloaded directory
    file_path = initial_path if initial_path else sample_data_path

    # Global variable to store cached results
    cached_results = None

    # file_path=None

    # if file_path and is_valid_path(file_path):
    metadata = get_metadata(file_path)
    cached_results = cache_results(file_path)
    code_count_years = cached_results["code_count_years"]
    code_count_subject = cached_results["code_count_subjects"]
    top_codes = cached_results["top_codes"]
    coding_dict = cached_results["coding_dict"]
    numerical_code_data = cached_results["numerical_code_data"]
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
                id="path-feedback", style={"marginTop": "10px", "color": "green", "textAlign": "center"}
            ),
            html.Div(
                [
                    dcc.Input(
                        id="input-path",
                        type="text",
                        placeholder="Enter folder path",
                        style={"width": "80%", "margin": "0 auto", "display": "block", "fontSize": "20px"},
                    ),
                    html.Button(
                        "Inspect 🔎",
                        id="submit-path",
                        n_clicks=0,
                        style={"display": "block", "margin": "20px auto", "fontSize": "20px"},
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
                    dcc.Tab(label="👤 Per Patient Codes", value="tab-2"),
                    dcc.Tab(label="🏆 Top Codes", value="tab-3"),
                    dcc.Tab(label="🕒 Patient Timeline", value="tab-4"),
                    dcc.Tab(label="📊 Code Distribution", value="tab-5"),
                    dcc.Tab(label="🔍 Code Search", value="tab-6"),
                    dcc.Tab(label="📖 Coding Dictionary", value="tab-7"),
                ],
            ),
            dcc.Loading(id="loading-tabs-content", type="default", children=html.Div(id="tabs-content")),
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
        Output("tabs-content", "children"), Input("tabs", "value"), State("hidden-file-path", "value")
    )
    def render_content(tab, file_path):
        if not file_path:
            return html.Div("No folder selected. Please enter a valid folder path to proceed.")

        # Get unique patient IDs and codes
        subject_ids = code_count_subject["Subject ID"].unique().to_list()
        # codes = top_codes['code'].unique().to_list()

        numerical_codes = numerical_code_data.select("code").unique().collect()["code"].to_list()
        if tab == "tab-1":
            fig_code_count_years = px.histogram(
                code_count_years, x="Date", y="Amount of codes", nbins=len(code_count_years)
            )
            return html.Div(
                [
                    html.H2(children="Code count over time", style={"textAlign": "center"}),
                    html.P(children="Adjust the number of bins:"),
                    dcc.Slider(
                        id="bins-slider-years",
                        min=1,
                        max=len(code_count_years + 1),
                        step=1,
                        value=len(code_count_years),
                        marks={
                            i: str(i)
                            for i in range(1, len(code_count_years) + 1, max(1, len(code_count_years) // 10))
                        },
                        tooltip={"placement": "bottom", "always_visible": True},
                    ),
                    html.P(children="Select the histogram normalization:"),
                    dcc.Dropdown(
                        id="histnorm-dropdown-years",
                        options=[
                            {"label": "None", "value": ""},
                            {"label": "Probability", "value": "probability"},
                            {"label": "Probability Density", "value": "probability density"},
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
                title="Code count distribution per patient",
            ).update_layout(yaxis_title="Segment of Subjects")
            return html.Div(
                [
                    html.H2(children="Code count per patient", style={"textAlign": "center"}),
                    html.P(children="Select the histogram normalization:"),
                    dcc.Dropdown(
                        id="histnorm-dropdown",
                        options=[
                            {"label": "None", "value": ""},
                            {"label": "Probability", "value": "probability"},
                            {"label": "Probability Density", "value": "probability density"},
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
                    html.H2(children="Top most frequent codes", style={"textAlign": "center"}),
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
                        children=dcc.Graph(id="fig_top_codes", style={"width": "90hh", "height": "90vh"}),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-4":
            return html.Div(
                [
                    html.H2(children="Codes over time for a single patient", style={"textAlign": "center"}),
                    dcc.Dropdown(
                        id="patient-dropdown",
                        options=[{"label": pid, "value": pid} for pid in subject_ids],
                        placeholder="Select a patient ID",
                    ),
                    dcc.Loading(
                        id="loading-fig-patient-codes",
                        type="default",
                        children=dcc.Graph(id="fig_patient_codes", style={"width": "90hh", "height": "50vh"}),
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-5":
            return html.Div(
                [
                    html.H2(
                        children="Numerical distribution for a single code", style={"textAlign": "center"}
                    ),
                    dcc.Dropdown(
                        id="code-dropdown",
                        options=[{"label": code, "value": code} for code in numerical_codes],
                        placeholder="Select a code",
                    ),
                    html.P(children="Select the histogram normalization:"),
                    dcc.Dropdown(
                        id="histnorm-dropdown-code",
                        options=[
                            {"label": "None", "value": ""},
                            {"label": "Probability", "value": "probability"},
                            {"label": "Probability Density", "value": "probability density"},
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
                            id="fig_code_distribution", style={"width": "90hh", "height": "50vh"}
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
                        id="search-term", type="text", placeholder="Enter code or description", n_submit=0
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
                        style={"display": "block", "margin": "20px auto", "fontSize": "20px"},
                    ),
                    dcc.Loading(
                        id="loading-search-results", type="default", children=html.Div(id="search-results")
                    ),
                ],
                style=card_style,
            )
        elif tab == "tab-7":
            return html.Div(
                [
                    html.H2(children="Coding Dictionary Overview", style={"textAlign": "center"}),
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
    @app.callback(Output("general-stats", "children"), Input("hidden-file-path", "value"))
    def update_general_stats(file_path):
        if file_path:
            general_statistics = cached_results["general_statistics"]
            metadata = get_metadata(file_path)

            # Convert Polars DataFrame to Pandas DataFrame
            general_statistics_df = general_statistics.to_pandas()

            # Apply formatting only to numerical columns
            general_statistics_df[general_statistics_df.select_dtypes(include=["number"]).columns] = (
                general_statistics_df.select_dtypes(include=["number"]).map(lambda x: f"{x:,}")
            )

            # Ensure all values are of type string, number, or boolean
            general_statistics_df = general_statistics_df.astype(str)

            stats_data = general_statistics_df.to_dict(orient="records")
            stats_columns = [{"name": i, "id": i} for i in general_statistics_df.columns]

            metadata_df = metadata.to_pandas()
            metadata_data = metadata_df.to_dict(orient="records")
            metadata_columns = [{"name": i, "id": i} for i in metadata_df.columns]

            stats_table = dash_table.DataTable(
                columns=stats_columns,
                data=stats_data,
                style_table={"width": "100%", "marginBottom": "20px"},
                style_cell={"textAlign": "left", "whiteSpace": "normal", "overflow": "hidden"},
            )

            metadata_table = dash_table.DataTable(
                columns=metadata_columns,
                data=metadata_data,
                style_table={"width": "100%", "marginBottom": "20px"},
                style_cell={"textAlign": "left", "whiteSpace": "normal", "overflow": "hidden"},
            )

            card = html.Div(
                [
                    html.H2("Dataset overview", style={"textAlign": "center"}),
                    html.Div(metadata_table, style={"display": "block", "marginBottom": "20px"}),
                    html.Div(stats_table, style={"display": "block", "marginBottom": "20px"}),
                ],
                style=card_style,
            )

            return html.Div(card, style={"fontFamily": "Helvetica", "marginBottom": "20px"})
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
            # title="Code count distribution per patient",
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
    def update_search_results(n_clicks, n_submit, search_term, search_options, file_path):
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
                        if len(results) < 1000
                        else "Showing first 1000 results found. Please refine search"
                    )
                ]
            ),
            html.Table(
                [
                    html.Thead(html.Tr([html.Th(col) for col in results.columns])),
                    html.Tbody(
                        [
                            html.Tr([html.Td(results[col].to_list()[i]) for col in results.columns])
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

    @app.callback(Output("fig_patient_codes", "figure"), Input("patient-dropdown", "value"))
    def update_patient_codes(patient_id):
        if patient_id is None:
            return {}

        patient_data = (
            pl.scan_parquet(return_data_path(file_path))
            .filter(pl.col("subject_id") == patient_id)
            .select(pl.col("time"), pl.col("code"))
            .collect()
        )

        if patient_data.is_empty():
            return {}

        fig_patient_codes = px.scatter(
            patient_data, x="time", y="code", title=f"Codes over time for patient {patient_id}"
        )
        return fig_patient_codes

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
            coding_dict.limit(1000),
            x="coding_dict",
            y="count",
            title="Coding Dictionary Overview",
            color="coding_dict",
            log_y=True if scale == "log" else False,
        )
        return fig_coding_dict

    app.run(debug=True, port=port)

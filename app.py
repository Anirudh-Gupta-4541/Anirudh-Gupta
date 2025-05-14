import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# Load data
file_path = "District data.xlsx"
df = pd.read_excel(file_path, sheet_name="Dist Wise Pivot  (2)", header=2)

# Clean column names
df.columns = [str(col).strip() for col in df.columns]
df = df.rename(columns={df.columns[0]: "District"})
df = df[df["District"].notna() & df["District"].str.strip().ne("")]

def safe(val):
    return float(val) if pd.notna(val) else 0.0

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "MP Waste Dashboard"

# Layout
app.layout = html.Div([
    html.H1("Madhya Pradesh District-wise Waste Management Dashboard",
            style={"textAlign": "center", "color": "white"}),

    dcc.Dropdown(
        id="district-dropdown",
        options=[{"label": dist, "value": dist} for dist in df["District"].unique()],
        value=df["District"].iloc[0],
        placeholder="Select a District",
        style={"color": "black"}
    ),

    html.Div(id="kpi-cards", style={
        "display": "flex",
        "justifyContent": "space-around",
        "margin": "20px 0"
    }),

    dcc.Graph(id="population-forecast"),
    html.Div(id="waste-bar-comparison", style={"display": "flex", "justifyContent": "space-between"}),
    html.Div(id="pie-comparison", style={"display": "flex", "justifyContent": "space-between"})

], style={"backgroundColor": "#1e1e1e", "padding": "20px", "fontFamily": "Arial"})


@app.callback(
    [Output("kpi-cards", "children"),
     Output("population-forecast", "figure"),
     Output("waste-bar-comparison", "children"),
     Output("pie-comparison", "children")],
    [Input("district-dropdown", "value")]
)
def update_dashboard(selected_district):
    try:
        row = df[df["District"] == selected_district].iloc[0]

        # KPI Cards
        census_pop = safe(row["Sum of Census 2011 Population"])
        sw_gen = safe(row["Sum of SW_Generation (TPD)"])
        sw_proc = safe(row["Sum of SW_Processed_ (TPD)"])
        sw_gap = safe(row["Sum of SW Collection Gap (in TPD)"])

        processed_percent = (sw_proc / sw_gen * 100) if sw_gen > 0 else 0

        kpis = [
            f"{int(census_pop):,}",
            f"{sw_gen:.2f} TPD",
            f"{processed_percent:.1f}%",
            f"{sw_gap:.2f} TPD"
        ]
        titles = ["Census 2011 Pop", "SW Generated", "% Waste Processed", "Gap in Collection"]

        cards = [html.Div([
            html.H4(title),
            html.P(value)
        ], style={
            "padding": "10px",
            "border": "1px solid #444",
            "borderRadius": "10px",
            "width": "18%",
            "backgroundColor": "#2c2c2c",
            "color": "white",
            "textAlign": "center"
        }) for title, value in zip(titles, kpis)]

        # Population Forecast
        trend_fig = go.Figure()
        trend_fig.add_trace(go.Scatter(
            x=["2011", "2025", "2030"],
            y=[safe(row['Sum of Census 2011 Population']),
               safe(row['Sum of Projected Population by 2025']),
               safe(row['Sum of Projected Population by 2030'])],
            mode='lines+markers',
            name="Population",
            line=dict(color="blue", width=3),
            marker=dict(color="red", size=10)
        ))
        trend_fig.update_layout(
            title="Population Forecast",
            yaxis_title="Population",
            plot_bgcolor="#1e1e1e",
            paper_bgcolor="#1e1e1e",
            font_color="white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#333", nticks=8)  # 🔧 more ticks
        )

        # Extract values for bar comparison
        curr_gen = safe(row["Sum of SW_Generation (TPD)"])
        curr_proc = safe(row["Sum of SW_Processed_ (TPD)"])
        curr_gap = safe(row["Sum of SW Collection Gap (in TPD)"])

        fut_gen = safe(row["Sum of SW_Generation (TPD)-2030"])
        fut_proc = safe(row["Sum of SW_Processed_ (TPD)-2030"])
        fut_gap = safe(row["Sum of SW Collection Gap (in TPD)-2030"])

        y_max = max(curr_gen, curr_proc, curr_gap, fut_gen, fut_proc, fut_gap) * 1.1

        # Current Waste Bar Chart
        current_fig = go.Figure()
        current_fig.add_trace(go.Bar(name="Generated", x=["Current"], y=[curr_gen], marker_color="blue"))
        current_fig.add_trace(go.Bar(name="Processed", x=["Current"], y=[curr_proc], marker_color="green"))
        current_fig.add_trace(go.Bar(name="Gap", x=["Current"], y=[curr_gap], marker_color="red"))
        current_fig.update_layout(title="Current Waste Metrics (TPD)",
                                  barmode='group',
                                  yaxis=dict(range=[0, y_max]),
                                  plot_bgcolor="#1e1e1e",
                                  paper_bgcolor="#1e1e1e",
                                  font_color="white")

        # Future Waste Bar Chart
        future_fig = go.Figure()
        future_fig.add_trace(go.Bar(name="Generated", x=["2030"], y=[fut_gen], marker_color="blue"))
        future_fig.add_trace(go.Bar(name="Processed", x=["2030"], y=[fut_proc], marker_color="green"))
        future_fig.add_trace(go.Bar(name="Gap", x=["2030"], y=[fut_gap], marker_color="red"))
        future_fig.update_layout(title="2030 Waste Metrics (TPD)",
                                 barmode='group',
                                 yaxis=dict(range=[0, y_max]),
                                 plot_bgcolor="#1e1e1e",
                                 paper_bgcolor="#1e1e1e",
                                 font_color="white")

        bar_row = [
            dcc.Graph(figure=current_fig, style={"width": "48%"}),
            dcc.Graph(figure=future_fig, style={"width": "48%"})
        ]

        # Pie charts with consistent colors
        current_pie = px.pie(
            names=["Processed", "Gap"],
            values=[curr_proc, curr_gap],
            hole=0.3,
            color_discrete_map={"Processed": "green", "Gap": "red"}
        )
        current_pie.update_traces(textinfo='percent+label',
                                  hovertemplate='%{label}: %{value:.2f} TPD')
        current_pie.update_layout(title="Current Waste Processed vs Gap",
                                  plot_bgcolor="#1e1e1e",
                                  paper_bgcolor="#1e1e1e",
                                  font_color="white")

        future_pie = px.pie(
            names=["Processed", "Gap"],
            values=[fut_proc, fut_gap],
            hole=0.3,
            color_discrete_map={"Processed": "green", "Gap": "red"}
        )
        future_pie.update_traces(textinfo='percent+label',
                                 hovertemplate='%{label}: %{value:.2f} TPD')
        future_pie.update_layout(title="2030 Waste Processed vs Gap",
                                 plot_bgcolor="#1e1e1e",
                                 paper_bgcolor="#1e1e1e",
                                 font_color="white")

        pie_row = [
            dcc.Graph(figure=current_pie, style={"width": "48%"}),
            dcc.Graph(figure=future_pie, style={"width": "48%"})
        ]

        return cards, trend_fig, bar_row, pie_row

    except Exception as e:
        print("⚠️ Callback error:", e)
        return [html.Div("Error loading data")], go.Figure(), [], []


# Run server
if __name__ == "__main__":
    app.run(debug=True)

import os

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)


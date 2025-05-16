import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output

# === Load GeoJSON ===
try:
    with open("MP Districts Website Map final.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
except Exception as e:
    raise FileNotFoundError(f"Error loading GeoJSON file: {e}")

districts_geo = geojson_data
district_names = [f["properties"]["Dist_Name"] for f in geojson_data["features"]]

# === Load Excel Data ===
try:
    df = pd.read_excel("District data.xlsx", sheet_name="Dist Wise Pivot  (2)", header=2)
except Exception as e:
    raise FileNotFoundError(f"Error loading Excel file: {e}")

df.columns = [str(col).strip() for col in df.columns]
df = df.rename(columns={df.columns[0]: "District"})
df = df[df["District"].notna() & df["District"].str.strip().ne("")]

def safe(val):
    return float(val) if pd.notna(val) else 0.0

# === Helper for empty figures ===
def empty_figure(title):
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "x": 0.5, "font": {"size": 20, "color": "white", "family": "Arial"}},
        plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e", font_color="white",
        xaxis={"visible": False}, yaxis={"visible": False},
        margin={"r":0, "t":40, "l":0, "b":0}
    )
    return fig

# === Create Dash App ===
app = Dash(__name__)
app.title = "MP Waste Dashboard"

# Create choropleth map with color by waste generated
map_fig = px.choropleth_map(
    df,
    geojson=districts_geo,
    locations="District",
    featureidkey="properties.Dist_Name",
    color="Sum of SW_Generation (TPD)",  # Color by waste generated
    color_continuous_scale="bluered",
    map_style="carto-positron",
    range_color = (0, 1500),
    center={"lat": 24, "lon": 78.5},
    zoom=6,
    opacity=0.7
)
map_fig.update_traces(
    marker_line_width=1,
    marker_line_color="black",
    hovertemplate="%{location}<br>Waste Generated: %{z:.2f} TPD<extra></extra>"
)
map_fig.update_layout(
    margin={"r":0, "t":0, "l":0, "b":0},
    clickmode="event+select",
    dragmode=False,
    uirevision=True,
    coloraxis_colorbar=dict(title="Waste Generated (TPD)"),
    paper_bgcolor="#ffffff",
)

app.layout = html.Div([
    html.H2("Madhya Pradesh District Waste Dashboard", style={"textAlign": "center", "color": "white", "fontSize": "28px", "fontWeight": "bold"}),
    html.Div([
        dcc.Graph(
            id="district-map",
            figure=map_fig,
            config={"scrollZoom": False, "displayModeBar": False},
            style={"height": "700px", "width": "100%"}
        )
    ], style={"overflow": "hidden", "marginTop": "40px"}),

    html.Div(id="kpi-cards", style={"display": "flex", "justifyContent": "space-around", "margin": "20px 0", "flexWrap": "wrap"}),
    dcc.Graph(id="population-forecast"),
    html.Div(id="current-bar-pie", style={"display": "flex", "justifyContent": "space-between", "flexWrap": "wrap"}),
    html.Div([dcc.Graph(id="waste-comp-pie")])
], style={"backgroundColor": "#1e1e1e", "padding": "20px", "fontFamily": "Arial"})

@app.callback(
    [Output("kpi-cards", "children"),
     Output("population-forecast", "figure"),
     Output("current-bar-pie", "children"),
     Output("waste-comp-pie", "figure")],
    Input("district-map", "clickData")
)
def update_dashboard(clickData):
    if not clickData or "points" not in clickData:
        return [html.Div("Click a district on the map", style={"color": "white", "flex": "1", "textAlign": "center"})], \
               empty_figure("Population Forecast"), [], empty_figure("Waste Composition")

    district_name = clickData["points"][0]["location"]
    match_row = df[df["District"].str.lower().str.strip() == district_name.lower().strip()]

    if match_row.empty:
        return [html.Div("No data for selected district", style={"color": "white", "flex": "1", "textAlign": "center"})], \
               empty_figure("Population Forecast"), [], empty_figure("Waste Composition")

    row = match_row.iloc[0]

    census_pop = safe(row.get("Sum of Census 2011 Population", 0))
    sw_gen = safe(row.get("Sum of SW_Generation (TPD)", 0))
    sw_proc = safe(row.get("Sum of SW_Processed_ (TPD)", 0))
    sw_gap = safe(row.get("Sum of SW Collection Gap (in TPD)", 0))
    processed_percent = (sw_proc / sw_gen * 100) if sw_gen > 0 else 0
    sewage_gen = safe(row.get("Sum of Sewage Generation (in MLD)", 0))
    growth_rate = safe(row.get("Average of Decadal Grouth Rate in % (During 2001-2011)"))

    kpis = [
        ("Census 2011 Pop", f"{int(census_pop):,}"),
        ("SW Generated", f"{sw_gen:.2f} TPD"),
        ("% Waste Processed", f"{processed_percent:.1f}%"),
        ("Sewage Gen (MLD)", f"{sewage_gen:.2f}"),
        ("Decadal Growth Rate", f"{growth_rate*100:.2f}%")
    ]
    cards = [html.Div([html.H4(title), html.P(value)], style={
        "padding": "10px", "border": "1px solid #444", "borderRadius": "10px",
        "flex": "1 1 18%", "backgroundColor": "#2c2c2c", "color": "white", "textAlign": "center", "margin": "0 5px"
    }) for title, value in kpis]

    pop_forecast = go.Figure()
    pop_forecast.add_trace(go.Scatter(
        x=["2011", "2025", "2030"],
        y=[
            round(census_pop, 3),
            round(safe(row.get("Sum of Projected Population by 2025", 0)), 2),
            round(safe(row.get("Sum of Projected Population by 2030", 0)), 2)
        ],
        mode='lines+markers',
        line=dict(color="red", width=3),
        marker=dict(color="blue", size=15)
    ))
    pop_forecast.update_layout(
        title={"text": "Population Forecast", "x": 0.5, "font": {"size": 30, "color": "white", "family": "Arial"}},
        yaxis_title="Population",
        xaxis=dict(showgrid=False),  # Hides vertical gridlines
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font_color="white"
    )

    bar_fig = go.Figure()
    bar_fig.add_trace(go.Bar(name=f"Generated: {sw_gen:.2f} TPD", x=["Generated"], y=[round(sw_gen, 2)], marker_color="blue"))
    bar_fig.add_trace(go.Bar(name=f"Processed: {sw_proc:.2f} TPD", x=["Processed"], y=[round(sw_proc, 2)], marker_color="green"))
    bar_fig.add_trace(go.Bar(name=f"Gap: {sw_gap:.2f} TPD", x=["Gap"], y=[round(sw_gap, 2)], marker_color='red'))
    bar_fig.update_layout(title={"text": "Current Waste Metrics (TPD)", "x": 0.5, "font": {"size": 20, "color": "white", "family": "Arial"}},
                          barmode='group',
                          plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e", font_color="white",
                          margin={"r":0, "t":40, "l":0, "b":0})

    # Pie Chart Patch for >100% Processed
    proc_pie = min(sw_proc, sw_gen)
    gap_pie = max(0, sw_gen - proc_pie)
    proc_label = "Processed (100%)" if sw_proc > sw_gen else "Processed"

    pie_fig = px.pie(
        names=[proc_label, "Gap"],
        values=[proc_pie, gap_pie],
        hole=0.3,
        color_discrete_map={proc_label: "green", "Gap": "red"}
    )
    pie_fig.update_layout(title={"text": "Processed vs Gap (TPD)", "x": 0.5, "font": {"size": 20, "color": "white", "family": "Arial"}},
                          plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e", font_color="white",
                          margin={"r":0, "t":40, "l":0, "b":0})

    pw = safe(row.get("Sum of Estimated PW Generation in TPD", 0))
    cd = safe(row.get("Sum of C&D Waste Generation in TPD - 2025", 0))
    ew = safe(row.get("Sum of e-waste Generation (TPA)", 0)) / 365
    other = max(0, sw_gen - (pw + cd + ew))
    comp_labels = [f"Plastic Waste: {pw:.2f} TPD", f"C&D: {cd:.2f} TPD", f"E-waste: {ew:.2f} TPD", f"Other: {other:.2f} TPD"]
    comp_pie = px.pie(names=comp_labels, values=[pw, cd, ew, other], hole=0.3,
                      color_discrete_sequence=["#2ca02c", "#c7c7c7", "#ff7f0e", "#1f77b4"])
    comp_pie.update_layout(title={"text": "Waste Composition (TPD)", "x": 0.5, "font": {"size": 20, "color": "white", "family": "Arial"}},
                           plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e", font_color="white",
                           margin={"r":0, "t":40, "l":0, "b":0})

    # District Name Card
    district_card = html.Div([
        html.H4("District"),
        html.P(district_name)
    ], style={
        "padding": "10px", "border": "1px solid #444", "borderRadius": "10px",
        "flex": "1 1 18%", "backgroundColor": "#2c2c2c", "color": "white",
        "textAlign": "center", "margin": "0 5px"
    })

    cards.insert(5, district_card)

    return cards, pop_forecast, [dcc.Graph(figure=bar_fig, style={"width": "48%", "marginBottom": "20px"}),
                                 dcc.Graph(figure=pie_fig, style={"width": "48%", "marginBottom": "20px"})], comp_pie

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)

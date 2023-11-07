
import random, json
import dash
from dash import dcc, html, Dash, callback, Output, Input, State
import dashleaflet as dl
import geopandas as gpd
from dash import dash_table
from dash_extensions.javascript import assign

url = 'https://gist.githubusercontent.com/incubated-geek-cc/5da3adbb2a1602abd8cf18d91016d451/raw/acaf26c65998bd5f53d6172dc6616c448584b19c/US_States.geojson'
us_states_gdf = gpd.read_file(url)
us_states_geojson = json.loads(us_states_gdf.to_json())

style_handle = assign("""function (feature, context) {
    const selection = context.props.hideout || {};
    if (feature.id in selection) {
        return {color: '#AA4A44', fillColor: '#AA4A44', weight: 2};
    }
    return {color: '#333', fillColor: '#f5f0e4', weight: 1};
}""")

app = Dash(__name__)

app.layout = html.Div([
    dl.Map([
        dl.TileLayer(url="http://tile.stamen.com/toner-lite/{z}/{x}/{y}.png"),
        dl.GeoJSON(data=us_states_geojson, id="state-layer",
                   options=dict(style=style_handle))],
        style={'width': '100%', 'height': '800px'},
        id="map",
        center=[39.8283, -98.5795],
    ),
    html.Div(id='state-container', children=[]),
    dash_table.DataTable(id='state-table', columns=[{"name": i, "id": i} for i in ["state"]], data=[])
])

app.clientside_callback(
    """
    function(clickedFeature, hideout) {
        if (!clickedFeature) {
            // NB. raise PreventUpdate to prevent ALL outputs updating, 
            // dash.no_update prevents only a single output updating
            throw window.dash_clientside.PreventUpdate;
        }

        const id = clickedFeature.id;
        const selection = hideout || {};

        if (id in selection) {
            delete selection[id];
        }
        else {
            selection[id] = clickedFeature;
        }

        const tableData = Object.values(selection).map(f => ({state: f.properties.NAME}));
        const stateText = `Clicked: ${clickedFeature.properties.NAME}`;

        return [selection, tableData, stateText, null];
    }
    """,
    Output("state-layer", "hideout"),
    Output("state-table", "data"),
    Output("state-container", "children"),
    Output("state-layer", "click_feature"),
    Input("state-layer", "click_feature"),
    State("state-layer", "hideout")
)

if __name__ == '__main__':
    app.run_server(debug=True)
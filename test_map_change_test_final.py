import dash
from dash import dcc, html
import folium
from folium.plugins import MarkerCluster
import pandas as pd
from haversine import haversine, Unit
from geopy import distance
from PIL import Image

def read_airport_data(filename):
    return pd.read_excel(filename)

def read_flight_data(filename):
    return pd.read_excel(filename)

def calculate_nearest_airports(flight_df, airport_df):
    nearest_airports = []
    for _, flight_row in flight_df.iterrows():
        flight_coords = (flight_row['Latitude'], flight_row['Longitude'])
        nearest_airports_flight = []
        for _, airport_row in airport_df.iterrows():
            airport_coords = (airport_row['Latitude'], airport_row['Longitude'])
            distance = haversine(flight_coords, airport_coords, unit=Unit.NAUTICAL_MILES)
            nearest_airports_flight.append((airport_row['Airport'], airport_row['ICAO Code'], distance))
        nearest_airports_flight.sort(key=lambda x: x[2])
        nearest_airports.append(nearest_airports_flight[:3])
    return nearest_airports

def update_flight_df_with_nearest_airports(flight_df, airport_df):
    nearest_airports = calculate_nearest_airports(flight_df, airport_df)
    flight_df['Nearest Airports'] = [",\n".join([f"{i+1}.({x[1]}, {x[2]:.2f}NM)" for i, x in enumerate(airports)]) for airports in nearest_airports]
    return flight_df

def add_markers_to_map(map_obj, df, color, icon, rotate_icons=False):
    for _, row in df.iterrows():
        popup_html = "<table>"
        for col in df.columns:
            popup_html += f"<tr><th>{col}</th><td>{row[col]}</td></tr>"
        popup_html += "</table>"
        
        if icon == 'A':
            folium.CircleMarker(location=[row['Latitude'], row['Longitude']], radius=5, color='skyblue', fill=True, fill_color='skyblue', popup=folium.Popup(popup_html, max_width=250)).add_to(map_obj)
        else:
            # Use custom airplane icon for flight markers
            if rotate_icons:
                img = Image.open('airplane.png')
                direction = row['Direction']
                rotated_img = img.rotate(direction)
                rotated_img.save('rotated_airplane.png')
                airplane_icon = folium.features.CustomIcon('rotated_airplane.png', icon_size=(33, 35))
            else:
                airplane_icon = folium.features.CustomIcon('airplane.png', icon_size=(33, 35))
            
            folium.Marker(location=[row['Latitude'], row['Longitude']],
                          popup=folium.Popup(popup_html, max_width=250),
                          icon=airplane_icon).add_to(map_obj)

def create_dash_app():
    app = dash.Dash(__name__)

    app.layout = html.Div([
        html.Div([
            html.H1("Flight Map Dashboard", style={'margin-bottom': '0'}),
            html.Div([
                html.Div([
                    html.H3("Flight Number", style={'color': 'purple', 'font-weight': 'bold', 'margin-bottom': '0'}),
                    dcc.Input(id='flight-number', type='text', placeholder='Enter Flight Number')
                ]),
                html.Div([
                    html.H3("Airport", style={'color': 'purple', 'font-weight': 'bold', 'margin-bottom': '0'}),
                    dcc.Input(id='airport-name', type='text', placeholder='Enter ICAO Code')
                ]),
                html.Div([
                    html.H3("Radius in NM", style={'color': 'purple', 'font-weight': 'bold', 'margin-bottom': '0'}),
                    dcc.Input(id='circle-radius', type='number', placeholder='Enter Circle Radius')
                ])
            ], style={'display': 'flex', 'flex-direction': 'row'})
        ], style={'margin-bottom': '0'}),
        html.Div(id='output-map'),
        html.Div([
            html.A(
                'Alert Stations',
                href='http://127.0.0.1:8050/',
                target='_blank',
                style={'margin-right': '10px'}
            ),
            html.A(
                'Ground Handling',
                href='http://127.0.0.1:8050/',
                target='_blank',
                style={'margin-right': '10px'}
            ),
            html.A(
                'Maintenance',
                href='http://127.0.0.1:8050/',
                target='_blank'
            ),
            html.A(
                'Crew_Management',
                href='http://127.0.0.1:8050/',
                target='_blank'
            ),
            html.A(
                'Weather',
                href='http://127.0.0.1:8888/',
                target='_blank'
            )
        ],
        style={'position': 'absolute', 'top': 0, 'right': 0}
        )
    ])

    @app.callback(
        dash.dependencies.Output('output-map', 'children'),
        [dash.dependencies.Input('flight-number', 'value'),
         dash.dependencies.Input('airport-name', 'value'),
         dash.dependencies.Input('circle-radius', 'value')]
    )
    def update_map(flight_number, airport_name, circle_radius):
        filtered_m = folium.Map(tiles="cartodb positron", location=[28, 77], zoom_start=3.7)
        flight_df['Flight Number'] = flight_df['Flight Number'].astype(str)
    
        if flight_number:
            filtered_flight_df = flight_df[flight_df['Flight Number'].str.contains(flight_number)]
            if not filtered_flight_df.empty:
                add_markers_to_map(filtered_m, filtered_flight_df, 'red', 'plane', rotate_icons=True)
                # Center map on first filtered flight
                first_filtered_flight = filtered_flight_df.iloc[0]
                filtered_m.location = [first_filtered_flight['Latitude'], first_filtered_flight['Longitude']]
        else:
            add_markers_to_map(filtered_m, flight_df, 'red', 'plane', rotate_icons=True)
    
        if airport_name:
            filtered_airport_df = airport_df[airport_df['ICAO Code'].str.contains(airport_name)]
            if not filtered_airport_df.empty:
                add_markers_to_map(filtered_m, filtered_airport_df, 'blue', 'A')
                # Center map on first filtered airport
                first_filtered_airport = filtered_airport_df.iloc[0]
                filtered_m.location = [first_filtered_airport['Latitude'], first_filtered_airport['Longitude']]
        else:
            add_markers_to_map(filtered_m, airport_df, 'blue', 'A')
    
        if circle_radius and flight_number:
            filtered_flight_df = filtered_flight_df.iloc[0]
            circle_center = (filtered_flight_df['Latitude'], filtered_flight_df['Longitude'])
            radius_meters = circle_radius * 1000  # Convert km to meters
            circle = folium.Circle(location=circle_center, radius=radius_meters).add_to(filtered_m)
    
        return html.Iframe(id='map', srcDoc=filtered_m._repr_html_(), width='100%', height='600')

    return app

if __name__ == '__main__':
    airport_df = read_airport_data("Airport_Map_with_Weather.xlsx")
    flight_df = read_flight_data("flight_data.xlsx")

    flight_df = update_flight_df_with_nearest_airports(flight_df, airport_df)

    app = create_dash_app()

    if app is not None:
        app.run_server(host='172.23.53.163')

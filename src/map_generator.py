class MapGenerator:
    def __init__(self, location=(0, 0), zoom_start=10):
        import folium
        self.map = folium.Map(location=location, zoom_start=zoom_start)

    def create_map(self, data):
        for coord in data:
            folium.Marker(location=coord).add_to(self.map)

    def save_map(self, file_path):
        self.map.save(file_path)
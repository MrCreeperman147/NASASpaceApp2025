def validate_coordinates(coords):
    if not isinstance(coords, tuple) or len(coords) != 2:
        raise ValueError("Coordinates must be a tuple of (latitude, longitude).")
    
    lat, lon = coords
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("Latitude must be between -90 and 90, and longitude must be between -180 and 180.")

def format_coordinates(coords):
    return f"Latitude: {coords[0]}, Longitude: {coords[1]}"
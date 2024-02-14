# Create global setting to save the fallowing
# Will have the fallowing keys and values
# font, fontsize, color, stroke_color, stroke_width
# Create global settings to save the following


settings = {
    "font": "../fonts/bold_font.ttf",
    "fontsize": 100,
    "color": "#FFFF00",
    "stroke_color": "black",
    "stroke_width": 5,
    "subtitles_position": "center,bottom",
}


def get_settings() -> dict:
    """
    Return the global settings  
    The Subtitle settings are:
    font: font path,
    fontsize: font size,
    color: Hexadecimal color,
    stroke_color: color of the stroke,
    stroke_width: Number of pixels of the stroke
    subtitles_position: Position of the subtitles
    """
    # Return the global settings
    return settings

# Update the global settings
def update_settings(new_settings: dict):
    """
    Update the global settings
    
    Args:
        font: font path,
        fontsize: font size,
        color: Hexadecimal color,
        stroke_color: color of the stroke,
        stroke_width: Number of pixels of the stroke
        subtitles_position: Position of the subtitles
    """
    # Update the global settings
    settings.update(new_settings)
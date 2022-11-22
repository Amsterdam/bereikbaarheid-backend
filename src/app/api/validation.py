from marshmallow import ValidationError

# Constants used for validating API parameters
bbox_adam = {
    "lat": {"min": 52.2, "max": 52.47},
    "lon": {"min": 4.7, "max": 5.1},
}

# The vehicle parameters should be in sync with validation requirements
# for client-side forms (defined in javascript)
vehicle = {
    "axleWeight": {"min": 0, "max": 12000},  # in kilograms
    "height": {"min": 0, "max": 4},  # in meters
    "length": {"min": 0, "max": 22},  # in meters
    "maxAllowedWeight": {"min": 0, "max": 60000},  # in kilograms
    "totalWeight": {"min": 0, "max": 60000},  # in kilograms
    # vehicle types are equal to types defined by RDW
    # see https://opendata.rdw.nl/resource/9dze-d57m.json
    "types": ("Bedrijfsauto", "Bus", "Personenauto"),
    "width": {"min": 0, "max": 3},  # in meters
}


def allowed_vehicle_types(vehicle_type):
    """
    Checks allowed vehicle types.
    To be used in a marshmallow Schema
    Lowercase values are also allowed, because when preparing database
    query parameters the vehicle type is checked in the same way
    """
    if not vehicle_type.casefold() in map(str.casefold, vehicle["types"]):
        raise ValidationError("Must be one of: " + ", ".join(vehicle["types"]))

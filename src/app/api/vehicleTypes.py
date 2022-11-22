#
# Helper functions for determining vehicle types
#


def vehicle_is_bus(vehicle_type):
    return vehicle_type.lower() == "bus"


def vehicle_is_company_car(vehicle_type):
    return vehicle_type.lower() == "bedrijfsauto"

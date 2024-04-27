class SNODASError(Exception):
    pass


class GeoJSONValidationError(SNODASError, TypeError):
    pass

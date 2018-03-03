INSTALLED_APPS += (
    'rest_framework',
    'rest_framework_gis',
)

# defined api versions
api_versions = [0.1]

REST_FRAMEWORK = {
    'PAGINATE_BY': 100,
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'DEFAULT_VERSIONING_CLASS':
        'rest_framework.versioning.AcceptHeaderVersioning',
    'ALLOWED_VERSIONS': [str(x) for x in api_versions],
    'DEFAULT_VERSION': str(max(api_versions)),
}

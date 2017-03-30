# Host to bind this server on
HOST = "localhost"
# Port to bind this server on
PORT = 8000
# URI for the API server to which we will connect
API_LOC = "localhost:8080"
# Set to True to enable debug mode, but DO NOT USE in production
DEBUG = False
# List of metadata fields that can be set when submitting a file for scanning
METADATA_FIELDS = [
    "Submitter Name",
    "Submission Description",
    "Submitter Email",
    "Submitter Organization",
    "Submitter Phone",
]
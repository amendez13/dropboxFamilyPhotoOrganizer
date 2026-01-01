"""Constants for OAuth 2.0 authentication."""

# Dropbox access token expiry duration in seconds
# Dropbox OAuth 2.0 access tokens typically expire after 4 hours
DROPBOX_ACCESS_TOKEN_EXPIRY_SECONDS = 14400  # 4 hours = 14400 seconds

# Buffer time before token expiry to trigger refresh (in seconds)
# Tokens are considered expired if they expire within this buffer
TOKEN_EXPIRY_BUFFER_SECONDS = 300  # 5 minutes = 300 seconds

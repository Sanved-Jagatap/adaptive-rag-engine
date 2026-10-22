# Authentication and Session Management

Authentication establishes the identity of a client before protected application resources are accessed. A typical session architecture uses short-lived access tokens together with longer-lived refresh tokens.

## Access Tokens

ACCESS_TOKEN_TTL_SECONDS controls the lifetime of an access token. The default value is 900 seconds, or 15 minutes. Keeping access tokens short-lived limits the useful lifetime of a leaked credential.

Access tokens are presented when clients call protected API endpoints. The authentication layer validates the token before the request is allowed to continue.

A long-lived access token creates a larger exposure window if the credential is copied from a compromised device, logging mistake, or other source.

## Refresh Tokens

REFRESH_TOKEN_TTL_SECONDS controls the lifetime of a refresh token. The default value is 1209600 seconds, or 14 days.

When an access token expires, the client can exchange the refresh token through /auth/refresh without requiring the user to authenticate again. This provides session continuity without requiring the access token itself to remain valid for a long period.

Refresh token rotation can be enabled through REFRESH_TOKEN_ROTATION_ENABLED. When enabled, a new refresh token is issued during refresh and the previous refresh token is invalidated.

## Session Security

Refresh tokens require stronger protection because they remain valid substantially longer than access tokens. Applications should avoid placing either token type in ordinary application logs.

Authentication failures should be recorded through structured security logging without exposing credentials or token values.

Authentication and authorization are separate controls. Authentication establishes who the caller is, while authorization determines whether that identity can perform a particular operation.

## Operational Considerations

Expired access tokens should produce an appropriate authentication response rather than silently allowing access. Refresh operations should also be observable so repeated failures or suspicious activity can be investigated.

Security-sensitive session operations should include correlation identifiers where possible, allowing authentication events to be connected with application requests without recording the secret token itself.

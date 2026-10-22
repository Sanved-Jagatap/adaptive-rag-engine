# Application Security

Application security includes protecting credentials, validating input, controlling access, and limiting the impact of compromised components.

## Authentication and Authorization

Authentication determines whether an identity has been established.

Authorization determines whether that identity is permitted to perform a particular operation.

These controls address different questions and should not be treated as interchangeable.

## Secrets

Secrets such as database passwords, API keys, and token-signing keys should be supplied through secure configuration mechanisms rather than committed directly into source code.

Environment variables can provide configuration, but production environments should use appropriate secret-management controls when available.

## Input Validation

Input validation reduces the risk of malformed or malicious data reaching application logic.

Validation should occur at appropriate system boundaries, including APIs that accept external user input.

Applications should not assume that data is safe simply because it originated from another internal service.

## Least Privilege

Least privilege means that a service or user should receive only the permissions required to perform its intended operations.

Reducing unnecessary permissions limits the potential impact of compromised credentials or application components.

## Security Logging

Security logging should record relevant authentication and authorization events while avoiding sensitive credential values.

Security events should contain enough context to support investigation without logging passwords, access tokens, secret keys, or complete sensitive payloads.

## Session Security

Short-lived access tokens can reduce the useful lifetime of a stolen credential.

Refresh-token mechanisms can maintain user sessions without requiring long-lived access tokens.

Access-token lifetime and refresh-token lifetime therefore represent different security and usability trade-offs.

## Defense in Depth

Security controls should be evaluated together because no single mechanism provides complete protection against every class of failure.

Authentication, authorization, input validation, secret protection, least privilege, and security monitoring provide complementary protections.

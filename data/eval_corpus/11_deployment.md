# Application Deployment

Application deployments move a new version of a service into an environment where it can receive traffic.

## Deployment Validation

A deployment process should verify that the application starts correctly and that required dependencies are reachable.

Automated healthchecks provide a repeatable way to determine whether a service is functioning correctly.

A deployment should also verify configuration values, network connectivity, and dependency availability before directing production traffic to the new version.

## Healthchecks

A liveness check indicates whether a process is running.

A readiness check indicates whether a service can safely receive traffic.

These checks represent different questions. A process can be alive while still being unable to handle requests because a required dependency is unavailable.

## Containers

Containerized services should avoid running as root when elevated privileges are unnecessary.

Running as a non-root user reduces the privileges available if the application process is compromised.

Container healthchecks should test behavior that is meaningful for the service rather than merely checking that a process exists.

## Dependencies

Dependency startup ordering is not always sufficient to guarantee that a dependency is ready.

Services may need healthchecks before accepting requests. A database container being started does not necessarily mean that it is ready to accept application connections.

## Configuration

Environment variables can provide deployment-specific configuration such as service addresses, database credentials, and model names.

Sensitive values should not be committed to source control. Deployment configuration should separate secrets from ordinary application settings where possible.

## Rolling Deployments

Rolling deployments can gradually replace old application instances with new ones, reducing the need for a complete service interruption.

During a rolling deployment, readiness checks help ensure that new instances receive traffic only after they are prepared to serve requests.

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Opt-in blue/green rolling deployments for generated Spring Boot services (#15): `deploy.rolling` manifest block,
  staged `deploy.yml` and a new `promote.yml` workflow, rollout infrastructure for ECS Fargate, Cloud Run and
  EKS/GKE Autopilot, and the `iru-springboot-rolling-deployments` skill to enable or disable it later.

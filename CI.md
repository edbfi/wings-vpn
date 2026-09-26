# Local validation

Repository CI, automated dependency updates and workflow-based deployment are disabled.
Validate changes locally and review dependency updates manually.
Use Conventional Commit titles and matching author sign-offs (`git commit -s`).

Available validation entry points (install the project toolchain first):

```sh
SKIP=no-commit-to-branch prek run --all-files
```

See the project README and package scripts for build and test commands.

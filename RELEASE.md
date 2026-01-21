# Release Process

## 1. Bump versions

```bash
# Edit version in both Cargo.toml files
vim validator/Cargo.toml agent/Cargo.toml

git add validator/Cargo.toml agent/Cargo.toml
git commit -m "Bump version to X.Y.Z"
git push origin main
```

## 2. Tag and push

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

This triggers the [Release workflow](.github/workflows/release.yml) which builds:

| Binary | Description |
|--------|-------------|
| `worldview-validate-darwin-arm64` | macOS ARM validator |
| `worldview-validate-linux-x86_64` | Linux x86 validator |
| `worldview-validate-linux-arm64` | Linux ARM validator |
| `worldview-darwin-arm64` | macOS ARM agent CLI |
| `worldview-linux-x86_64` | Linux x86 agent CLI |
| `worldview-linux-arm64` | Linux ARM agent CLI |

## 3. Verify release

Once the workflow completes, check the [Releases page](../../releases) for the new version with all artifacts attached.

## Version scheme

```
0.1.0-alpha.1   # Early development
0.1.0-rc.1      # Release candidate
0.1.0           # Stable release
```

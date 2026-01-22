# Release Process

## 1. Bump versions

```bash
# Edit version in Cargo.toml files
vim validator/Cargo.toml cli/Cargo.toml

git add validator/Cargo.toml cli/Cargo.toml
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
| `worldview-darwin-arm64` | macOS ARM CLI |
| `worldview-linux-x86_64` | Linux x86 CLI |
| `worldview-linux-arm64` | Linux ARM CLI |

The `worldview` binary includes both validation (`worldview validate`) and agent (`worldview add`) functionality.

## 3. Verify release

Once the workflow completes, check the [Releases page](../../releases) for the new version with all artifacts attached.

## Version scheme

```
0.1.0-alpha.1   # Early development
0.1.0-rc.1      # Release candidate
0.1.0           # Stable release
```

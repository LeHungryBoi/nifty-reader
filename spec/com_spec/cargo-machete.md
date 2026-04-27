# cargo-machete — Unused Dependency Cleaner

`cargo-machete` is a tool for the Rust ecosystem designed to identify and help remove unused dependencies in `Cargo.toml` files.

## Installation
```bash
cargo install cargo-machete
```

## Usage
To automatically fix (remove) the dependencies:
```bash
 cargo machete --with-metadata --fix
```

## Configuration
To ignore specific dependencies, add this to `Cargo.toml`:
```toml
[package.metadata.cargo-machete]
ignored = ["some-crate"]
```

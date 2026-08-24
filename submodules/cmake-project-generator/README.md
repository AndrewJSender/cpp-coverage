# cmake-project-generator

A powerful cross-platform build system generator that automates the creation of Xcode projects and Visual Studio solutions from CMake configurations.

## Overview

`cmake-project-generator` simplifies project setup for C++ developers by automatically generating IDE-specific project files (Xcode on macOS, Visual Studio on Windows) from a single CMake configuration. It eliminates manual project setup and ensures consistency across platforms.

## Features

- **Cross-Platform Support**: Generates projects for Xcode (macOS) and Visual Studio (Windows)
- **Automatic Platform Detection**: Intelligently selects the appropriate generator based on your OS
- **Simple CLI Interface**: Easy-to-use command-line tool for project generation
- **CMake Integration**: Leverages CMake's powerful configuration system
- **Build Directory Management**: Organized build output structure

## Prerequisites

Before using `cmake-project-generator`, ensure you have the following installed:

- **CMake** (version 3.15 or later)
- **Python** (version 3.6 or later)
- **Xcode Command Line Tools** (macOS) or **Visual Studio** (Windows)

### macOS
```bash
# Install CMake (if not already installed)
brew install cmake

# Xcode Command Line Tools should be installed
xcode-select --install
```

### Windows
```powershell
# Install CMake using Chocolatey (if not already installed)
choco install cmake

# Visual Studio 2022 or later is required
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cmake-project-generator
```

2. Ensure all prerequisites are installed and accessible from your command line.

## Usage

### Basic Usage

Run the generator script from your project root:

```bash
python src/generate.py
```

The script will automatically detect your platform and generate the appropriate project files:
- **macOS**: Creates Xcode project in `build_xcode/`
- **Windows**: Creates Visual Studio solution in `build_vs/`

### Specifying a Generator

To explicitly specify a generator:

```bash
# Generate Xcode project
python src/generate.py --generator xcode

# Generate Visual Studio project
python src/generate.py --generator vs
```

### Example Project

An example CMake project is included in the `examples/` directory. To generate a project for the example:

```bash
python src/generate.py
```

This creates build directories containing the IDE-specific project files ready for development.

## Project Structure

```
cmake-project-generator/
├── README.md                 # This file
├── LICENSE                   # Apache License 2.0
├── examples/
│   ├── CMakeLists.txt       # Example CMake configuration
│   └── main.cpp             # Sample C++ source code
└── src/
    └── generate.py          # Project generator script
```

## Supported Generators

| Generator | Platform | Output Directory | IDE |
|-----------|----------|------------------|-----|
| `xcode` | macOS | `build_xcode/` | Xcode |
| `vs` | Windows | `build_vs/` | Visual Studio 2022 |

## Troubleshooting

### CMake not found
Ensure CMake is installed and added to your system PATH. Verify with:
```bash
cmake --version
```

### Platform not supported
If you're on an unsupported platform (Linux, etc.), explicitly specify a generator:
```bash
python src/generate.py --generator <generator-name>
```

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for more details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests to improve this tool.

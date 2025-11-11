# Arduino IDE Modern - Roadmap

This document outlines the development roadmap for Arduino IDE Modern.

## Phase 1: Core Features ✅ (Completed)
- [x] Basic code editor with syntax highlighting
- [x] Serial monitor
- [x] Theme system
- [x] Project explorer
- [x] Board selection

## Phase 2: Advanced Editing ✅ (Completed)
- [x] IntelliSense with clangd integration
- [x] Code snippets library
- [x] Multi-file project support
- [x] Find and replace
- [x] Code folding

## Phase 3: Build System (In Progress)
- [x] Arduino CLI integration
- [ ] Library manager (partially implemented - missing ZIP installation)
- [x] Board manager
- [x] Custom build configurations

### Library Manager Status:
**Implemented:**
- Library index integration with Arduino library registry
- Search and filtering system
- Dependency resolution
- Install/uninstall/update from registry
- Modern UI with detailed library information

**Missing (critical features from Arduino IDE 1.8):**
- ❌ Install library from ZIP file
- ❌ Verification that full library index loads (thousands of libraries)

Note: PlatformIO backend support was not implemented - the IDE follows an Arduino CLI-focused architecture by design.

## Phase 4: Debugging
- [ ] Remote debugging over serial
- [ ] Breakpoint support
- [ ] Variable inspection
- [ ] Memory profiler
- [ ] Execution timeline

## Phase 5: Advanced Features
- [ ] Visual programming mode (block-based)
- [ ] Circuit view with diagrams
- [ ] Git integration
- [ ] Collaborative features
- [ ] Plugin system

## Phase 6: Professional Tools
- [ ] Unit testing framework
- [ ] CI/CD integration
- [ ] Performance profiler
- [ ] Power consumption analyzer
- [ ] Hardware-in-loop testing

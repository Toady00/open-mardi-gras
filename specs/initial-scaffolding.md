# Initial Scaffolding Specification

## Overview

Create the foundational project structure for `open-mardi-gras`, a TypeScript-based OpenCode plugin that provides workflow automation features (starting with command chaining/return functionality). This scaffolding establishes the npm package structure, build system, TypeScript configuration, linting, and open source files required for publishing to the npm registry.

**IMPORTANT**: The `.opencode/` directory contains OpenCode's configuration and helper plugins for development purposes ONLY. It is NOT part of this plugin package and should be completely ignored in the published npm package.

**Goal**: Produce a working npm package that exports OpenCode plugins and can be installed via `npm install open-mardi-gras` or referenced in `opencode.json`.

## Requirements

### 1. Package Configuration

**1.1 Root package.json**
- Package name: `open-mardi-gras`
- Initial version: `0.1.0`
- Description: "OpenCode plugin for workflow automation and command chaining"
- Type: `module` (ES modules)
- Main entry: `./dist/index.js`
- Types entry: `./dist/index.d.ts`
- Files to include: `["dist/", "LICENSE", "README.md", "CHANGELOG.md"]` (explicitly excludes `.opencode/`)
- Scripts needed:
  - `build`: Compile TypeScript to `dist/` (`tsc`)
  - `lint`: Run ESLint (`eslint src/`)
  - `lint:fix`: Fix ESLint issues (`eslint src/ --fix`)
  - `clean`: Remove `dist/` directory (`rm -rf dist/`)
  - `prepublishOnly`: Run `clean` and `build` (clean must run first to avoid stale files)
  - `dev` (optional): Watch mode (`tsc --watch`)
- Engines field:
  - `node`: ">=18.0.0" (supports current LTS)

**1.2 Dependencies**
- `@opencode-ai/plugin`: `^1.2.10` (devDependency only - OpenCode guarantees it's available at runtime)
- `typescript`: `^5.x` (devDependency)
- `@types/node`: `^20.x` (devDependency)
- `eslint`: `^9.x` (devDependency)
- `@typescript-eslint/eslint-plugin`: `^8.x` (devDependency)
- `@typescript-eslint/parser`: `^8.x` (devDependency)

### 2. TypeScript Configuration

**2.1 tsconfig.json**
- Target: ES2022
- Module: NodeNext
- ModuleResolution: NodeNext
- Declaration: true (generate .d.ts files)
- DeclarationMap: true
- SourceMap: true
- Strict: true
- OutDir: `./dist`
- RootDir: `./src`
- SkipLibCheck: true
- EsModuleInterop: true
- Exclude: `[".opencode/"]` (don't compile dev helpers)

### 3. ESLint Configuration

**3.1 eslint.config.js**
- Use ESLint flat config format (eslint.config.js)
- Include `@typescript-eslint/recommended` rules
- Include `@typescript-eslint/recommended-type-checked` rules
- Target files: `src/**/*.ts`
- Ignore: `dist/`, `node_modules/`, `.opencode/`
- Include parserOptions with project reference to tsconfig.json for type-aware linting

### 4. Project Structure

```
open-mardi-gras/
├── package.json           # NPM package configuration
├── tsconfig.json          # TypeScript compiler configuration
├── eslint.config.js       # ESLint configuration
├── LICENSE                # MIT license file
├── CHANGELOG.md           # Changelog following common-changelog format
├── README.md              # Existing - enhance with development info
├── .gitignore             # Add dist/, node_modules/
├── src/
│   ├── index.ts           # Main entry point - exports HelloWorldPlugin
│   └── plugins/
│       └── hello-world.ts # Validation plugin (hello world)
└── dist/                  # Compiled output (gitignored)
```

**Note**: `.opencode/` directory exists at root but is NOT part of the plugin package.

### 5. Source Code Files

**5.1 src/plugins/hello-world.ts**
- Simple "Hello World" OpenCode plugin to validate wiring
- Implements the Plugin type from `@opencode-ai/plugin`
- Logs a message on initialization
- Accepts optional configuration object (even if unused) to support future configuration needs
- Example structure:
  ```typescript
  import type { Plugin } from "@opencode-ai/plugin"
  
  export interface HelloWorldPluginConfig {
    // Reserved for future configuration options
  }
  
  export const HelloWorldPlugin = (config?: HelloWorldPluginConfig): Plugin => {
    return async ({ client }) => {
      await client.app.log({
        body: {
          service: "open-mardi-gras",
          level: "info",
          message: "HelloWorldPlugin initialized",
        },
      })
      
      return {
        // Empty hooks object - this plugin just validates wiring
      }
    }
  }
  ```

**5.2 src/index.ts**
- Main entry point for the plugin package
- Export HelloWorldPlugin from `./plugins/hello-world.js`
- Export HelloWorldPluginConfig type for TypeScript users
- Re-export types from `@opencode-ai/plugin` if needed
- Structure:
  ```typescript
  export { HelloWorldPlugin } from './plugins/hello-world.js'
  export type { HelloWorldPluginConfig } from './plugins/hello-world.js'
  export type * from '@opencode-ai/plugin'
  ```

### 6. Open Source Files

**6.1 LICENSE**
- MIT License
- Include copyright notice: "Copyright (c) 2026 Brandon Dennis"
- Use standard MIT license text

**6.2 CHANGELOG.md**
- Follow [Common Changelog](https://common-changelog.org/) format
- Initial version: 0.1.0
- Sections: "0.1.0 - 2026-02-26" with "Initial release" description
- Include link to full git history for details

**6.3 README.md (Enhancements)**
Add sections:
- Installation (npm install)
- Development setup (bun install, build, lint)
- Plugin usage in opencode.json (both string reference and import with config)
  ```typescript
  // Option 1: String reference (simplest)
  plugins: ['open-mardi-gras']
  
  // Option 2: Import with configuration (for advanced use)
  import { HelloWorldPlugin } from 'open-mardi-gras'
  plugins: [HelloWorldPlugin({ /* options */ })]
  ```
- Contributing (brief)
- License reference
- Changelog reference

### 7. Build System

**7.1 Compilation**
- Use `tsc` for building (no bundler needed for now)
- Output to `dist/` directory
- Include .d.ts files for TypeScript consumers
- Include source maps for debugging
- Must NOT compile `.opencode/` directory

**7.2 Watch Mode**
- `dev` script using `tsc --watch`

### 8. Git Configuration

**8.1 .gitignore additions**
```
# Build output
dist/

# Dependencies
node_modules/

# OS
.DS_Store

# Temporary files
*.tmp
*.swp
```

**8.2 Do NOT add to .gitignore**
- `.opencode/` - this directory IS tracked in git (contains dev helpers)

**8.3 npm publish exclusions**
- Use `files` field in package.json: `["dist/", "LICENSE", "README.md", "CHANGELOG.md"]`
- This explicitly excludes `.opencode/` from npm package

## Acceptance Criteria

- [ ] Running `bun install` installs all dependencies
- [ ] Running `bun run build` compiles TypeScript without errors
- [ ] Running `bun run lint` checks code style without critical errors
- [ ] Running `bun run lint:fix` fixes auto-fixable ESLint issues
- [ ] Running `bun run clean` removes the `dist/` directory
- [ ] Running `bun run dev` starts TypeScript watch mode
- [ ] `dist/` directory contains compiled `.js` and `.d.ts` files
- [ ] `dist/` contains `.js.map` source map files
- [ ] `dist/` contains `.d.ts.map` declaration map files
- [ ] `dist/index.js` is the main entry point
- [ ] `dist/index.d.ts` provides TypeScript definitions
- [ ] `tsconfig.json` is valid (running `tsc --noEmit` succeeds)
- [ ] `eslint.config.js` is valid (running `eslint --print-config src/index.ts` succeeds)
- [ ] LICENSE file exists with standard MIT text and copyright "Brandon Dennis"
- [ ] CHANGELOG.md exists following common-changelog format with date 2026-02-26
- [ ] README includes development instructions
- [ ] README documents both string and import plugin usage patterns
- [ ] Package can be linked locally with `bun link` for testing
- [ ] Running `npm pack` creates a valid tarball without errors
- [ ] Running `npm pack --dry-run` shows only expected files (dist/, LICENSE, README.md, CHANGELOG.md)
- [ ] Running `npm publish --dry-run` succeeds without errors
- [ ] `files` field in package.json correctly limits published files
- [ ] `.opencode/` directory is NOT included in the published npm package
- [ ] `.opencode/` directory IS tracked in git (not gitignored)
- [ ] `git check-ignore dist/` returns dist/ (is ignored)
- [ ] `git check-ignore node_modules/` returns node_modules/ (is ignored)
- [ ] @opencode-ai/plugin is NOT in dependencies or peerDependencies (devDependency only)
- [ ] HelloWorldPlugin can be imported and used in an OpenCode configuration
- [ ] Installing the package via `npm install` and importing it works without errors
- [ ] Plugin accepts optional configuration object (even if unused in v0.1.0)

## Edge Cases

### Bun vs npm Compatibility
- Use `bun` for development (as per OpenCode)
- Ensure package works with standard `npm`/`node` consumers
- Lock file: Use `bun.lock` (Bun's format)
- Windows compatibility: `clean` script uses `rm -rf` (Unix-only); Windows support deferred to future release

### ESM-Only Package
- Do not generate CommonJS output
- Set `"type": "module"` in package.json
- Use `.js` extensions in imports (TypeScript handles this)
- Ensure `"module": "NodeNext"` in tsconfig.json

### Dependency Handling
- `@opencode-ai/plugin` is a devDependency only
- OpenCode guarantees runtime availability
- No peerDependencies complexity needed
- Type checking works during development

### Build Artifacts
- `dist/` is gitignored but included in npm package via `files` field
- Source maps included for debugging
- Declaration maps for IDE go-to-definition

### .opencode/ Directory Handling
- **In Git**: `.opencode/` IS tracked (helpers shared across dev environments)
- **In Build**: TypeScript excludes `.opencode/` from compilation
- **In npm**: `.opencode/` is NOT published (via `files` field in package.json)
- **In ESLint**: Ignored from linting (development helpers, not package code)

### Build Failures
- If TypeScript compilation fails, output must show file/line/column of errors
- Build process should exit with non-zero status code on failure
- `clean` script must complete successfully before `build` runs (order matters in prepublishOnly)

### Stale Build Artifacts
- `clean` script must remove entire `dist/` directory before rebuilding
- Stale files in dist/ must not be included in published package

### npm Package Verification
- `npm pack --dry-run` must show only expected files
- Published package must not include .opencode/, src/, or config files
- Package must be installable via `npm install` without errors

### Runtime Errors
- Plugin must fail gracefully if OpenCode client is unavailable
- Missing @opencode-ai/plugin at runtime should produce clear error message

## Dependencies

This epic has no dependencies. It is the foundational work.

## Child Issues

After this scaffolding is complete, the following child issues will be created:

1. **"Implement Return Plugin"** (separate epic)
   - Depends on: This scaffolding epic
   - Implements the command chaining feature described in README
   - Adds return.ts to src/plugins/
   - Updates index.ts exports

## Next Steps After Scaffolding

1. Verify scaffolding acceptance criteria all pass
2. Close this epic
3. Create child epic: "Implement Return Plugin" (depends on this epic)
4. Test locally with `bun link`
5. Create npm account and publish v0.1.0
6. Update documentation with real npm install instructions

## References

- OpenCode Plugin Documentation: https://opencode.ai/docs/plugins/
- Bun Documentation: https://bun.sh/docs
- TypeScript ESM Guide: https://www.typescriptlang.org/docs/handbook/esm-node.html
- npm Package Publishing: https://docs.npmjs.com/packages-and-modules/contributing-packages-to-the-registry
- npm files field: https://docs.npmjs.com/cli/v10/configuring-npm/package-json#files
- Common Changelog: https://common-changelog.org/

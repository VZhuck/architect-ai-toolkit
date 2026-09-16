# Overview
This repository serves as solution architecture repository, which keeps artifacts required for implementing specific project. 

# Environment Variables

Required environment variables include:
- PROJECT_IDS=007,101
- JIRA 
- ADO_ORGANIZATION_URL
- ADO_CAPABILITY_ID
- ADO_FEATURE_IDS
- ADO_PAT

## Naming Convention for Skills and Commands

New skills and commands are prefixed `aait` (AI Architect Toolkit), so toolkit capabilities are distinguishable from a target repository's own skills once installed.

- Skills: `skills/aait-<name>/` — for example `skills/aait-nfr/`.
- Commands: `commands/aait/<name>.md`, invoked as `/aait:<name>` — for example `/aait:nfr-detect`. Nested command folders are discovered correctly by `ossify-cogents`.

Skills that predate this convention (`load-raw-req`, `md-to-word`, `summarize-meeting-decisions`, `word-to-md`) keep their existing names. The prefix applies going forward only; do not rename them.

## Repository Structure
The repository is structured as follows:

architect-ai-toolkit/
|- .ai-automation/                  # Single source of truth for AI agent customization
|  |- instructions.md               # Top-level instructions (this file)
|  |- ai-platform.psm1              # AiPlatform enum ([Flags] Claude, GhCopilot, All)
|  |- create-links.ps1              # Creates links from .github into .ai-automation
|  |- agents/                       # Agent definitions
|  |- skills/                       # Skill definitions
|  |- instructions/                 # Scoped instruction files
|  |- scripts/                      # PowerShell helpers used by sync workflows
|  |  |- AdoWorkItem.psm1           # Defines class AdoWorkItem
|  |  |- AdoRequirements.psm1       # Defines class AdoRequirements
|  |  |- fetch-ado-workitem.ps1     # Returns a single ADO work item
|  |  |- get-ado-work-items.ps1     # Returns capability + feature work items
|  |  |- read-folder-files.ps1      # Reads folder files into a hashtable
|  |  |- remove-folder-files.ps1    # Cleans target folder
|  |  |- load-env-vars.ps1          # Loads .env variables into process scope
|  |  |- test-ado-prerequisites.ps1 # Validates az/devops/env/login prerequisites
|  |  |- split-markdown-by-heading.py # Splits markdown by heading structure
|  |  |- copy-dir.py                # Copies directory content
|- .env.example                     # Example environment variables for local setup
|- README.md                        # Repository overview and usage
|- LICENSE                          # License file

## Raw Requirements Instructions

Detailed formatting rules for `functional-requirements-raw/` files are defined in `.ai-automation/instructions/functional-requirements-raw.instructions.md`.

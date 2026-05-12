# architect-ai-toolkit
Set of skills and tool for solution architecture

## Installation Guide

### Creating Soft Link Mappings

To set up the repository for your preferred AI platform, run the following PowerShell script from the repository root:

```powershell
# For GitHub Copilot
./create-links.ps1 -AiPlatform "GhCopilot"

# For Claude
./create-links.ps1 -AiPlatform "Claude"

# For both platforms (GitHub Copilot & Claude)
./create-links.ps1 -AiPlatform "All"
```

This will create the necessary symbolic links for agent, skill, and instruction files under the appropriate platform folders (e.g., `.github`, `.claude`).

To force replacement of existing links, add the `-Force` flag:

```powershell
./create-links.ps1 -AiPlatform "GhCopilot" -Force
```

### Creating a Python Environment
Skills require a Python environment configured in your target repository (the repo where you will run skills):

1. Ensure you have Python 3.8+ installed.
2. Create a virtual environment:
	```bash
	python3 -m venv .venv
	```
3. Activate the environment:
	- On macOS/Linux:
	  ```bash
	  source .venv/bin/activate
	  ```
	- On Windows:
	  ```powershell
	  .venv\Scripts\Activate.ps1
	  ```
4. Copy the dependencies file from this repository to your target repository (if not already present):
	```bash
	cp /path/to/architect-ai-toolkit/requirements.txt /path/to/your/target-repo/
	```
5. Install dependencies in your target repo:
	```bash
	pip install -r requirements.txt
	```

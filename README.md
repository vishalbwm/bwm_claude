# BWM Claude

Custom overrides and automation for Banaraswala Wire Mesh P Limited.

## Features

### WIP RM Return Automation
- **Block WO Close with unreturned RM**: Prevents closing Work Orders that have excess raw material in WIP warehouse. Forces users to use "Return Components" first.
- **Block WO Stop with unreturned RM**: Same validation for Stop action.

## Installation

```bash
bench get-app https://github.com/banaraswala/bwm_claude.git
bench --site your-site install-app bwm_claude
```

## Version

0.0.1 - Initial release with WO close/stop RM validation

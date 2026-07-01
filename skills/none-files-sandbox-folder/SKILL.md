---
name: none-files-sandbox-folder
description: Handle none requests like: list the files in my sandbox folder
category: none
version: 1.0
use_count: 1
created: 2026-06-30 19:07
---

## When to Use
list the files in my sandbox folder

## Procedure
1. User asks: list the files in my sandbox folder
2. Tool used: none
3. Steps: detect intent -> run tool -> format response
4. Return result to user

## Example Output
`cd sandbox && ls` 
returns:
`code.sh  my_sandbox  SHRRI_projects  venv  workon.sh`

## Notes
- Auto-created by SHRRI
- Last updated: 2026-06-30 19:07
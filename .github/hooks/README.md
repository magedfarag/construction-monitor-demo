# Hook wiring

This folder contains a thin routing layer only.

GitHub Copilot CLI loads hook configuration from the current working directory. The dispatcher scripts forward hook payloads to the external optimizer repo referenced by `COPILOT_OPTIMIZER_HOME`.

These hooks are required for **live monitoring mode**.

They are **not required** for **historical import mode**, where you import existing Copilot exports into the external optimizer and analyze them offline.

In live mode, the external optimizer also captures before/after file snapshots for writable paths when possible so it can explain when later changes likely overwrote or removed features added by earlier prompts.

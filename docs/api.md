# Guardrail AI Platform API Reference

This document outlines the available FastAPI REST API endpoints.

## Endpoints

### 1. `GET /`
Returns a simple welcome message.

### 2. `GET /health`
Performs a health check on the service.
- **Response:** `{"status": "healthy"}`

### 3. `GET /policies`
Retrieves the loaded declarative policy ruleset.

### 4. `POST /evaluate`
Evaluates a target tool action against the policies.
- **Request Body (ActionRequest):**
  ```json
  {
    "tool": "database",
    "action": "delete",
    "record_count": 500
  }
  ```
- **Response (EvaluationResult):**
  ```json
  {
    "decision": "block",
    "matched_rule": "block_large_delete",
    "reason": "Delete request exceeds maximum allowed limit (100 records)."
  }
  ```

### 5. `POST /execute`
Evaluates the request and executes it on the target tool if allowed.
- **Request Body (ActionRequest):**
  ```json
  {
    "tool": "database",
    "action": "delete",
    "record_count": 5,
    "dry_run": false
  }
  ```
- **Response (ExecutionResult):**
  ```json
  {
    "status": "executed",
    "decision": "allow",
    "matched_rule": null,
    "reason": "No matching policy. Action allowed.",
    "tool_output": {
      "status": "success",
      "message": "5 records deleted"
    }
  }
  ```

### 6. `GET /simulate`
Runs the pre-configured simulation scenarios and prints details.

### 7. `GET /audit`
Returns the raw contents of the JSON Lines audit log file.

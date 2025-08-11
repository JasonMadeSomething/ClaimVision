# WebSocket Events and Payloads

This document lists all WebSocket messages the backend can deliver to the frontend, the source that emits them, and their expected payload shapes. All messages share a common envelope:

- type: string. Event identifier.
- timestamp: ISO8601 string (set by `notifier_handler.py`).
- data: object. Event-specific payload.

Notes
- Control acks from the `$default` route (`default_handler.py`) also use the same envelope shape.
- For batch-tracker notifications, `notifier_handler.py` promotes `notificationType` to the top-level `type` and injects `batchId`, `itemId`, and `notificationType` into `data` for easier client routing.

## Control / Acks from `$default`
Source: `src/websockets/default_handler.py`

- pong
  - Trigger: client sends `{ action: "ping" }`
  - Payload:
    ```json
    { "type": "pong", "timestamp": "<lambda ARN>" }
    ```

- subscribed
  - Trigger: client sends `{ action: "subscribe", "claimId": "<id>" }`
  - Payload:
    ```json
    { "type": "subscribed", "claimId": "<id>" }
    ```

- error
  - Trigger: invalid subscribe message (missing `claimId`)
  - Payload:
    ```json
    { "type": "error", "message": "Missing claimId for subscription" }
    ```

- echo
  - Trigger: any other message
  - Payload:
    ```json
    { "type": "echo", "message": { /* original client message */ } }
    ```

## Direct notifications
Source: `src/misc/websocket_sender.py` (emits to OUTBOUND_QUEUE -> `notifier_handler.py` -> WebSocket)

- file_processed
  - Envelope:
    ```json
    {
      "type": "file_processed",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "fileId": "file-123",
        "claimId": "claim-abc",
        "fileInfo": {
          "name": "doc.pdf",
          "size": 123456,
          "contentType": "application/pdf",
          "s3Key": "claims/claim-abc/doc.pdf",
          "presignedUrl": "https://s3/..." // present if s3Key available
        }
      }
    }
    ```

- analysis_complete
  - Envelope:
    ```json
    {
      "type": "analysis_complete",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "fileId": "file-123",
        "claimId": "claim-abc",
        "analysisResults": {
          "labels": [/* ... */],
          "confidence": {/* ... */}
        }
      }
    }
    ```

- export_status
  - status: "started" | "in_progress" | "completed" | "failed"
  - Envelope:
    ```json
    {
      "type": "export_status",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "exportId": "exp-1",
        "claimId": "claim-abc",
        "status": "completed",
        "details": { /* optional */ }
      }
    }
    ```

## Batch tracking notifications
Source: `src/batch/tracker_handler.py` (emits SQS with `messageType: notification` and `notificationType`; routed by `notifier_handler.py`)

Common fields injected by notifier into `data`:
- batchId: string
- itemId: string (except `batch_completed` which has counts and items)
- notificationType: string (duplicate of `type` for convenience)

- file_uploaded
  - Original data: `{ fileName }`
  - Envelope:
    ```json
    {
      "type": "file_uploaded",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "file_uploaded",
        "batchId": "batch-1",
        "itemId": "file-123",
        "fileName": "doc.pdf"
      }
    }
    ```

- file_analysis_queued
  - Original data: `{ messageId }`
  - Envelope:
    ```json
    {
      "type": "file_analysis_queued",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "file_analysis_queued",
        "batchId": "batch-1",
        "itemId": "file-123",
        "messageId": "sqs-msg-id"
      }
    }
    ```

- analysis_started
  - Original data: `{}`
  - Envelope:
    ```json
    {
      "type": "analysis_started",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "analysis_started",
        "batchId": "batch-1",
        "itemId": "file-123"
      }
    }
    ```

- analysis_completed
  - Original data: `{ success, labels?, error? }`
  - Envelope:
    ```json
    {
      "type": "analysis_completed",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "analysis_completed",
        "batchId": "batch-1",
        "itemId": "file-123",
        "success": true,
        "labels": [/* ... */]
      }
    }
    ```

- file_processed
  - Original data: `{ success, fileUrl?, error? }`
  - Envelope:
    ```json
    {
      "type": "file_processed",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "file_processed",
        "batchId": "batch-1",
        "itemId": "file-123",
        "success": true,
        "fileUrl": "https://..."
      }
    }
    ```

- export_started
  - Original data: `{ exportType }`
  - Envelope:
    ```json
    {
      "type": "export_started",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "export_started",
        "batchId": "batch-1",
        "itemId": "exp-1",
        "exportType": "pdf"
      }
    }
    ```

- export_completed
  - Original data: `{ success, exportUrl?, error? }`
  - Envelope:
    ```json
    {
      "type": "export_completed",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "export_completed",
        "batchId": "batch-1",
        "itemId": "exp-1",
        "success": true,
        "exportUrl": "https://..."
      }
    }
    ```

- batch_completed
  - Original data: `{ itemCount, completedCount, failedCount, items }`
  - Envelope:
    ```json
    {
      "type": "batch_completed",
      "timestamp": "2025-01-01T00:00:00Z",
      "data": {
        "notificationType": "batch_completed",
        "batchId": "batch-1",
        "itemCount": 10,
        "completedCount": 9,
        "failedCount": 1,
        "items": [ /* batch items with status + data */ ]
      }
    }
    ```

## Frontend handling
- The WebSocket client is provided by `claimvision-ui/src/context/WebSocketContext.tsx`.
- Connection URL: `NEXT_PUBLIC_WS_ENDPOINT` (falls back to `wss://ws.dev.claimvision.made-something.com`).
- Auth: Cognito ID token is passed as `?token=...` during connect.
- Heartbeat: sends `{ action: "ping" }` every 30s; expect `type: "pong"`.
- Subscribe to a claim: `subscribeToClaim(claimId)` sends `{ action: "subscribe", claimId }` and expect `type: "subscribed"`.

## Routing suggestions (UI)
- Switch on `message.type`:
  - Control: `pong`, `subscribed`, `error`, `echo`
  - File pipeline: `file_uploaded`, `file_analysis_queued`, `analysis_started`, `analysis_completed`, `file_processed`
  - Export: `export_started`, `export_completed`, `export_status`
  - Batch lifecycle: `batch_completed`
- Use `data.batchId`/`data.itemId` where present to update batch/item state.
- For `file_processed` (direct and tracker), prefer presigned URL if `data.fileInfo.presignedUrl` or `data.fileUrl`.

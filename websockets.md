# WebSocket Integration Checklist

## Infrastructure (Terraform)
- [ ] Create `outbound-messages` SQS queue
- [ ] Create DLQ for outbound queue (optional)
- [ ] Add SQS ARNs to `outputs.tf` for SAM integration
- [ ] Output IAM policy ARNs for SQS send permissions (optional)

## Infrastructure (SAM)
- [ ] Create WebSocket API Gateway (`AWS::ApiGatewayV2::Api`)
- [ ] Create WebSocket API Gateway stage (`prod`)
- [ ] Define WebSocket routes: `$connect`, `$disconnect`, `$default`
- [ ] Create integrations for each route → Lambda
- [ ] Create `$connect` Lambda to parse JWT and write to DynamoDB
- [ ] Create `$disconnect` Lambda to remove connection from DynamoDB
- [ ] Create `$default` Lambda (optional — handle subscription logic or no-op)
- [ ] Create `NotifierLambda` to consume messages from SQS and call `@connections`
- [ ] Create DynamoDB table `WebSocketConnections`
  - [ ] Use `connectionId` as partition key
  - [ ] Add GSI on `userId` and/or `claimId` (if needed)
  - [ ] Add TTL attribute for pruning stale connections (optional)
- [ ] Grant `$connect` Lambda permission to write to DynamoDB
- [ ] Grant `NotifierLambda` permission to:
  - [ ] Read from SQS
  - [ ] Read from DynamoDB
  - [ ] Call `execute-api:ManageConnections` on WebSocket API
  - [ ] Add DNS record for WebSocket API 

## Application Changes
- [ ] Update export pipeline Lambda to send message to `outbound-messages` queue
- [ ] Update upload/analyze Lambdas to send to the same queue
- [ ] Standardize message structure across all producers
- [ ] Add `OUTBOUND_QUEUE_URL` to all producer Lambda environment variables
- [ ] Update IAM roles for producers to allow `sqs:SendMessage`
- [ ] Implement `NotifierLambda` logic:
  - [ ] Parse SQS message
  - [ ] Query DynamoDB for relevant `connectionId`s
  - [ ] POST to WebSocket Management API
  - [ ] Handle `GoneException` and remove stale connections
  - [ ] Log failures, push to DLQ if needed

## Configuration / Env Vars
- [ ] `OUTBOUND_QUEUE_URL` → all message-producing Lambdas
- [ ] `DYNAMO_TABLE_NAME` → `$connect`, `NotifierLambda`
- [ ] `WS_API_ENDPOINT` → `NotifierLambda` (e.g., `https://{api-id}.execute-api...`)
- [ ] `JWT_SECRET` or `PUBLIC_KEY` → `$connect` Lambda

## Testing / Local Dev
- [ ] Add `wscat` test script for local verification
- [ ] Create mock HTML test client to simulate frontend
- [ ] Generate fake JWTs for `$connect` testing
- [ ] Mock SQS messages to test `NotifierLambda` locally
- [ ] Update CI/Makefile to ensure SAM + Terraform coordination

## Monitoring / Enhancements (Optional)
- [ ] Add CloudWatch alarms for:
  - [ ] SQS queue age or depth
  - [ ] DLQ activity
  - [ ] `NotifierLambda` error rate
- [ ] Add TTL to DynamoDB table to auto-expire old records
- [ ] Add structured logging to WebSocket handlers
- [ ] Implement frontend reconnect logic

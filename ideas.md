# Ideas
## User Experience

 - Trauma Informed
 - Low-Stress
 - Clean
 - User friendly
 - User Control
 - ***My Documents* Section**
 - More Visual Cues
 - Resources Page (lighthearted -> Not official)
 - Contacts Table segregated by Claim
 - *My Resources* page (User Maintained) -> Schema Changes + Additional Endpoint
 - *My Contacts* Bar (User Maintained) -> Schema Changes + Additional Endpoint
 - *My Documents* DropZone -> *My Documents* Page (User Maintained)
 - Invite User to Household -> Schema Changes + Additional Endpoint
 - Invite Adjuster to view claim -> Schema Changes + Additional Endpoint
 - Room Overview Photos -> Possible Schema Change, might be able to graft on to upload or file edit
 - Waterline Documentation -> Possible Schema Change, might be able to graft on to upload or file edit
 - First time instruction modal per user (tutorial)
 - Progress Tracking (x of y files associated to items; x of y items associated to rooms)
 - Finalization flag on items (When claim submitted)
 - Invite adjuster to view claim

## Technical
 - Zip Upload -> might work, untested
 - Room mapping on Zip Upload -> might work, untested
 - Webhook for upload completion
 - Webhook for report generation
 - ~~Presigned S3 Uploads~~
 - Group ID -> Access policy abstraction -> Nearly done
 - Claim Workbench endpoint (Load all resources on one pull) -> Maybe an additional endpoint, maybe enhance the existing one
 - Have the Web UI be ***less*** shit -> might be irrelevant now
 - iPhone App -> ~~Buy a mac~~
 - Android App
 - Improve logging (who cares other than me though?)
 - Metadata normalization (multi source uploads)
 - Report report -> To report on reports internally. Probably an additional endpoint
 - Monitoring/Alerting
 - DLQ Inegration -> Not an endpoint, but definitely an auxillary lambda. Maybe webhooks?
 - Training consent screen -> Schema Changes
 - AI confidence slider -> Schema Changes
 - Offline mode
 - PATCH /claims/{id}/change-group -> Maybe not a schema change, but an additional endpoint
    - Body:
        ```json
        {
            "new_group_id": "uuid-of-target-group"
        }
        ```
 - GET /users/{id}/groups (For additional context)
 - Admin onboarding for non houshold type users -> Additional Endpoint(s)
 - Multiple group support (ie. Household, Adjuster, etc.) -> Additional Endpoint(s)
 - CI/CD when I feel like an adult (Did I already do this to the extent I need to?)
 - Group invite by invite code (need a new table for this) -> Schema Changes + Additional Endpoint(s)
 - Invite User to Household -> Schema Changes + Additional Endpoint(s)
 - Invite Adjuster to view claim -> Schema Changes + Additional Endpoint(s)
 - Harden registration process (stop login spam) -> Figure out how to do this
 - ~~Cross Machine CI Pipeline (Makefile(s))~~
 - Notes on files (new table) -> Schema Changes
 - Notes on items -> rollup file notes
 - Notes on claims -> rollup file notes
 - Notes on rooms -> rollup items notes?
 - Notes on claims -> rollup room notes?

 | Feature | Table | Field(s) | Endpoint(s) | Notes |
 | --- | --- | --- | --- | --- |
 | My Resources | Resources | Various | GET /resources | This should exist on the group level. Is this just a high level notes function?|
 | My Contacts | Contacts | Various | GET /contacts | This should exist on the claim level|
 | My Documents | Files | Various | GET /documents | There are basically a type of file, but they should be flagged for placement on a seperate endpoint|
 | File Documentation Types| Files | Documentation Type | GET /files/{file_id} | Kind of like an expansion of above, but allows for things like waterlines or pre-disaster photos |
 | File Notes | Notes | Various | GET /files/{file_id}/notes | Might need to generalize this to items, claims, and rooms |
 | Item Notes | Notes | Various | GET /items/{item_id}/notes | Do I want to rollup file notes or have item notes a seprate entity? |
 | Rooms as lookup | Claim_Rooms | Various | GET /claim/{claim_id}/rooms -> POST /claim/{claim_id}/rooms | |
 | AI Confidence Slider | User Settings | AI Confidence | PUT /users/{user_id}/settings | |
 | User Training Consent | User Settings | Training Consent | PUT /users/{user_id}/settings | |
 | Invite to Claim | Claim_Invite | Various | POST /claim_invites | |
 | Invite to group | Group_Invite | Various | POST /group_invites | |
 | Invites | Invites | Various | POST /invites | Maybe this is the polymorphic invite table?|
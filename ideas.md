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
 - Zip Upload
 - Room mapping on Zip Upload
 - Webhook for upload completion
 - Webhook for report generation
 - Presigned S3 Uploads
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
 - PATCH /claims/{id}/change-group -> Schema Changes
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
 - 
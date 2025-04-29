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
 - *My Resources* page (User Maintained)
 - *My Contacts* Bar (User Maintained)
 - *My Documents* DropZone -> *My Documents* Page (User Maintained)
 - Invite User to Household
 - Invite Adjuster to view claim
 - Room Overview Photos
 - Waterline Documentation
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
 - Group ID -> Access policy abstraction
 - Claim Workbench endpoint (Load all resources on one pull)
 - Have the Web UI be ***less*** shit -> might be irrelevant now
 - iPhone App -> ~~Buy a mac~~
 - Android App
 - Improve logging (who cares other than me though?)
 - Metadata normalization (multi source uploads)
 - Report report
 - Monitoring/Alerting
 - DLQ Inegration
 - Training consent screen
 - AI confidence slider
 - Offline mode
 - PATCH /claims/{id}/change-group
    - Body:
        ```json
        {
            "new_group_id": "uuid-of-target-group"
        }
        ```
 - GET /users/{id}/groups (For additional context)
 - Invite User to Household
 - Invite Adjuster to view claim
 - Admin onboarding for non houshold type users
 - Multiple group support (ie. Household, Adjuster, etc.)
 - CI/CD when I feel like an adult (Did I already do this to the extent I need to?)
 - Group invite by invite code (need a new table for this)
 - Invite User to Household
 - Invite Adjuster to view claim
 - Harden registration process (stop login spam)
 - ~~Cross Machine CI Pipeline (Makefile(s))~~
 - Notes on files (new table)
 - 
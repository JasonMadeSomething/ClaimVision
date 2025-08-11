# Tech Debt

## Lambda Handler Cleanup

Many lambda handlers are not following the same pattern and are missing important error handling and logging.

## Invite abuse prevention

Invite abuse prevention is not implemented. Need some way to gate access to invites for adjusters but allow housholds to be arbitrarily large.
I can manually create invite keys for now and that can serve as a stop gap.

## Access decorator

Access decorator exists but isn't used. It can probably simplify redundant access control logic.

## Split off zip file processing

Zip file processing is currently handled in the post s3 lambda. It should be split off into its own lambda.
Will probably look like: 
    when a file is sent to s3, the post s3 lambda will check the type of the file and either route it to the zip processing lambda or the file processing lambda
    the zip processing lambda will extract the files from the zip and send them to s3 and the file processing lambda
    the file processing lambda will process the files reguadless of the source. the unzipper sends messages to the same queue as the post s3 lambda



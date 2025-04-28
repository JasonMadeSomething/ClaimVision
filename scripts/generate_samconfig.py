import argparse
import json
import subprocess
import os
import sys
import re

# -----------------------------
# REPLACEMENT SOURCES (Single Source of Truth)
# -----------------------------
REPLACEMENT_SOURCES = {
    "{{ENV}}": ("static", None, None),

    # Cognito
    "{{USER_POOL_ID}}": ("cognito", "CognitoUserPoolId", None),
    "{{USER_POOL_CLIENT}}": ("cognito", "CognitoUserPoolClientId", None),

    # Terraform Outputs
    "{{S3_BUCKET_NAME}}": ("terraform", "s3_bucket_name", lambda d: d["value"]),
    "{{REPORTS_BUCKET_NAME}}": ("terraform", "reports_bucket_name", lambda d: d["value"]),
    "{{DB_USERNAME_SSM_PATH}}": ("terraform", "db_username_ssm_path", lambda d: d["value"]),
    "{{DB_PASSWORD_SSM_PATH}}": ("terraform", "db_password_ssm_path", lambda d: d["value"]),
    "{{RDS_ENDPOINT_SSM_PATH}}": ("terraform", "rds_endpoint_ssm_path", lambda d: d["value"]),
    "{{DB_ENDPOINT}}": ("terraform", "rds_endpoint", lambda d: d["value"]),
    "{{VPC_ID}}": ("terraform", "vpc_id", lambda d: d["value"]),
    "{{SUBNET_IDS}}": ("terraform", "subnet_ids", lambda d: ",".join(d["value"])),
    "{{SECURITY_GROUP_IDS}}": ("terraform", "rds_security_group_id", lambda d: d["value"]),
    "{{PUBLIC_SUBNET_1}}": ("terraform", "public_subnet_1", lambda d: d["value"]),
    "{{PUBLIC_SUBNET_2}}": ("terraform", "public_subnet_2", lambda d: d["value"]),
    "{{EFS_ACCESS_POINT_ARN}}": ("terraform", "efs_access_point_arn", lambda d: d["value"]),
    "{{EFS_FILE_SYSTEM_ID}}": ("terraform", "efs_file_system_id", lambda d: d["value"]),

    # SQS Queues
    "{{FILE_UPLOAD_QUEUE_URL}}": ("terraform", "file_upload_queue_url", lambda d: d["value"]),
    "{{FILE_UPLOAD_QUEUE_ARN}}": ("terraform", "file_upload_queue_arn", lambda d: d["value"]),
    "{{FILE_UPLOAD_QUEUE_NAME}}": ("terraform", "file_upload_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{FILE_ANALYSIS_QUEUE_URL}}": ("terraform", "file_analysis_queue_url", lambda d: d["value"]),
    "{{FILE_ANALYSIS_QUEUE_ARN}}": ("terraform", "file_analysis_queue_arn", lambda d: d["value"]),
    "{{FILE_ANALYSIS_QUEUE_NAME}}": ("terraform", "file_analysis_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{USER_REGISTRATION_QUEUE_URL}}": ("terraform", "user_registration_queue_url", lambda d: d["value"]),
    "{{USER_REGISTRATION_QUEUE_ARN}}": ("terraform", "user_registration_queue_arn", lambda d: d["value"]),
    "{{USER_REGISTRATION_QUEUE_NAME}}": ("terraform", "user_registration_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{COGNITO_UPDATE_QUEUE_URL}}": ("terraform", "cognito_update_queue_url", lambda d: d["value"]),
    "{{COGNITO_UPDATE_QUEUE_ARN}}": ("terraform", "cognito_update_queue_arn", lambda d: d["value"]),
    "{{COGNITO_UPDATE_QUEUE_NAME}}": ("terraform", "cognito_update_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{FILE_ORGANIZATION_QUEUE_URL}}": ("terraform", "file_organization_queue_url", lambda d: d["value"]),
    "{{FILE_ORGANIZATION_QUEUE_ARN}}": ("terraform", "file_organization_queue_arn", lambda d: d["value"]),
    "{{FILE_ORGANIZATION_QUEUE_NAME}}": ("terraform", "file_organization_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{REPORT_REQUEST_QUEUE_URL}}": ("terraform", "report_request_queue_url", lambda d: d["value"]),
    "{{REPORT_REQUEST_QUEUE_ARN}}": ("terraform", "report_request_queue_arn", lambda d: d["value"]),
    "{{REPORT_REQUEST_QUEUE_NAME}}": ("terraform", "report_request_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{DELIVER_REPORT_QUEUE_URL}}": ("terraform", "deliver_report_queue_url", lambda d: d["value"]),
    "{{DELIVER_REPORT_QUEUE_ARN}}": ("terraform", "deliver_report_queue_arn", lambda d: d["value"]),
    "{{EMAIL_QUEUE_URL}}": ("terraform", "email_queue_url", lambda d: d["value"]),
    "{{EMAIL_QUEUE_ARN}}": ("terraform", "email_queue_arn", lambda d: d["value"]),
    "{{EMAIL_QUEUE_NAME}}": ("terraform", "email_queue_url", lambda d: d["value"].split('/')[-1]),
    "{{S3_UPLOAD_NOTIFICATION_QUEUE_URL}}": ("terraform", "s3_upload_notification_queue_url", lambda d: d["value"]),
    "{{S3_UPLOAD_NOTIFICATION_QUEUE_ARN}}": ("terraform", "s3_upload_notification_queue_arn", lambda d: d["value"]),

    # DNS/SES
    "{{API_DOMAIN_NAME}}": ("secrets", "ApiDomainName", None),
    "{{HOSTED_ZONE_ID}}": ("secrets", "HostedZoneId", None),
    "{{FRONTEND_ORIGIN}}": ("secrets", "FrontendOrigin", None),
    "{{SENDER_EMAIL}}": ("secrets", "SenderEmail", None),

    # Database Credentials
    "{{DB_USERNAME}}": ("secrets", "DBUsername", None),
    "{{DB_PASSWORD}}": ("secrets", "DBPassword", None),
}

# -----------------------------
# Helper Functions
# -----------------------------

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}\n{result.stderr}")
        sys.exit(1)
    return result.stdout

def load_json_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def fetch_cognito_outputs(env):
    stack_name = f"ClaimVision-cognito-{env}"
    try:
        output = run_cmd(f"aws cloudformation describe-stacks --stack-name {stack_name}")
        data = json.loads(output)
        outputs = data['Stacks'][0].get('Outputs', [])
        output_dict = {item['OutputKey']: item['OutputValue'] for item in outputs}
        return output_dict
    except Exception as e:
        print(f"Error fetching Cognito outputs for stack {stack_name}: {e}")
        return {}

# -----------------------------
# Main Script
# -----------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="dev", help="Environment (dev/staging/prod)")
    args = parser.parse_args()
    env = args.env

    terraform_outputs = json.loads(run_cmd("terraform -chdir=terraform output -json"))
    cognito_outputs = fetch_cognito_outputs(env)
    secrets = load_json_file("scripts/secrets.json")

    # Load template
    with open("samconfig.template.toml", "r") as f:
        template_content = f.read()

    replacements = {}

    for placeholder, (source_type, key, transform_fn) in REPLACEMENT_SOURCES.items():
        if source_type == "terraform":
            source = terraform_outputs
        elif source_type == "cognito":
            source = cognito_outputs
        elif source_type == "secrets":
            source = secrets
        elif source_type == "static":
            source = env
            key = None
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        value = source.get(key) if key else source

        if value is None:
            raise ValueError(f"Missing value for placeholder {placeholder}")

        if transform_fn:
            value = transform_fn(value)

        replacements[placeholder] = str(value)

    # Replace all placeholders
    for placeholder, replacement in replacements.items():
        template_content = template_content.replace(placeholder, replacement)

    # Write final output
    with open("samconfig.toml", "w") as f:
        f.write(template_content)

    print("✅ samconfig.toml successfully generated.")

if __name__ == "__main__":
    main()

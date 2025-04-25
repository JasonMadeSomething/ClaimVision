import json
import os
import shutil
import subprocess
from pathlib import Path

# Dynamically locate project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define paths relative to project root
TEMPLATE_FILE = PROJECT_ROOT / "samconfig.template.toml"
OUTPUT_FILE = PROJECT_ROOT / "samconfig.toml"
TF_OUTPUTS_FILE = PROJECT_ROOT / "terraform_outputs.json"

def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)

def get_cognito_outputs(stack_name):
    print(f"🔍 Fetching Cognito stack outputs for {stack_name}...")
    try:
        output = subprocess.check_output([
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", stack_name,
            "--output", "json"
        ], text=True)
        data = json.loads(output)
        outputs = {}
        for item in data["Stacks"][0].get("Outputs", []):
            outputs[item["OutputKey"]] = item["OutputValue"]
        return outputs
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to fetch Cognito outputs: {e}")
        return {}

def patch_template(template_path, output_path, replacements):
    shutil.copyfile(template_path, output_path)
    with open(output_path, "r") as f:
        content = f.read()
    for key, value in replacements.items():
        content = content.replace(key, value)
    with open(output_path, "w") as f:
        f.write(content)

def main():
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template file {TEMPLATE_FILE} not found.")

    terraform_outputs = {}
    if TF_OUTPUTS_FILE.exists():
        terraform_outputs = load_json(TF_OUTPUTS_FILE)

    cognito_outputs = get_cognito_outputs("ClaimVision-cognito-dev")

    replacements = {
        # Cognito outputs
        "{{USER_POOL_ID}}"     : cognito_outputs.get("CognitoUserPoolId", ""),
        "{{USER_POOL_CLIENT}}" : cognito_outputs.get("CognitoAppClientId", ""),
        
        # S3 outputs
        "{{S3_BUCKET_NAME}}"   : terraform_outputs.get("s3_bucket_name", {}).get("value", ""),
        "{{REPORTS_BUCKET_NAME}}": terraform_outputs.get("reports_bucket_name", {}).get("value", ""),
        
        # SSM paths
        "{{DB_USERNAME_SSM_PATH}}": terraform_outputs.get("db_username_ssm_path", {}).get("value", ""),
        "{{DB_PASSWORD_SSM_PATH}}": terraform_outputs.get("db_password_ssm_path", {}).get("value", ""),
        "{{RDS_ENDPOINT_SSM_PATH}}": terraform_outputs.get("rds_endpoint_ssm_path", {}).get("value", ""),
        
        # Database outputs
        "{{DB_ENDPOINT}}"      : terraform_outputs.get("rds_endpoint", {}).get("value", ""),
        
        # VPC outputs
        "{{VPC_ID}}"           : terraform_outputs.get("vpc_id", {}).get("value", ""),
        "{{SUBNET_IDS}}"       : ",".join(terraform_outputs.get("subnet_ids", {}).get("value", [])),
        "{{SECURITY_GROUP_IDS}}": terraform_outputs.get("security_group_ids", {}).get("value", []),
        "{{PUBLIC_SUBNET_1}}"  : terraform_outputs.get("public_subnet_1", {}).get("value", ""),
        "{{PUBLIC_SUBNET_2}}"  : terraform_outputs.get("public_subnet_2", {}).get("value", ""),
        "{{RDS_SECURITY_GROUP_ID}}": terraform_outputs.get("rds_security_group_id", {}).get("value", ""),
        
        # EFS outputs
        "{{EFS_ACCESS_POINT_ARN}}": terraform_outputs.get("efs_access_point_arn", {}).get("value", ""),
        "{{EFS_FILE_SYSTEM_ID}}": terraform_outputs.get("efs_file_system_id", {}).get("value", ""),
        
        # SQS queues - File Upload
        "{{FILE_UPLOAD_QUEUE_URL}}": terraform_outputs.get("file_upload_queue_url", {}).get("value", ""),
        "{{FILE_UPLOAD_QUEUE_ARN}}": terraform_outputs.get("file_upload_queue_arn", {}).get("value", ""),
        "{{FILE_UPLOAD_QUEUE_NAME}}": terraform_outputs.get("file_upload_queue_name", {}).get("value", ""),
        
        # SQS queues - File Analysis
        "{{FILE_ANALYSIS_QUEUE_URL}}": terraform_outputs.get("file_analysis_queue_url", {}).get("value", ""),
        "{{FILE_ANALYSIS_QUEUE_ARN}}": terraform_outputs.get("file_analysis_queue_arn", {}).get("value", ""),
        "{{FILE_ANALYSIS_QUEUE_NAME}}": terraform_outputs.get("file_analysis_queue_name", {}).get("value", ""),
        
        # SQS queues - User Registration
        "{{USER_REGISTRATION_QUEUE_URL}}": terraform_outputs.get("user_registration_queue_url", {}).get("value", ""),
        "{{USER_REGISTRATION_QUEUE_ARN}}": terraform_outputs.get("user_registration_queue_arn", {}).get("value", ""),
        "{{USER_REGISTRATION_QUEUE_NAME}}": terraform_outputs.get("user_registration_queue_name", {}).get("value", ""),
        
        # SQS queues - Cognito Update
        "{{COGNITO_UPDATE_QUEUE_URL}}": terraform_outputs.get("cognito_update_queue_url", {}).get("value", ""),
        "{{COGNITO_UPDATE_QUEUE_ARN}}": terraform_outputs.get("cognito_update_queue_arn", {}).get("value", ""),
        "{{COGNITO_UPDATE_QUEUE_NAME}}": terraform_outputs.get("cognito_update_queue_name", {}).get("value", ""),
        
        # SQS queues - File Organization
        "{{FILE_ORGANIZATION_QUEUE_URL}}": terraform_outputs.get("file_organization_queue_url", {}).get("value", ""),
        "{{FILE_ORGANIZATION_QUEUE_ARN}}": terraform_outputs.get("file_organization_queue_arn", {}).get("value", ""),
        "{{FILE_ORGANIZATION_QUEUE_NAME}}": terraform_outputs.get("file_organization_queue_name", {}).get("value", ""),
        
        # SQS queues - Report Request
        "{{REPORT_REQUEST_QUEUE_URL}}": terraform_outputs.get("report_request_queue_url", {}).get("value", ""),
        "{{REPORT_REQUEST_QUEUE_ARN}}": terraform_outputs.get("report_request_queue_arn", {}).get("value", ""),
        "{{REPORT_REQUEST_QUEUE_NAME}}": terraform_outputs.get("report_request_queue_name", {}).get("value", ""),
        
        # SQS queues - Deliver Report
        "{{DELIVER_REPORT_QUEUE_URL}}": terraform_outputs.get("deliver_report_queue_url", {}).get("value", ""),
        "{{DELIVER_REPORT_QUEUE_ARN}}": terraform_outputs.get("deliver_report_queue_arn", {}).get("value", ""),
        
        # SQS queues - Email
        "{{EMAIL_QUEUE_URL}}": terraform_outputs.get("email_queue_url", {}).get("value", ""),
        "{{EMAIL_QUEUE_ARN}}": terraform_outputs.get("email_queue_arn", {}).get("value", ""),
        "{{EMAIL_QUEUE_NAME}}": terraform_outputs.get("email_queue_name", {}).get("value", ""),
        
        # SQS queues - S3 Upload Notification (new)
        "{{S3_UPLOAD_NOTIFICATION_QUEUE_URL}}": terraform_outputs.get("s3_upload_notification_queue_url", {}).get("value", ""),
        "{{S3_UPLOAD_NOTIFICATION_QUEUE_ARN}}": terraform_outputs.get("s3_upload_notification_queue_arn", {}).get("value", ""),
        
        # SES
        "{{SENDER_EMAIL}}": terraform_outputs.get("sender_email", {}).get("value", ""),
        
        # DNS
        "{{API_DOMAIN_NAME}}": terraform_outputs.get("api_domain_name", {}).get("value", ""),
        "{{HOSTED_ZONE_ID}}": terraform_outputs.get("hosted_zone_id", {}).get("value", ""),
        "{{FRONTEND_ORIGIN}}": terraform_outputs.get("frontend_origin", {}).get("value", ""),
    }

    patch_template(TEMPLATE_FILE, OUTPUT_FILE, replacements)
    print(f"✅ Generated {OUTPUT_FILE.relative_to(PROJECT_ROOT)} successfully.")

if __name__ == "__main__":
    main()

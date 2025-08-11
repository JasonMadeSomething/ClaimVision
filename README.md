# ClaimVision

**Flood damage claim management born from necessity**

When my house flooded, documenting everything for insurance was a nightmare. Hundreds of photos, room-by-room organization, item lists, receipts—all managed in spreadsheets and folders. ClaimVision is the tool I wish I'd had.

## 🎯 Overview

Built after personally navigating a flood claim, ClaimVision eliminates the friction in damage documentation by providing:

- **Flood-Focused Workflow** - Built specifically for the chaos of flood damage documentation
- **Intelligent Photo Organization** - Upload photos and organize by room with drag-and-drop simplicity
- **Automated Item Detection** - AI-powered image analysis identifies damaged items and suggests categorizations
- **Structured Documentation** - Tag items, add descriptions, and maintain detailed damage records
- **Professional Reporting** - Generate comprehensive claim reports ready for insurance submission
- **Secure & Private** - Enterprise-grade security with user authentication and data encryption

*"The tool I wish I'd had when my house flooded."*

---

## ✨ Key Features

### 📸 Smart Photo Management
- Batch file uploads with drag-and-drop interface
- Automatic image analysis using AWS Rekognition
- Room-based organization with visual workbench
- Support for multiple file formats and sizes

### 🏠 Room & Item Organization
- Create custom room layouts for your property
- Drag photos between rooms to organize documentation
- Create item entries linked to supporting photos
- Tag and categorize items with detailed descriptions

### 🤖 AI-Powered Analysis
- Automatic object detection and labeling
- Intelligent suggestions for item categorization

### 📊 Professional Reporting
- Generate structured claim reports
- Email delivery of completed reports
- Audit trail of all documentation activities

### 🔒 Enterprise Security
- AWS Cognito authentication
- Role-based access control
- Encrypted data storage
- Private file handling

---

## 🏗️ Architecture

ClaimVision is built as a modern, scalable cloud-native application:

### Frontend
- **Next.js 14** with TypeScript
- **React** with hooks and modern patterns
- **TailwindCSS** for responsive design
- **React DnD** for drag-and-drop functionality
- **Headless UI** components

### Backend
- **AWS Lambda** serverless functions (Python 3.12)
- **Amazon API Gateway** for REST API
- **AWS Cognito** for authentication
- **Amazon RDS** (PostgreSQL) for data persistence
- **Amazon S3** for file storage
- **Amazon SQS** for async processing
- **Amazon Rekognition** for image analysis

### Infrastructure
- **AWS SAM** for serverless deployment
- **Terraform** for infrastructure as code
- **VPC** with private subnets and security groups
- **EFS** for shared file processing
- **CloudWatch** for monitoring and logging

---

## 🚀 API Endpoints

### Claims Management
```
POST   /claims                    # Create new claim
GET    /claims/{claim_id}         # Get claim details
PUT    /claims/{claim_id}         # Update claim
DELETE /claims/{claim_id}         # Delete claim
```

### File & Photo Management
```
POST   /claims/{claim_id}/files/upload    # Upload files
GET    /claims/{claim_id}/files           # List claim files
DELETE /files/{file_id}                  # Delete file
```

### Room Organization
```
GET    /claims/{claim_id}/rooms           # Get claim rooms
POST   /claims/{claim_id}/rooms/{room_id} # Add room to claim
```

### Item Management
```
POST   /claims/{claim_id}/items           # Create item
GET    /claims/{claim_id}/items           # List items
PUT    /items/{item_id}                   # Update item
DELETE /items/{item_id}                   # Delete item
```

### Reporting
```
POST   /claims/{claim_id}/reports/request # Request claim report
GET    /reports/{report_id}               # Download report
```

---

## 🛠️ Tech Stack

**Frontend**
- Next.js 14, TypeScript, React 18
- TailwindCSS, Headless UI, Heroicons
- React DnD, React Dropzone
- Jest & Testing Library

**Backend**
- Python 3.12, SQLAlchemy, Pydantic
- AWS Lambda, API Gateway, Cognito
- PostgreSQL, S3, SQS, Rekognition
- Boto3, PyJWT

**Infrastructure**
- AWS SAM, Terraform
- VPC, EFS, CloudWatch
- Route 53, ACM

**Development**
- ESLint, Prettier
- GitHub Actions
- Docker for local development

---

## 🏃‍♂️ Quick Start

### Prerequisites
- Node.js 18+
- Python 3.12+
- AWS CLI configured
- Terraform
- Make

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/jasonmadesomething/claimvision.git
   cd claimvision
   ```

2. **Set up infrastructure with Terraform**
   ```bash
   cd terraform
   # Configure your terraform variables
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your AWS settings
   
   terraform init
   terraform plan
   terraform apply
   ```

3. **Build and deploy backend**
   ```bash
   # From project root
   make build    # Build the SAM application
   make deploy   # Deploy to AWS
   ```

4. **Set up the frontend**
   ```bash
   cd claimvision-ui
   npm install
   cp .env.example .env.local
   # Configure your environment variables with deployed API endpoints
   npm run dev
   ```

5. **Access the application**
   ```
   Frontend: http://localhost:3000
   API: Your deployed API Gateway endpoint from SAM output
   ```

---

## 📁 Project Structure

```
claimvision/
├── claimvision-ui/          # Next.js frontend application
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   ├── types/           # TypeScript definitions
│   │   └── utils/           # Frontend utilities
│   └── package.json
├── src/                     # Python Lambda functions
│   ├── claims/              # Claim management functions
│   ├── files/               # File upload & processing
│   ├── items/               # Item management
│   ├── rooms/               # Room organization
│   ├── reports/             # Report generation
│   └── utils/               # Shared utilities
├── terraform/               # Infrastructure as code
│   ├── networking/          # VPC, subnets, security groups
│   ├── application/         # EFS, S3, queues
│   └── cognito/             # Authentication setup
├── template.yaml            # SAM template
└── README.md
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🙏 Acknowledgments

Born from the frustrating experience of documenting flood damage with spreadsheets and photo folders. Sometimes the best tools come from solving your own problems.

If you've dealt with flood damage, you know the pain. This is my attempt to make it a little easier for the next person.

---

*ClaimVision - The flood claim tool I wish I'd had.*

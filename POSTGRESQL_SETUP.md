# PostgreSQL Setup Guide for ATS

This guide will walk you through setting up PostgreSQL for your ATS application in production.

## Prerequisites

- PostgreSQL installed on your server
- Access to create databases and users in PostgreSQL

## Setup Steps

### 1. Install PostgreSQL

If PostgreSQL is not already installed on your server:

```bash
# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# For RHEL/CentOS
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 2. Create a Database and User for ATS

```bash
# Log in as postgres user
sudo -u postgres psql

# In PostgreSQL shell, create the database and user
CREATE DATABASE ats;
CREATE USER atsuser WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE ats TO atsuser;
\q
```

### 3. Configure Environment Variables

Set the following environment variables on your production server:

```bash
# Database configuration
export FLASK_ENV=production
export DB_USER=atsuser
export DB_PASSWORD=your_secure_password
export DB_HOST=localhost  # Change if your DB is on a different server
export DB_PORT=5432
export DB_NAME=ats

# Other required environment variables
export SECRET_KEY=your_secure_secret_key
export JWT_SECRET_KEY=your_secure_jwt_secret
export MISTRAL_API_KEY=your_mistral_api_key
export GROQ_API_KEY=your_groq_api_key

# You can add these to your .env file or to your server's environment
```

### 4. Update Docker Configuration (If using Docker)

If you're using Docker, update your `docker-compose.yml` to include the PostgreSQL service:

```yaml
version: '3'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DB_USER=atsuser
      - DB_PASSWORD=your_secure_password
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=ats
      - SECRET_KEY=your_secure_secret_key
      - JWT_SECRET_KEY=your_secure_jwt_secret
      - MISTRAL_API_KEY=your_mistral_api_key
      - GROQ_API_KEY=your_groq_api_key
    depends_on:
      - db
  
  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=atsuser
      - POSTGRES_PASSWORD=your_secure_password
      - POSTGRES_DB=ats

volumes:
  postgres_data:
```

### 5. Run the Migration Script

Run the migration script to set up the database tables:

```bash
python migrate_db.py
```

### 6. Verify the Setup

Start your application and verify that it's connecting to the PostgreSQL database:

```bash
python app.py
```

Check the logs to make sure the application is using PostgreSQL and not SQLite.

## Docker Deployment

### 1. Build and Run Docker Container Locally

```bash
# Build the Docker image
docker build -t ats-app:latest .

# Run the container with PostgreSQL using docker-compose
docker-compose up --build
```

### 2. Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Tag your image with your Docker Hub username
docker tag ats-app:latest yourusername/ats-app:latest

# Push the image to Docker Hub
docker push yourusername/ats-app:latest
```

## AWS Deployment

### 1. Prerequisites
- AWS CLI installed and configured with appropriate permissions
- An ECR repository created for your application

### 2. Deploy to Amazon ECR

```bash
# Login to Amazon ECR
aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-aws-account-id.dkr.ecr.your-region.amazonaws.com

# Tag the image for ECR
docker tag ats-app:latest your-aws-account-id.dkr.ecr.your-region.amazonaws.com/ats-app:latest

# Push to ECR
docker push your-aws-account-id.dkr.ecr.your-region.amazonaws.com/ats-app:latest
```

### 3. Deploy to AWS ECS or EKS

#### For ECS with Fargate:

```bash
# Create a task definition (replace placeholders with your values)
aws ecs register-task-definition \
  --family ats-app \
  --container-definitions "[{\"name\":\"ats-app\",\"image\":\"your-aws-account-id.dkr.ecr.your-region.amazonaws.com/ats-app:latest\",\"essential\":true,\"portMappings\":[{\"containerPort\":5000,\"hostPort\":5000}],\"environment\":[{\"name\":\"FLASK_ENV\",\"value\":\"production\"},{\"name\":\"DB_HOST\",\"value\":\"your-rds-endpoint\"},{\"name\":\"DB_USER\",\"value\":\"atsuser\"},{\"name\":\"DB_PASSWORD\",\"value\":\"your_secure_password\"},{\"name\":\"DB_NAME\",\"value\":\"ats\"}]}]" \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 1024 \
  --memory 2048 \
  --execution-role-arn arn:aws:iam::your-aws-account-id:role/ecsTaskExecutionRole

# Create a service
aws ecs create-service \
  --cluster your-cluster \
  --service-name ats-app-service \
  --task-definition ats-app:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678],securityGroups=[sg-12345678],assignPublicIp=ENABLED}"
```

### 4. Using AWS RDS for PostgreSQL

Instead of running PostgreSQL in a container, you may want to use Amazon RDS for production:

```bash
# Create an RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier ats-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username atsuser \
  --master-user-password your_secure_password \
  --allocated-storage 20 \
  --db-name ats
```

Update your environment variables to point to the RDS instance:

```bash
export DB_HOST=your-rds-endpoint.rds.amazonaws.com
```

## Monitoring and Scaling

### CloudWatch Monitoring

```bash
# Enable CloudWatch monitoring for your ECS service
aws ecs update-service \
  --cluster your-cluster \
  --service ats-app-service \
  --enable-execute-command
```

### Auto-scaling

```bash
# Configure Auto Scaling for your ECS service
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/your-cluster/ats-app-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 5

# Create a scaling policy based on CPU utilization
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/your-cluster/ats-app-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration "{ \
    \"TargetValue\": 70.0, \
    \"PredefinedMetricSpecification\": { \
      \"PredefinedMetricType\": \"ECSServiceAverageCPUUtilization\" \
    } \
  }"
```

## Troubleshooting

- **Connection Issues**: Make sure your PostgreSQL server is configured to accept connections from your application server (check pg_hba.conf).
- **Permission Issues**: Ensure the user has the right permissions on the database.
- **Missing Dependencies**: Ensure psycopg2-binary is installed (`pip install psycopg2-binary`).

## Backup Recommendations

Set up regular backups of your PostgreSQL database:

```bash
# Basic backup command
pg_dump -U atsuser -W -F t ats > ats_backup_$(date +%Y%m%d_%H%M%S).tar

# To restore from a backup
pg_restore -U atsuser -d ats ats_backup_filename.tar
```

## CI/CD Pipeline Integration

Set up a CI/CD pipeline using GitHub Actions or AWS CodePipeline:

```yaml
# Example GitHub Actions workflow
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: your-aws-region
        
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
      
    - name: Build and push Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: ats-app
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        
    - name: Deploy to ECS
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: ats-app
        IMAGE_TAG: ${{ github.sha }}
      run: |
        aws ecs update-service --cluster your-cluster --service ats-app-service --force-new-deployment
```

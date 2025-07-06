#!/usr/bin/env python3
"""
Job Database Seeder - Creates 500+ diverse job listings
Run this script to populate your ATS with comprehensive job data
"""

import os
import sys
import random
from datetime import datetime, timedelta

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Job, User

# Comprehensive job data categories
JOB_CATEGORIES = {
    "Software Engineering": {
        "titles": [
            "Software Engineer", "Senior Software Engineer", "Lead Software Engineer",
            "Software Developer", "Full Stack Developer", "Backend Developer", 
            "Frontend Developer", "Web Developer", "Mobile App Developer",
            "Senior Full Stack Developer", "Principal Software Engineer",
            "Staff Software Engineer", "Software Architect", "Solutions Architect"
        ],
        "skills": [
            "Python", "JavaScript", "Java", "C++", "React", "Node.js", "SQL",
            "Git", "Docker", "Kubernetes", "AWS", "REST APIs", "MongoDB",
            "PostgreSQL", "Redis", "Microservices", "Agile", "TDD"
        ]
    },
    "AI/Machine Learning": {
        "titles": [
            "AI Engineer", "Machine Learning Engineer", "Senior ML Engineer",
            "Data Scientist", "Senior Data Scientist", "AI Research Scientist",
            "ML Research Engineer", "Computer Vision Engineer", "NLP Engineer",
            "Deep Learning Engineer", "MLOps Engineer", "AI Product Manager",
            "Principal Data Scientist", "Staff ML Engineer", "AI Architect"
        ],
        "skills": [
            "Python", "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
            "Jupyter", "SQL", "R", "Keras", "OpenCV", "NLTK", "spaCy",
            "AWS SageMaker", "Docker", "Kubernetes", "MLflow", "Airflow"
        ]
    },
    "Data Engineering": {
        "titles": [
            "Data Engineer", "Senior Data Engineer", "Lead Data Engineer",
            "Big Data Engineer", "Data Platform Engineer", "ETL Developer",
            "Data Pipeline Engineer", "Principal Data Engineer", "Staff Data Engineer",
            "Data Infrastructure Engineer", "Real-time Data Engineer"
        ],
        "skills": [
            "Python", "SQL", "Apache Spark", "Hadoop", "Kafka", "Airflow",
            "AWS", "GCP", "Azure", "Snowflake", "BigQuery", "Redshift",
            "Docker", "Kubernetes", "Terraform", "ETL", "Data Warehousing"
        ]
    },
    "DevOps/Platform": {
        "titles": [
            "DevOps Engineer", "Senior DevOps Engineer", "Platform Engineer",
            "Site Reliability Engineer", "Cloud Engineer", "Infrastructure Engineer",
            "SRE", "Senior SRE", "Lead Platform Engineer", "Principal DevOps Engineer",
            "Cloud Solutions Architect", "Kubernetes Engineer"
        ],
        "skills": [
            "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
            "Ansible", "Jenkins", "GitLab CI", "Prometheus", "Grafana",
            "Linux", "Bash", "Python", "Helm", "Istio", "CI/CD"
        ]
    },
    "Frontend Development": {
        "titles": [
            "Frontend Developer", "Senior Frontend Developer", "UI Developer",
            "React Developer", "Vue.js Developer", "Angular Developer",
            "JavaScript Developer", "Web Developer", "Lead Frontend Developer",
            "Principal Frontend Engineer", "Frontend Architect"
        ],
        "skills": [
            "JavaScript", "TypeScript", "React", "Vue.js", "Angular", "HTML5",
            "CSS3", "SASS", "Webpack", "Node.js", "Redux", "Next.js",
            "Tailwind CSS", "Material-UI", "Jest", "Cypress", "Figma"
        ]
    },
    "Mobile Development": {
        "titles": [
            "iOS Developer", "Android Developer", "Mobile App Developer",
            "Senior iOS Developer", "Senior Android Developer", "React Native Developer",
            "Flutter Developer", "Mobile Engineer", "Lead Mobile Developer",
            "Principal Mobile Engineer", "Mobile Architect"
        ],
        "skills": [
            "Swift", "Kotlin", "Java", "React Native", "Flutter", "Dart",
            "iOS SDK", "Android SDK", "Xcode", "Android Studio", "Firebase",
            "Core Data", "SQLite", "RESTful APIs", "GraphQL", "Git"
        ]
    },
    "Product Management": {
        "titles": [
            "Product Manager", "Senior Product Manager", "Lead Product Manager",
            "Principal Product Manager", "VP of Product", "Product Owner",
            "Technical Product Manager", "AI Product Manager", "Growth Product Manager",
            "Senior Product Owner", "Director of Product"
        ],
        "skills": [
            "Product Strategy", "User Research", "Analytics", "A/B Testing",
            "Roadmapping", "Agile", "Scrum", "JIRA", "Figma", "SQL",
            "Data Analysis", "Market Research", "Stakeholder Management"
        ]
    },
    "Design": {
        "titles": [
            "UI/UX Designer", "Product Designer", "Senior UX Designer",
            "Visual Designer", "Interaction Designer", "User Researcher",
            "Design Lead", "Principal Designer", "Creative Director",
            "UI Designer", "UX Researcher", "Design System Designer"
        ],
        "skills": [
            "Figma", "Sketch", "Adobe Creative Suite", "Prototyping", "Wireframing",
            "User Research", "Usability Testing", "Design Systems", "HTML/CSS",
            "InVision", "Zeplin", "Principle", "Framer", "After Effects"
        ]
    },
    "Cybersecurity": {
        "titles": [
            "Security Engineer", "Cybersecurity Analyst", "Information Security Analyst",
            "Senior Security Engineer", "Security Architect", "Penetration Tester",
            "Security Consultant", "CISO", "Security Researcher", "SOC Analyst",
            "Principal Security Engineer", "Lead Security Architect"
        ],
        "skills": [
            "Network Security", "Vulnerability Assessment", "Penetration Testing",
            "SIEM", "Incident Response", "Risk Assessment", "Compliance",
            "Python", "Bash", "Wireshark", "Metasploit", "Nessus", "Burp Suite"
        ]
    },
    "Marketing/Growth": {
        "titles": [
            "Digital Marketing Manager", "Growth Marketing Manager", "SEO Specialist",
            "Content Marketing Manager", "Social Media Manager", "Marketing Analyst",
            "Performance Marketing Manager", "Email Marketing Specialist",
            "Brand Manager", "Marketing Director", "Head of Growth"
        ],
        "skills": [
            "Google Analytics", "SEO", "SEM", "Social Media Marketing",
            "Content Marketing", "Email Marketing", "A/B Testing",
            "Marketing Automation", "CRM", "SQL", "Data Analysis"
        ]
    }
}

COMPANIES = [
    "Google", "Apple", "Microsoft", "Amazon", "Meta", "Netflix", "Tesla", "Uber",
    "Airbnb", "Spotify", "Slack", "Zoom", "Dropbox", "Salesforce", "Oracle",
    "IBM", "Intel", "NVIDIA", "Adobe", "Atlassian", "GitHub", "GitLab",
    "TechCorp", "InnovateLabs", "DataFlow Inc", "CloudVision", "AI Solutions",
    "NextGen Tech", "Digital Dynamics", "Future Systems", "Quantum Labs",
    "CyberShield", "SmartData", "CodeCraft", "TechNova", "ByteDance",
    "Palantir", "Coinbase", "Stripe", "Square", "PayPal", "Twilio",
    "Shopify", "Datadog", "Snowflake", "MongoDB", "Redis Labs", "Elastic",
    "HashiCorp", "Docker", "JetBrains", "Unity", "Epic Games", "Roblox",
    "Figma", "Notion", "Airtable", "Zapier", "Canva", "Discord"
]

LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Boston, MA", "Los Angeles, CA", "Chicago, IL", "Denver, CO",
    "Atlanta, GA", "Miami, FL", "Portland, OR", "Phoenix, AZ",
    "Remote", "Remote (US)", "Remote (Global)", "Hybrid - San Francisco",
    "Hybrid - New York", "Hybrid - Seattle", "London, UK", "Toronto, Canada",
    "Berlin, Germany", "Amsterdam, Netherlands", "Singapore", "Tokyo, Japan",
    "Sydney, Australia", "Tel Aviv, Israel", "Bangalore, India", "Dublin, Ireland"
]

EMPLOYMENT_TYPES = ["full-time", "part-time", "contract", "internship"]

def generate_job_description(title, category, skills):
    """Generate a realistic job description"""
    base_descriptions = {
        "Software Engineering": [
            "Join our engineering team to build scalable, high-performance applications that serve millions of users worldwide.",
            "We're looking for a passionate developer to help architect and implement cutting-edge solutions.",
            "Build robust, maintainable code and collaborate with cross-functional teams to deliver exceptional products.",
            "Work on challenging technical problems and contribute to our platform that powers modern businesses."
        ],
        "AI/Machine Learning": [
            "Drive AI innovation by developing machine learning models that solve real-world problems at scale.",
            "Join our AI research team to push the boundaries of artificial intelligence and machine learning.",
            "Build and deploy ML models that power intelligent features across our product ecosystem.",
            "Work with large datasets to extract insights and build predictive models that drive business value."
        ],
        "Data Engineering": [
            "Design and build data infrastructure that processes petabytes of data reliably and efficiently.",
            "Create robust data pipelines that enable data-driven decision making across the organization.",
            "Build scalable data platforms that support both batch and real-time processing requirements.",
            "Work with big data technologies to solve complex data processing challenges."
        ],
        "DevOps/Platform": [
            "Build and maintain cloud infrastructure that supports rapid scaling and high availability.",
            "Design automation tools and processes that enable efficient software delivery and operations.",
            "Ensure system reliability and performance while implementing best practices for security and monitoring.",
            "Work with development teams to streamline deployment processes and improve developer productivity."
        ],
        "Frontend Development": [
            "Create beautiful, responsive user interfaces that provide exceptional user experiences.",
            "Build modern web applications using the latest frontend technologies and frameworks.",
            "Collaborate with designers and backend engineers to implement pixel-perfect, performant UIs.",
            "Optimize applications for maximum speed and scalability across various devices and browsers."
        ],
        "Mobile Development": [
            "Develop native mobile applications that delight users and drive engagement.",
            "Build cross-platform mobile solutions that work seamlessly across iOS and Android.",
            "Implement mobile-first designs and ensure optimal performance on various devices.",
            "Work with product teams to translate requirements into intuitive mobile experiences."
        ],
        "Product Management": [
            "Drive product strategy and roadmap for features that impact millions of users.",
            "Work closely with engineering, design, and business teams to deliver successful products.",
            "Analyze user behavior and market trends to identify opportunities for product growth.",
            "Define product requirements and coordinate cross-functional teams to execute on the vision."
        ],
        "Design": [
            "Create intuitive, user-centered designs that solve complex user problems.",
            "Collaborate with product and engineering teams to bring innovative design solutions to life.",
            "Conduct user research and usability testing to inform design decisions.",
            "Build and maintain design systems that ensure consistency across all products."
        ],
        "Cybersecurity": [
            "Protect our systems and data by implementing robust security measures and protocols.",
            "Conduct security assessments and penetration testing to identify vulnerabilities.",
            "Respond to security incidents and develop strategies to prevent future threats.",
            "Work with development teams to integrate security best practices into the development lifecycle."
        ],
        "Marketing/Growth": [
            "Drive user acquisition and engagement through data-driven marketing strategies.",
            "Develop and execute marketing campaigns that increase brand awareness and conversion.",
            "Analyze marketing performance and optimize campaigns for maximum ROI.",
            "Work with product and sales teams to develop go-to-market strategies for new features."
        ]
    }
    
    descriptions = base_descriptions.get(category, base_descriptions["Software Engineering"])
    base_desc = random.choice(descriptions)
    
    responsibilities = [
        f"• Develop and maintain {random.choice(['scalable', 'robust', 'high-performance', 'innovative'])} solutions",
        f"• Collaborate with cross-functional teams including product, design, and engineering",
        f"• Participate in code reviews and contribute to technical documentation",
        f"• Mentor junior team members and contribute to team growth",
        f"• Stay current with industry trends and emerging technologies"
    ]
    
    qualifications = [
        f"• {random.randint(2, 8)}+ years of experience in {category.lower()}",
        f"• Strong proficiency in {', '.join(random.sample(skills, min(3, len(skills))))}",
        f"• Experience with {random.choice(['agile methodologies', 'CI/CD pipelines', 'cloud platforms', 'distributed systems'])}",
        "• " + random.choice(['Bachelor\'s', 'Master\'s']) + " degree in Computer Science, Engineering, or related field",
        f"• Excellent communication and problem-solving skills"
    ]
    
    benefits = [
        "• Competitive salary and equity package",
        "• Comprehensive health, dental, and vision insurance",
        "• Flexible work arrangements and unlimited PTO",
        "• $3000 annual learning and development budget",
        "• Top-tier equipment and home office setup",
        "• Catered meals and snacks in office locations"
    ]
    
    description = f"""{base_desc}

**Responsibilities:**
{chr(10).join(responsibilities)}

**Qualifications:**
{chr(10).join(qualifications)}

**Benefits:**
{chr(10).join(benefits)}

Join our team and help us build the future of technology while growing your career in an inclusive, innovative environment."""
    
    return description

def create_jobs_data():
    """Generate comprehensive job data"""
    jobs_data = []
    
    for category, data in JOB_CATEGORIES.items():
        titles = data["titles"]
        skills = data["skills"]
        
        # Create multiple jobs for each title to reach 500+ total
        jobs_per_title = max(3, 50 // len(titles))  # Ensure good distribution
        
        for title in titles:
            for _ in range(jobs_per_title):
                company = random.choice(COMPANIES)
                location = random.choice(LOCATIONS)
                employment_type = random.choice(EMPLOYMENT_TYPES)
                
                # Generate salary ranges based on seniority and category
                if "Senior" in title or "Lead" in title or "Principal" in title:
                    salary_min = random.randint(120000, 180000)
                    salary_max = salary_min + random.randint(30000, 70000)
                elif "Staff" in title or "Director" in title or "VP" in title:
                    salary_min = random.randint(180000, 250000)
                    salary_max = salary_min + random.randint(50000, 100000)
                elif employment_type == "internship":
                    salary_min = random.randint(4000, 8000)  # Monthly
                    salary_max = salary_min + random.randint(1000, 2000)
                elif employment_type == "contract":
                    salary_min = random.randint(80, 150)  # Hourly
                    salary_max = salary_min + random.randint(20, 50)
                else:
                    salary_min = random.randint(80000, 140000)
                    salary_max = salary_min + random.randint(20000, 50000)
                
                # Select relevant skills for requirements
                selected_skills = random.sample(skills, min(random.randint(4, 8), len(skills)))
                
                job_data = {
                    "title": title,
                    "company": company,
                    "description": generate_job_description(title, category, selected_skills),
                    "requirements": selected_skills,
                    "location": location,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "employment_type": employment_type,
                    "category": category
                }
                
                jobs_data.append(job_data)
    
    return jobs_data

def seed_jobs():
    """Seed the database with job data"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Starting job database seeding...")
        
        # Check if we already have jobs
        existing_jobs = Job.query.count()
        if existing_jobs > 100:
            print(f"Database already has {existing_jobs} jobs. Skipping seeding.")
            print("Delete existing jobs first if you want to reseed.")
            return
        
        # Create a default HR user if none exists
        hr_user = User.query.filter_by(role='hr').first()
        if not hr_user:
            print("Creating default HR user for job creation...")
            hr_user = User(
                name="System Admin",
                email="admin@ats.com",
                role="hr"
            )
            hr_user.set_password("admin123")  # You should change this
            db.session.add(hr_user)
            db.session.commit()
            print(f"✅ Created HR user with ID: {hr_user.id}")
        
        # Generate job data
        print("📊 Generating comprehensive job data...")
        jobs_data = create_jobs_data()
        print(f"Generated {len(jobs_data)} job listings")
        
        # Create job records
        print("💾 Inserting jobs into database...")
        jobs_created = 0
        
        for job_data in jobs_data:
            try:
                job = Job(
                    title=job_data["title"],
                    company=job_data["company"],
                    description=job_data["description"],
                    requirements=job_data["requirements"],
                    location=job_data["location"],
                    salary_min=job_data["salary_min"],
                    salary_max=job_data["salary_max"],
                    employment_type=job_data["employment_type"],
                    is_active=True,
                    created_by=hr_user.id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
                )
                
                db.session.add(job)
                jobs_created += 1
                
                # Commit in batches for better performance
                if jobs_created % 50 == 0:
                    db.session.commit()
                    print(f"✅ Created {jobs_created} jobs...")
                    
            except Exception as e:
                print(f"❌ Error creating job: {e}")
                db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            print(f"\n🎉 Successfully created {jobs_created} jobs!")
            
            # Print summary statistics
            print("\n📈 Job Creation Summary:")
            for category in JOB_CATEGORIES.keys():
                count = Job.query.filter(Job.description.contains(category)).count()
                print(f"  • {category}: {count} jobs")
            
            print(f"\n📊 Total jobs in database: {Job.query.count()}")
            print("🚀 Job seeding completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during final commit: {e}")
            db.session.rollback()

if __name__ == "__main__":
    seed_jobs()

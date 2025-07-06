import os
import json
from mistralai import Mistral
from config import Config
import PyPDF2

class MistralOCRService:
    """
    Service class for Mistral AI resume parsing
    
    Note: Updated to use PyPDF2 for text extraction + Mistral for structuring
    due to API issues with the file upload/OCR endpoints (Status 422 errors).
    This provides a reliable fallback approach.
    """
    
    def __init__(self):
        self.client = Mistral(api_key=Config.MISTRAL_API_KEY)
    
    def parse_resume(self, file_path):
        """
        Parse resume using fallback method with PyPDF2 + Mistral AI
        
        Args:
            file_path (str): Path to the resume file
            
        Returns:
            dict: Structured resume data
        """
        try:
            # First try to extract text using PyPDF2 as fallback
            print("🔄 Extracting text from PDF using PyPDF2...")
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                raw_text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    raw_text += page.extract_text() + "\n"
            
            if not raw_text.strip():
                return {
                    "success": False,
                    "error": "Could not extract text from PDF"
                }
            
            print(f"✅ Extracted {len(raw_text)} characters from PDF")
            
            # Now use Mistral to structure the extracted text
            print("🔄 Structuring extracted text with Mistral AI...")
            
            messages = [
                {
                    "role": "user",
                    "content": f"""
                    Please analyze this resume text and extract structured information in JSON format:
                    
                    {{
                        "personal_info": {{
                            "name": "Full name",
                            "email": "Email address",
                            "phone": "Phone number", 
                            "location": "Address/Location"
                        }},
                        "summary": "Professional summary or objective",
                        "skills": ["skill1", "skill2", "skill3"],
                        "experience": [
                            {{
                                "company": "Company name",
                                "position": "Job title",
                                "duration": "Employment duration",
                                "description": "Job description and achievements"
                            }}
                        ],
                        "education": [
                            {{
                                "institution": "School/University name",
                                "degree": "Degree type and field",
                                "graduation_year": "Year",
                                "gpa": "GPA if available"
                            }}
                        ],
                        "certifications": ["cert1", "cert2"],
                        "languages": ["language1", "language2"]
                    }}
                    
                    Resume Text:
                    {raw_text}
                    
                    Extract all available information and return only valid JSON.
                    """
                }
            ]
            
            chat_response = self.client.chat.complete(
                model="mistral-small-latest",
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            # Parse the structured response
            structured_data = json.loads(chat_response.choices[0].message.content)
            
            print("✅ Successfully structured resume data")
            
            return {
                "success": True,
                "structured_data": structured_data,
                "raw_text": raw_text.strip()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_match_score(self, resume_data, job_requirements):
        """
        Calculate match score between resume and job requirements
        
        Args:
            resume_data (dict): Parsed resume data
            job_requirements (list): List of job requirements
            
        Returns:
            float: Match score between 0 and 1
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": f"""
                    Analyze the match between this resume and job requirements.
                    
                    Resume Data:
                    {json.dumps(resume_data, indent=2)}
                    
                    Job Requirements:
                    {json.dumps(job_requirements, indent=2)}
                    
                    Calculate a match score from 0 to 1 based on:
                    - Skills alignment
                    - Experience relevance
                    - Education requirements
                    - Overall fit
                    
                    Return only a JSON object with:
                    {{
                        "match_score": 0.85,
                        "explanation": "Brief explanation of the score",
                        "strengths": ["strength1", "strength2"],
                        "gaps": ["gap1", "gap2"]
                    }}
                    """
                }
            ]
            
            response = self.client.chat.complete(
                model="mistral-small-latest",
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {
                "match_score": 0.0,
                "explanation": f"Error calculating match: {str(e)}",
                "strengths": [],
                "gaps": []
            }

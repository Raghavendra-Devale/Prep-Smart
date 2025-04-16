import os
import openai
from pydub import AudioSegment
import speech_recognition as sr
from typing import Dict, Any
import json

# Initialize OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

# Sample answers for different questions
SAMPLE_ANSWERS = {
    # HR Questions
    1: "I am a [your role] with [X] years of experience in [industry/field]. I have expertise in [key skills] and have worked on [notable projects/achievements]. I'm passionate about [relevant interests] and am looking to [career goals].",
    2: "My strengths include [list 2-3 key strengths with examples]. As for weaknesses, I'm working on [mention a genuine area of improvement] and have taken steps like [specific actions] to address it.",
    3: "I want to work here because [company name] is known for [specific company strengths/values]. I'm particularly interested in [specific aspects of the company] and believe my skills in [relevant skills] align well with the role.",
    4: "In a previous role, I dealt with a difficult coworker by [specific approach]. I focused on [key actions taken] and the outcome was [positive result]. This taught me the importance of [key learning].",
    5: "My career goals include [specific short-term goals] and [long-term aspirations]. I plan to achieve these through [specific steps/strategies].",
    6: "A significant failure I experienced was [describe situation]. From this, I learned [key lessons] and implemented [specific changes] to prevent similar issues in the future.",
    
    # Technical Questions
    7: "Closures in JavaScript are functions that have access to variables in their outer scope, even after the outer function has returned. They're useful for [specific use cases] and help maintain [specific benefits].",
    8: "To reverse a linked list, you need to [algorithm steps]. The time complexity is O(n) and space complexity is O(1). Here's how it works: [explanation]",
    9: "SQL databases are [characteristics] while NoSQL databases are [characteristics]. The main differences are [key differences] and each is better suited for [specific use cases].",
    10: "Virtual memory works by [explanation]. The key components are [components] and it provides benefits like [benefits].",
    11: "Multithreading allows [explanation]. The benefits include [benefits] and it's particularly useful for [use cases].",
    12: "Dynamic programming is [explanation]. It's best used when [conditions] and involves [key steps]. The main advantages are [advantages]."
}

def convert_audio_to_text(audio_file_path: str) -> str:
    """Convert audio file to text using speech recognition."""
    recognizer = sr.Recognizer()
    
    # Convert webm to wav if needed
    audio = AudioSegment.from_file(audio_file_path)
    wav_path = audio_file_path.replace('.webm', '.wav')
    audio.export(wav_path, format='wav')
    
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError:
            return "Could not request results"
        finally:
            # Clean up temporary wav file
            if os.path.exists(wav_path):
                os.remove(wav_path)

def compare_answers(user_answer: str, question_id: int) -> Dict[str, Any]:
    """Compare user's answer with sample answer using OpenAI's API."""
    sample_answer = SAMPLE_ANSWERS.get(question_id, "")
    
    if not sample_answer:
        return {
            "success": False,
            "message": "No sample answer found for this question"
        }
    
    prompt = f"""
    Compare the following interview answer with a sample answer and provide:
    1. Accuracy percentage (0-100)
    2. Key points covered
    3. Missing points
    4. Areas for improvement
    
    Sample Answer: {sample_answer}
    User's Answer: {user_answer}
    
    Provide the response in JSON format with the following structure:
    {{
        "accuracy": number,
        "key_points_covered": [string],
        "missing_points": [string],
        "improvement_areas": [string]
    }}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interviewer analyzing interview responses."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error comparing answers: {str(e)}"
        }

def analyze_interview_response(audio_file_path: str, question_id: int) -> Dict[str, Any]:
    """Main function to analyze interview response."""
    # Convert audio to text
    user_answer = convert_audio_to_text(audio_file_path)
    
    if user_answer == "Could not understand audio":
        return {
            "success": False,
            "message": "Could not understand the audio recording"
        }
    
    # Compare answers
    comparison_result = compare_answers(user_answer, question_id)
    
    if not comparison_result["success"]:
        return comparison_result
    
    # Add additional analysis
    result = comparison_result["result"]
    result["transcribed_text"] = user_answer
    
    return {
        "success": True,
        "result": result
    } 
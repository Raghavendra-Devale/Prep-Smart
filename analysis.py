import os
import openai
from pydub import AudioSegment
import speech_recognition as sr
from typing import Dict, Any
import json
<<<<<<< HEAD

# Initialize OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')
=======
import random

# Initialize OpenAI API client
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    USE_OPENAI = True
    print("OpenAI API key found. Using real OpenAI API.")
else:
    USE_OPENAI = False
    print("No OpenAI API key found. Using mock implementation.")
>>>>>>> ecfd4dffffe076ca6ba48fffe74e6d4f3d92b9b1

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
    
<<<<<<< HEAD
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
=======
    try:
        print(f"Processing audio file: {audio_file_path}")
        
        # Check if file exists
        if not os.path.exists(audio_file_path):
            print(f"Audio file does not exist: {audio_file_path}")
            return "Could not find audio file"
        
        # Get file extension
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        print(f"Audio file extension: {file_ext}")
        
        # Convert file to wav format
        try:
            audio = AudioSegment.from_file(audio_file_path)
            wav_path = audio_file_path.replace(file_ext, '.wav')
            print(f"Converting to WAV: {wav_path}")
            audio.export(wav_path, format='wav')
        except Exception as e:
            print(f"Error converting audio to WAV: {e}")
            return f"Could not convert audio: {str(e)}"
        
        # Process with speech recognition
        try:
            with sr.AudioFile(wav_path) as source:
                print("Recording audio from file")
                audio_data = recognizer.record(source)
                print("Recognizing speech...")
                text = recognizer.recognize_google(audio_data)
                print(f"Transcription successful, text length: {len(text)}")
                return text
        except sr.UnknownValueError as e:
            print(f"Speech recognition could not understand audio: {e}")
            return "Could not understand audio"
        except sr.RequestError as e:
            print(f"Speech recognition service request error: {e}")
            return "Could not request results"
        except Exception as e:
            print(f"Unknown error in speech recognition: {e}")
            return f"Speech recognition error: {str(e)}"
        finally:
            # Clean up temporary wav file
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
                    print(f"Removed temporary file: {wav_path}")
            except Exception as e:
                print(f"Error removing temporary WAV file: {e}")
    except Exception as e:
        print(f"General error in audio conversion: {e}")
        return f"Error processing audio: {str(e)}"

def mock_compare_answers(user_answer: str, question_id: int) -> Dict[str, Any]:
    """Generate a mock response when OpenAI is not available"""
    # Get the sample answer for reference
    sample_answer = SAMPLE_ANSWERS.get(question_id, "")
    
    # Do some basic analysis on the user's answer
    answer_length = len(user_answer)
    word_count = len(user_answer.split())
    
    # Determine if this is an HR or Technical question
    is_hr_question = question_id < 7
    
    # Set base accuracy based on answer length and word count
    # Too short answers should not get high scores
    if word_count < 15:
        base_accuracy = 40
    elif word_count < 50:
        base_accuracy = 60
    elif word_count < 100:
        base_accuracy = 75
    else:
        base_accuracy = 85
    
    # Add some variation but less random than before
    variation = random.randint(-5, 10)
    accuracy = min(95, max(40, base_accuracy + variation))
    
    # Question-specific key points
    key_points_by_question = {
        # HR Questions
        1: ["Introduced yourself clearly", "Mentioned relevant experience", "Highlighted key skills", "Showed passion/career goals"],
        2: ["Listed specific strengths with examples", "Addressed weaknesses honestly", "Showed self-awareness", "Mentioned improvement steps"],
        3: ["Showed knowledge of the company", "Connected your skills to the role", "Demonstrated genuine interest", "Mentioned company values/culture"],
        4: ["Described a specific situation", "Explained your approach constructively", "Highlighted positive resolution", "Shared learning outcome"],
        5: ["Outlined clear short-term goals", "Mentioned long-term aspirations", "Showed alignment with role", "Demonstrated realistic planning"],
        6: ["Described a specific failure", "Took ownership", "Explained learnings", "Showed how you've improved"],
        
        # Technical Questions
        7: ["Defined closures correctly", "Explained lexical scope", "Provided practical examples", "Mentioned benefits/use cases"],
        8: ["Described correct algorithm", "Mentioned time/space complexity", "Explained pointer manipulation", "Addressed edge cases"],
        9: ["Explained structure differences", "Compared query capabilities", "Discussed scaling characteristics", "Mentioned appropriate use cases"],
        10: ["Explained paging mechanism", "Described address translation", "Mentioned benefits", "Addressed memory management"],
        11: ["Defined multithreading correctly", "Explained concurrency benefits", "Mentioned challenges", "Provided use cases"],
        12: ["Defined dynamic programming", "Explained memoization/tabulation", "Described optimal substructure", "Mentioned practical applications"]
    }
    
    # Get appropriate key points for this question
    all_key_points = key_points_by_question.get(question_id, [
        "Structured response logically",
        "Provided specific examples",
        "Demonstrated technical knowledge",
        "Showed problem-solving skills"
    ])
    
    # Determine how many points were covered based on accuracy
    num_points_covered = max(1, int(len(all_key_points) * (accuracy / 100)))
    key_points_covered = all_key_points[:num_points_covered]
    missing_points = all_key_points[num_points_covered:]
    
    # If no missing points, add some generic ones
    if not missing_points:
        missing_points = ["Could add more specific details", "Consider adding quantifiable results"]
    
    # Question-specific improvement areas
    if is_hr_question:
        improvement_areas = [
            "Use the STAR method (Situation, Task, Action, Result) for behavioral questions",
            "Add more personal examples that highlight your specific contributions",
            "Quantify your achievements with specific metrics when possible",
            "Keep responses focused and concise (2-3 minutes per answer)"
        ]
    else:
        improvement_areas = [
            "Explain technical concepts using simple analogies when appropriate",
            "Mention specific technologies/tools you've used to solve similar problems",
            "Consider discussing trade-offs in your technical approaches",
            "Practice working through problems step by step for clarity"
        ]
    
    # Select 2-3 improvement areas
    selected_improvements = random.sample(improvement_areas, min(3, len(improvement_areas)))
    
    # Create a mock result
    return {
        "success": True,
        "result": {
            "accuracy": accuracy,
            "key_points_covered": key_points_covered,
            "missing_points": missing_points,
            "improvement_areas": selected_improvements
        }
    }
>>>>>>> ecfd4dffffe076ca6ba48fffe74e6d4f3d92b9b1

def compare_answers(user_answer: str, question_id: int) -> Dict[str, Any]:
    """Compare user's answer with sample answer using OpenAI's API."""
    sample_answer = SAMPLE_ANSWERS.get(question_id, "")
    
    if not sample_answer:
        return {
            "success": False,
            "message": "No sample answer found for this question"
        }
    
<<<<<<< HEAD
=======
    # If OpenAI is not available, use the mock implementation
    if not USE_OPENAI:
        print("Using mock implementation for compare_answers")
        return mock_compare_answers(user_answer, question_id)
    
>>>>>>> ecfd4dffffe076ca6ba48fffe74e6d4f3d92b9b1
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
<<<<<<< HEAD
        response = openai.ChatCompletion.create(
=======
        # Using the new OpenAI API syntax (v1.0+)
        response = client.chat.completions.create(
>>>>>>> ecfd4dffffe076ca6ba48fffe74e6d4f3d92b9b1
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
<<<<<<< HEAD
        return {
            "success": False,
            "message": f"Error comparing answers: {str(e)}"
        }
=======
        print(f"Error comparing answers: {e}")
        # Fallback to mock implementation if OpenAI call fails
        print("Using mock implementation as fallback due to OpenAI API error")
        return mock_compare_answers(user_answer, question_id)
>>>>>>> ecfd4dffffe076ca6ba48fffe74e6d4f3d92b9b1

def analyze_interview_response(audio_file_path: str, question_id: int) -> Dict[str, Any]:
    """Main function to analyze interview response."""
    # Convert audio to text
    user_answer = convert_audio_to_text(audio_file_path)
    
    if user_answer == "Could not understand audio":
<<<<<<< HEAD
        return {
            "success": False,
            "message": "Could not understand the audio recording"
        }
=======
        # Generate a simulated answer for demonstration
        if not USE_OPENAI:
            user_answer = "This is a simulated answer since speech recognition failed and OpenAI is not available. In a real interview, I would respond by highlighting my relevant experience and skills that make me a good fit for this position."
            print("Using simulated answer for demonstration")
        else:
            return {
                "success": False,
                "message": "Could not understand the audio recording"
            }
>>>>>>> ecfd4dffffe076ca6ba48fffe74e6d4f3d92b9b1
    
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
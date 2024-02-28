import threading
from dotenv import load_dotenv
import os
import assemblyai as aai
from pathlib import Path
import sys
import time
from os.path import dirname

# Constants
maxWordsPerFile = 4000
speaker_label_words = 1

# Global variables
stop_loading = threading.Event()
isExecutable = getattr(sys, 'frozen', False) # Check if the application is running as an executable

def introduction():
    clear_terminal()
    time.sleep(1)
    print("Welcome!")
    time.sleep(2)
    clear_terminal()
    time.sleep(1)

def load_api_key():
    env_path = None
    # Get the path of the .env file
    if isExecutable:
        # The application is frozen (running in a PyInstaller bundle)
        env_path = os.path.join(sys._MEIPASS, '.env')
    else:
        # The application is not frozen (running in a normal Python environment)
        env_path = '../.env'
    load_dotenv(dotenv_path=env_path)
    apiKey = os.getenv('ASSEMBLYAI_API_KEY')

    # Your API key
    aai.settings.api_key = apiKey
    if not aai.settings.api_key:
        raise ValueError("ASSEMBLYAI_API_KEY not set.")

def get_source_file_name():
    # Get the name of the recording file from the user via drag and drop into the terminal
    print("Drag and drop the recording file here and press enter:")
    sourceFileName = input().replace("\\ ", " ").strip()
    if not Path(sourceFileName).exists():
        raise FileNotFoundError(f"File {sourceFileName} does not exist.")
    return sourceFileName

def processing_animation():
    # Print a processing animation
    print()
    while not stop_loading.is_set():
        print("\rProcessing your recording", end="")
        time.sleep(0.5)
        for i in range(3):
            print(".", end="")
            sys.stdout.flush()
            time.sleep(0.5)
        print("\rProcessing your recording   ", end="")  # overwrite the line with spaces
    print("\rProcessing your recording...")
    print("Processing complete!        \n")
    time.sleep(2)
    stop_loading.clear() # Unblock the main thread

def transcribe_file(sourceFileName):
    # Start the processing animation
    threading.Thread(target=processing_animation).start()
    
    # Create a transcription config with speaker labels enabled
    config = aai.TranscriptionConfig(speaker_labels=True)
    transcriber = aai.Transcriber() 
    try:
        transcript = transcriber.transcribe(sourceFileName, config=config)
        stop_loading.set()
        while stop_loading.is_set(): # Wait for the processing animation to finish
            time.sleep(0.1)
    except Exception as e:
        raise RuntimeError(f"Transcription failed with error {e}")
    return transcript

def check_utterances(transcript):
    # First pass to check if any of the utterances are longer than the wordsPerFile
    wordTotal = 0
    for utterance in transcript.utterances: # Iterate through the utterances
        wordCount = len(utterance.words)
        if (wordCount > maxWordsPerFile): # If the word count exceeds the limit
            raise ValueError(f"A single utterance is longer than {maxWordsPerFile} words. Please split the file manually.")
        wordTotal += wordCount + speaker_label_words
    print(f"Transcript contains {wordTotal} words.\n")
    time.sleep(2)

def identify_speakers(transcript):
    # Identify the speakers
    speakers = set()
    for utterance in transcript.utterances:
        speakers.add(utterance.speaker)
    return speakers

def identify_names_of_speakers(transcript):
    # Identify the names of the speakers
    print("Please identify the speakers in the interview.\n")
    time.sleep(2)
    print("Enter the name of the speaker when prompted. If not sure, press enter for another line.\n")
    time.sleep(5)
    speakerLabelsToIdentify = identify_speakers(transcript)
    speakerNameMap = {}
    for utterance in transcript.utterances:
        if not speakerLabelsToIdentify:
            break
        if utterance.speaker in speakerLabelsToIdentify:
            realName = input(f"Who said:\n\"{utterance.text}\"\n")
            if realName:
                speakerNameMap[utterance.speaker] = realName
                speakerLabelsToIdentify.remove(utterance.speaker)
            print()
    return speakerNameMap

def replace_speaker_labels_with_names(transcript):
    # Replace the speaker labels with the names
    speakerNameMap = identify_names_of_speakers(transcript)
    for utterance in transcript.utterances:
        if utterance.speaker in speakerNameMap:
            utterance.speaker = speakerNameMap[utterance.speaker]
    return transcript

def get_current_dir():
    # Get the current directory
    if isExecutable:
        # The application is frozen (running in a PyInstaller bundle)
        return dirname(sys.executable) # Assume executable is in the root directory
    else:
        # The application is not frozen (running in a normal Python environment)
        return dirname(dirname(__file__)) # Go up one level from src

def write_transcript_to_files(transcript, interviewName):
    # Second pass to write the transcript to files. Each file will contain at most maxWordsPerFile words
    fileCount = 1
    wordTotal = 0
    filesWritten = []
    currentDir = get_current_dir()
    scriptPath = Path(currentDir) / f"Scripts/{interviewName}_{fileCount}.txt"
    f = open(scriptPath, 'w')
    for utterance in transcript.utterances:
        wordCount = len(utterance.words)
        if wordTotal + wordCount > maxWordsPerFile: # If the new word count would exceed the limit
            if f:
                f.close()
                filesWritten.append(str(scriptPath))
            fileCount += 1
            scriptPath = Path(currentDir) / f"Scripts/{interviewName}_{fileCount}.txt"
            f = open(scriptPath, 'w')
            wordTotal = 0
        f.write(f"{utterance.speaker}: {utterance.text}\n")
        wordTotal += wordCount + speaker_label_words # +1 for the speaker label
    f.close()
    filesWritten.append(str(scriptPath))
    return filesWritten

def printFiles(filesWritten):
    print("Transcript has been written to the following files:")
    count = 1
    for fileName in filesWritten:
        print(f"{count}: {fileName}")
        count += 1

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def prompt_repeat():
    print("\nWould you like to transcribe another recording? (yes/no)")
    response = input().lower()
    while response not in ["yes", "no", "y", "n"]:
        print("Invalid response. Please enter 'yes' or 'no'.")
        response = input().lower()
    if response == "yes" or response == "y":
        main()
    else:
        print("\nOkay! You may close this window now.")
        while True:
            input()

def main():
    introduction()
    load_api_key() # Load the API keys (for AssemblyAI)
    sourceFileName = get_source_file_name() # Get the name of the source file from the user
    interviewName = Path(sourceFileName).stem # Get the name of the interview for the output files
    transcript = transcribe_file(sourceFileName) # Transcribe the file via the AssemblyAI API
    check_utterances(transcript) # Check if any utterances are too long
    transcriptWithNames = replace_speaker_labels_with_names(transcript) # Replace the speaker labels with the names
    filesWritten = write_transcript_to_files(transcriptWithNames, interviewName) # Write the transcript to files, splitting by maxWordsPerFile
    printFiles(filesWritten) # Print the names of the files that the transcript has been written to
    prompt_repeat() # Ask the user if they would like to transcribe another recording

if __name__ == "__main__":
    main()
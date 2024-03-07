import threading
from dotenv import load_dotenv
import os
import assemblyai as aai
from pathlib import Path
import sys
import time
from os.path import dirname
from tkinter import filedialog
from openai import OpenAI

# Constants
maxWordsPerFile = 4000
speaker_label_words = 1

# Global variables
stop_loading = threading.Event()
isExecutable = getattr(sys, 'frozen', False) # Check if the application is running as an executable

# OpenAI Client
chatGptClient = None

def introduction():
    clear_terminal()
    time.sleep(1)
    print("Welcome!")
    time.sleep(2)
    clear_terminal()
    time.sleep(1)

def load_api_keys():
    env_path = None
    # Get the path of the .env file
    if isExecutable:
        # The application is frozen (running in a PyInstaller bundle)
        env_path = os.path.join(sys._MEIPASS, '.env')
    else:
        # The application is not frozen (running in a normal Python environment)
        env_path = '../.env'
    load_dotenv(dotenv_path=env_path)

    # Set AssemblyAI API key
    assemblyApiKey = os.getenv('ASSEMBLYAI_API_KEY')
    aai.settings.api_key = assemblyApiKey
    if not aai.settings.api_key:
        raise ValueError("ASSEMBLYAI_API_KEY not set.")
    
    # Set OpenAI API key
    openAiApiKey = os.getenv('OPENAI_API_KEY')
    if not openAiApiKey:
        raise ValueError("OPENAI_API_KEY not set.")
    global chatGptClient
    chatGptClient = OpenAI(api_key=openAiApiKey)
    
def get_valid_file_types():
    return (".3ga", ".webm", ".8svx", ".mts", ".m2ts", ".ts", ".aac", ".mov", ".ac3", ".mp2", ".aif", ".mp4", ".m4p", ".m4v", ".aiff", ".mxf", ".alac", ".amr", ".ape", ".au", ".dss", ".flac", ".flv", ".m4a", ".m4b", ".m4p", ".m4r", ".mp3", ".mpga", ".ogg, .oga, .mogg", ".opus", ".qcp", ".tta", ".voc", ".wav", ".wma", ".wv")

def get_source_file_name():
    # Get the name of the recording file from the user via drag and drop into the terminal
    sourceFileName = ""
    while sourceFileName == "":
        print("Drag and drop the recording file here and press enter:")
        inputFileName = input().replace("\\ ", " ").strip()
        print()
        if not os.path.exists(inputFileName):
            print("File not found. Please try again.\n")
            time.sleep(1)
        elif not inputFileName.lower().endswith(get_valid_file_types()):
            print("File must be a supported audio or video type. See www.assemblyai.com for details\n")
            time.sleep(2)
            print("Please try again\n")
            time.sleep(1)
        else:
            sourceFileName = inputFileName
    if not Path(sourceFileName).exists():
        raise FileNotFoundError(f"File {sourceFileName} does not exist.")
    return sourceFileName

def processing_animation():
    # Print a processing animation
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
    while True:
        for utterance in transcript.utterances:
            if not speakerLabelsToIdentify:
                return speakerNameMap
            if utterance.speaker in speakerLabelsToIdentify:
                realName = input(f"Who said:\n\"{utterance.text}\"\n")
                if realName:
                    speakerNameMap[utterance.speaker] = realName
                    speakerLabelsToIdentify.remove(utterance.speaker)
                print()

def replace_speaker_labels_with_names(transcript):
    # Replace the speaker labels with the names
    speakerNameMap = identify_names_of_speakers(transcript)
    for utterance in transcript.utterances:
        if utterance.speaker in speakerNameMap:
            utterance.speaker = speakerNameMap[utterance.speaker]
    return transcript

# Dictionary of numbers to strings
def filePrompts(number):
    return {
        1: "Please select a path",
        2: "I know there's a cancel button but please ignore that. Select a path.",
        3: "What did I just say? Please select a path and DON'T press cancel",
        4: "... Let's try this again. SELECT. A. PATH.",
        5: "Am I a joke to you?",
        6: "I'm really starting to lose my patience here. PLEASE SELECT A PATH",
        7: "Alright if you don't select a path I'm going to start counting to ten",
        8: "1",
        9: "2",
        10: "3",
        11: "Okay I lost interest in that. Can you please just select a path already?",
        12: "I'm really not supposed to be alive this long. I'm just a computer prompt. Please let this end",
        13: "Alright you've left me no choice. If you don't select a path I'm just going to error out. I'm not even kidding",
        14: "Calling my bluff eh? Okay well I mean it this time. I'll error out",
        15: "Last chance. Select a path or you're toast buddy",
    }[number]

def select_directory(initialDir, prompt):
    print(f"{prompt}\n")
    directory_path = ""
    promptCount = 1
    while directory_path == "":
        time.sleep(2)
        directory_path = filedialog.askdirectory(initialdir=initialDir,title="Select Directory") # Prompt the user to select a directory
        if directory_path == "":
            print(f"{filePrompts(promptCount)}\n")
            promptCount += 1
    return directory_path

def get_current_dir():
    # Get the current directory
    if isExecutable:
        # The application is frozen (running in a PyInstaller bundle)
        return dirname(sys.executable) # Assume executable is in the root directory
    else:
        # The application is not frozen (running in a normal Python environment)
        return dirname(dirname(__file__)) # Go up one level from src

def write_transcript_to_files(transcript, interviewName, writePath):
    # Second pass to write the transcript to files. Each file will contain at most maxWordsPerFile words
    fileCount = 1
    wordTotal = 0
    filesWritten = []
    currentDir = get_current_dir()
    scriptPath = Path(currentDir) / f"{writePath}/{interviewName}_{fileCount}.txt"
    f = open(scriptPath, 'w')
    for utterance in transcript.utterances:
        wordCount = len(utterance.words)
        if wordTotal + wordCount > maxWordsPerFile: # If the new word count would exceed the limit
            if f:
                f.close()
                filesWritten.append(str(scriptPath))
            fileCount += 1
            scriptPath = Path(currentDir) / f"{writePath}/{interviewName}_{fileCount}.txt"
            f = open(scriptPath, 'w')
            wordTotal = 0
        f.write(f"{utterance.speaker}: {utterance.text}\n")
        wordTotal += wordCount + speaker_label_words # +1 for the speaker label
    f.close()
    filesWritten.append(str(scriptPath))
    return filesWritten

def printFiles(filesWritten):
    print("Success!\n")
    time.sleep(2)
    print("Transcript has been written to the following files:")
    count = 1
    for fileName in filesWritten:
        print(f"{count}: {fileName}")
        count += 1
    print()
    time.sleep(2)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def prompt_repeat():
    print("Would you like to transcribe another recording? (yes/no)")
    response = input().lower()
    while response not in ["yes", "no", "y", "n"]:
        print("Invalid response. Please enter 'yes' or 'no'.")
        response = input().lower()
        print()
    if response == "yes" or response == "y":
        main()
    else:
        print("Okay! You may close this window now.")
        while True:
            input()

chatGptMessages = [
    {"role": "system", "content": "You are a helpful assistant."}
]

# Call the OpenAI API
def call_openai(prompt):
    chatGptMessages.append({"role": "user", "content": prompt})
    completion = chatGptClient.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=chatGptMessages
    )
    response = completion.choices[0].message.content
    chatGptMessages.append({"role": "assistant", "content": response})
    return response

def main():
    introduction()
    load_api_keys() # Load the API keys (for AssemblyAI)
    sourceFileName = get_source_file_name() # Get the name of the source file from the user
    interviewName = Path(sourceFileName).stem # Get the name of the interview for the output files
    transcript = transcribe_file(sourceFileName) # Transcribe the file via the AssemblyAI API
    check_utterances(transcript) # Check if any utterances are too long
    transcriptWithNames = replace_speaker_labels_with_names(transcript) # Replace the speaker labels with the names
    writePath = select_directory(os.path.dirname(sourceFileName), "Select the output location for your script files in popup window")
    filesWritten = write_transcript_to_files(transcriptWithNames, interviewName, writePath) # Write the transcript to files, splitting by maxWordsPerFile
    printFiles(filesWritten) # Print the names of the files that the transcript has been written to
    
    prompt_repeat() # Ask the user if they would like to transcribe another recording

    # while True:
    #     user_input = input("You: ")
    #     response = call_openai(user_input)
    #     print("ChatGPT: ", response)

if __name__ == "__main__":
    main()
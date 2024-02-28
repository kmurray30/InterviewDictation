Simply click on the "ClickMe" file in this directory
Paste a recording file from anywhere in your computer (or even online) into the terminal (drag and drop works)
The output script and summaries will be put in "Scripts" "Gemini" and "GPT" folders

If you want to edit the logic
First make sure your virtual environment is set up with:
    python3 -m venv .venv
    source .venv/bin/activate (run this line every time you open a new terminal)
Then make sure all necessary python modules are installed (including pyinstaller)
Make sure to add a .env file in the root directory with the contents:
    ASSEMBLYAI_API_KEY="<key_here>" # Get this from https://www.assemblyai.com/app
Make your changes in the main.py file
If fine running python file directly, cd to src and run:
    python3 main.py
If you want to build an executable, cd to src and run:
    build.sh
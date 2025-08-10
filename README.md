# Airbnb Virtual Assistant

A web-based interface for managing Airbnb message threads with AI assistance.

## Features

- 📧 **Message Thread Management**: View and select from your Airbnb message threads
- 🤖 **AI-Powered Responses**: Get AI-generated responses using the context from your check-in instructions
- 💬 **Interactive Chat Interface**: Real-time chat interface for each message thread
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file with the following variables:
   ```
   EMAIL=your_email@gmail.com
   PASSWORD=your_app_password
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access the Web Interface**:
   Open your browser and go to `http://localhost:5000`

## Usage

1. **Select a Thread**: Click on any message thread from the sidebar to view the conversation
2. **View Messages**: The chat interface will display all messages in the selected thread
3. **Send Prompts**: Type your message in the input field and press Enter or click Send
4. **Get AI Responses**: The AI will respond using the context from your check-in instructions

## Files

- `app.py` - Flask web application
- `email_reader.py` - Email fetching and parsing logic
- `main.py` - Original command-line interface
- `CheckInInstructions.txt` - Context file for AI responses
- `templates/index.html` - Web interface template

## Note

Make sure to use an App Password for Gmail if you have 2FA enabled.

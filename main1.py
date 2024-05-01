import boto3
from datetime import datetime
import json
import pyaudio
import wave
import os
import urllib
import threading
# Replace with your AWS access key and secret access key
ACCESS_KEY = ""
SECRET_KEY = ""

# Replace with your AWS region and S3 bucket name
REGION = 'us-east-1'
BUCKET_NAME = 'aiml-stt-inputs'

# Initialize the PyAudio
audio = pyaudio.PyAudio()

# Define audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Generate a unique filename using timestamp
recorded_file_name = f"recording_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"

# Start recording
print("Recording... Press 'q' to stop recording.")
stream = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

frames = []
recording = True

# Function to listen for 'q' key press
def key_listener():
    global recording
    while True:
        key = input()
        if key == 'q':
            recording = False
            break

# Start the key listener thread
listener_thread = threading.Thread(target=key_listener)
listener_thread.start()

# Record audio until 'q' is pressed
while recording:
    data = stream.read(CHUNK)
    frames.append(data)

# Stop recording
print("Finished recording.")
stream.stop_stream()
stream.close()
audio.terminate()

# Save the recorded audio to a WAV file
WAVE_OUTPUT_FILENAME = recorded_file_name
with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))

# Upload the WAV file to S3
s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
s3_client.upload_file(WAVE_OUTPUT_FILENAME, BUCKET_NAME, WAVE_OUTPUT_FILENAME)

# Generate a unique transcription job name using timestamp
job_name = 'transcription_job_' + datetime.now().strftime('%Y%m%d%H%M%S')

# Create a Transcribe client
transcribe_client = boto3.client('transcribe', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)

# Start the transcription job
transcription_job = transcribe_client.start_transcription_job(
    TranscriptionJobName=job_name,
    Media={'MediaFileUri': f's3://{BUCKET_NAME}/{WAVE_OUTPUT_FILENAME}'},
    MediaFormat='wav',
    LanguageCode='en-US'
)

# Wait for the transcription job to complete
while True:
    job = transcribe_client.get_transcription_job(TranscriptionJobName=transcription_job['TranscriptionJob']['TranscriptionJobName'])
    if job['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
        break

# Check if the job was successful
if job['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
    # Retrieve the transcribed text
    transcript_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
    transcript_text = urllib.request.urlopen(transcript_uri).read().decode('utf-8')
    transcribed_text = json.loads(transcript_text)['results']['transcripts'][0]['transcript']
    # Print the transcribed text
    print("Transcribed Text:")
    print(transcribed_text)
else:
    print("Transcription job failed.")
    
# Remove the local recording file
os.remove(WAVE_OUTPUT_FILENAME)



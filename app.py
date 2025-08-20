import streamlit as st
# Custom CSS + JS Styling
def local_css():
    st.markdown("""
       <style>
/* App dark background with animated gradient */
.stApp {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #e0e0e0;
}

/* Gradient background animation */
@keyframes gradientBG {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

/* Title Styling - neon glow */
h1 {
    color: #00ffcc !important;
    text-align: center;
    font-size: 3em !important;
    font-weight: bold;
    text-shadow: 0 0 20px #00ffcc, 0 0 40px #00ffcc;
    animation: fadeIn 2s ease-in-out;
}

/* Fade In animation */
@keyframes fadeIn {
    from {opacity: 0; transform: translateY(-20px);}
    to {opacity: 1; transform: translateY(0);}
}

/* Sidebar glass + dark effect */
section[data-testid="stSidebar"] {
    background: rgba(20, 20, 20, 0.8);
    backdrop-filter: blur(10px);
    color: #ffffff;
    border-radius: 15px;
    padding: 15px;
    box-shadow: 0px 0px 20px rgba(0,0,0,0.6);
}
section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] label {
    color: #00ffcc !important;
}

/* Progress Bar neon */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #ff512f, #dd2476);
    border-radius: 10px;
    box-shadow: 0px 0px 12px rgba(255, 81, 47, 0.8);
}

/* Neon Buttons */
.stButton>button {
    background: linear-gradient(90deg, #ff6a00, #ee0979);
    color: white;
    border: none;
    border-radius: 15px;
    padding: 0.7em 1.5em;
    font-size: 1.1em;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0px 0px 15px rgba(255,106,0,0.9);
}
.stButton>button:hover {
    transform: scale(1.08);
    background: linear-gradient(90deg, #ee0979, #ff6a00);
    box-shadow: 0px 0px 25px rgba(255,0,120,1);
}

/* Download Button */
.stDownloadButton>button {
    background: linear-gradient(90deg, #00c6ff, #0072ff);
    color: white;
    font-weight: bold;
    border-radius: 12px;
    padding: 0.6em 1.3em;
    transition: 0.3s;
    box-shadow: 0px 0px 15px rgba(0, 198, 255, 0.9);
}
.stDownloadButton>button:hover {
    background: linear-gradient(90deg, #0072ff, #00c6ff);
    transform: scale(1.08);
    box-shadow: 0px 0px 25px rgba(0, 198, 255, 1);
}
</style>


    """, unsafe_allow_html=True)

def local_js():
    st.markdown("""
        <script>
        document.addEventListener("DOMContentLoaded", function() {
            let title = document.querySelector("h1");
            if(title){
                title.style.opacity = 0;
                setTimeout(() => {
                    title.style.transition = "opacity 2s";
                    title.style.opacity = 1;
                }, 500);
            }
        });
        </script>
    """, unsafe_allow_html=True)

# -----------------------------
# Imports
# -----------------------------
import os
import requests
from zipfile import ZipFile
import yt_dlp
from time import sleep
import uuid
import datetime

# -----------------------------
# Utils
# -----------------------------
def get_unique_filename(base, ext):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base}_{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"

# -----------------------------
# UI
# -----------------------------
st.markdown('# 📝 **Transcriber App**')
local_css()
local_js()
bar = st.progress(0)

# -----------------------------
# 1. Download YouTube audio
# -----------------------------
def get_yt(URL):
    try:
        output_template = get_unique_filename("yt_audio", "%(ext)s")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(URL, download=True)
            filename = ydl.prepare_filename(result)

        if os.path.exists(filename):
            bar.progress(10)
            return filename
        st.error("❌ Audio file not found after download.")
        return None

    except Exception as e:
        st.error(f"❌ Error downloading YouTube audio: {e}")
        return None

# -----------------------------
# 2. Upload to AssemblyAI + Transcribe
# -----------------------------
def transcribe_yt(filename):
    bar.progress(20)

    def read_file(filename, chunk_size=5242880):
        with open(filename, 'rb') as _file:
            while True:
                data = _file.read(chunk_size)
                if not data:
                    break
                yield data

    # Upload
    headers = {'authorization': api_key}
    response = requests.post(
        'https://api.assemblyai.com/v2/upload',
        headers=headers,
        data=read_file(filename)
    )
    if response.status_code != 200:
        st.error("❌ Upload to AssemblyAI failed.")
        return None
    audio_url = response.json()['upload_url']
    bar.progress(30)

    # Request transcription
    endpoint = "https://api.assemblyai.com/v2/transcript"
    json = {"audio_url": audio_url}
    headers = {"authorization": api_key, "content-type": "application/json"}
    transcript_input_response = requests.post(endpoint, json=json, headers=headers)
    if transcript_input_response.status_code != 200:
        st.error("❌ Transcription request failed.")
        return None
    bar.progress(40)

    transcript_id = transcript_input_response.json()["id"]
    bar.progress(50)

    # Poll until complete
    endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    headers = {"authorization": api_key}
    while True:
        transcript_output_response = requests.get(endpoint, headers=headers)
        status = transcript_output_response.json()['status']
        if status == 'completed':
            break
        elif status == 'error':
            st.error("❌ Transcription failed.")
            return None
        else:
            st.warning('⏳ Transcription is processing ...')
            sleep(5)
    bar.progress(100)

    # Show transcript
    st.header('Output')
    text = transcript_output_response.json()["text"]
    st.success(text)

    # Save unique files
    txt_file = get_unique_filename("transcript", "txt")
    srt_file = get_unique_filename("transcript", "srt")
    zip_file_name = get_unique_filename("transcription", "zip")

    with open(txt_file, 'w', encoding="utf-8") as f:
        f.write(text)

    srt_endpoint = endpoint + "/srt"
    srt_response = requests.get(srt_endpoint, headers=headers)
    with open(srt_file, "w", encoding="utf-8") as _file:
        _file.write(srt_response.text)

    with ZipFile(zip_file_name, 'w') as zip_file:
        zip_file.write(txt_file)
        zip_file.write(srt_file)

    return zip_file_name

# -----------------------------
# 3. The App
# -----------------------------
api_key = st.secrets['api_key']  # put your API key in .streamlit/secrets.toml
st.warning('👉 Enter a YouTube URL in the sidebar to start.')

# Sidebar
st.sidebar.header('Input parameter')
with st.sidebar.form(key='my_form'):
    URL = st.text_input('Enter URL of YouTube video:')
    submit_button = st.form_submit_button(label='Go')

# Run pipeline
if submit_button:
    audio_file = get_yt(URL)
    if audio_file:
        zip_file_name = transcribe_yt(audio_file)
        if zip_file_name:
            with open(zip_file_name, "rb") as zip_download:
                st.download_button(
                    label="⬇️ Download ZIP",
                    data=zip_download,
                    file_name=zip_file_name,
                    mime="application/zip"
                )

from youtube_transcript_api import YouTubeTranscriptApi
import json

# Extraer el ID del video de YouTube de la URL
video_id = "ky6wFiF5vMk"  # ID extraído de https://www.youtube.com/watch?v=ky6wFiF5vMk

# Obtener la transcripción
transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

# Combinar los segmentos de transcripción en un solo texto
transcript_text = " ".join([segment['text'] for segment in transcript_list])
print(transcript_text)

# Guardar el transcript en formato JSON
transcript_data = {"transcript": transcript_text}
print(transcript_data)
with open("transcript.json", "w") as f:
    json.dump(transcript_data, f, indent=4)
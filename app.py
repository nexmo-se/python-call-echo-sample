#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_sock import Sock
from werkzeug.routing import Map, Rule
import time, struct, math
app = Flask(__name__)
sock = Sock(app)
PORT = 3003

SHORT_NORMALIZE = (1.0/32768.0)
swidth = 2
Threshold = 10
TIMEOUT_LENGTH = 0.5 #The silent length we allow before cutting recognition

def rms(frame): #Root mean Square: a function to check if the audio is silent. Commonly used in Audio stuff
    count = len(frame) / swidth
    format = "%dh" % (count) 
    #print(format)
    #print(frame)
    shorts = struct.unpack(format, frame) #unpack a frame into individual Decimal Value
    print(shorts)
    sum_squares = 0.0
    for sample in shorts:
        n = sample * SHORT_NORMALIZE #get the level of a sample and normalize it a bit (increase levels)
        sum_squares += n * n #get square of level
    rms = math.pow(sum_squares / count, 0.5) #summ all levels and get mean
    return rms * 1000 #raise value a bit so it's easy to read 

@app.route("/webhooks/answer")
def answer_call():
    print("Ringing",request.host)
    ncco = [
        {
            "action": "talk",
            "text": "This is a Voice Echo test. Speak after the Ding.",
        },
        {
            "action": "connect",
            "from": "Vonage",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": f'wss://{request.host}/socket'.format(request.host),
                    "content-type": "audio/l16;rate=16000",
                }
            ],
        },
    ]

    return jsonify(ncco)


@app.route("/webhooks/call-event", methods=["POST"])
def events():
    request_body = request.data.decode("utf-8")  # Assuming it's a text-based request body
    print("Request Body:", request_body)
    return "200"


@sock.route("/socket")
def echo_socket(ws):
  rec = []
  current = 1
  end = 0

  #This part sends a wav file called ding.wav
  #we open the wav file
  with open("./ding.wav", "rb") as file:
    buffer = file.read()
  
  #we then chunk it out
  for i in range(0, len(buffer), 640):
    chunk = (buffer[i:i+640])
    ws.send(bytes(chunk))
  

  #!!!This part will echo whatever the user says if it detects a pause!!!
  while True:
    audio = ws.receive()
    if isinstance(audio, str):
        continue #if this is a string, we don't handle it
    rms_val = rms(audio)

    #If audio is loud enough, set the current timeout to now and end timeout to now + TIMEOUT_LENGTH
    #This will start the next part that stores the audio until it's quiet again
    if rms_val > Threshold and not current <= end :
      print("Heard Something")
      current = time.time()
      end = time.time() + TIMEOUT_LENGTH

    #If levels are higher than threshold add audio to record array and move the end timeout to now + TIMEOUT_LENGTH
    #When the levels go lower than threshold, continue recording until timeout. 
    #By doing this, we only capture relevant audio and not continously call our STT/NLP with nonsensical sounds
    #By adding a trailing TIMEOUT_LENGTH we can capture natural pauses and make things not sound robotic
    if current <= end: 
      if rms_val >= Threshold: end = time.time() + TIMEOUT_LENGTH
      current = time.time()
      rec.append(audio)

    #process audio if we have an array of non-silent audio
    else:
      if len(rec)>0: 
        print("Echoing Audio")

        output_audio = b''.join(rec) #get whatever we heard
        #chunk it and send it out
        for i in range(0, len(output_audio), 640):
            chunk = (output_audio[i:i+640])
            ws.send(bytes(chunk))
        
        rec = [] #reset audio array to blank



if __name__ == "__main__":
    from gevent import pywsgi
    from gevent import monkey
    monkey.patch_all()
    server = pywsgi.WSGIServer(("0.0.0.0", PORT), app)
    server.serve_forever()
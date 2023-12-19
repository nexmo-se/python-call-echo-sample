# Python Call Echo and File audio playback via Websocket sample

A sample app that shows how to send a wav file via websocket and how to echo a user's voice.

##Running

1. pip install -r requirements.txt
2. python app.py

##Other requirements
1. Set your Vonage callbacks to the following
- Answer callback URL: GET {APP_URL}/webhooks/answer
- Event URL: GET {APP_URL}/webhooks/call-event

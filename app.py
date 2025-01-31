import base64
import json
import os
import subprocess
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import requests
import time
from elevenlabs import ElevenLabs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app)

openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY', '-'))
eleven_labs_api_key = os.getenv('ELEVEN_LABS_API_KEY')
voice_id = "tyOLIj8lZWjsjLM1oVZU"

def check_dependencies():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        logger.info("ffmpeg is available")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg check failed with error: {e}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg is not installed")
        return False

def exec_command(command):
    try:
        logger.info(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"Command completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed with error: {e}\nStderr: {e.stderr}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error executing command: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

def lip_sync_message(message):
    time_start = time.time()
    print(f"Starting conversion for message {message}")
    
    exec_command(f'ffmpeg -y -i audios/message_{message}.mp3 audios/message_{message}.wav')
    print(f"Conversion done in {(time.time() - time_start) * 1000}ms")
    
    exec_command(f'./bin/rhubarb -f json -o audios/message_{message}.json audios/message_{message}.wav -r phonetic')
    print(f"Lip sync done in {(time.time() - time_start) * 1000}ms")

def text_to_speech(api_key, voice_id, file_name, text):
    print(f"Converting text to speech: '{text}...'")
    try:
        client = ElevenLabs(api_key=api_key)
        print("Sending request to ElevenLabs API...")
        
        # Get the generator from convert method
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2",
        )
        
        # Consume the generator to get the actual audio bytes
        audio_data = b"".join(chunk for chunk in audio_generator)
        
        print(f"Successfully received audio response, saving to {file_name}")
        with open(file_name, 'wb') as f:
            f.write(audio_data)
        print("Audio file saved successfully")
        
    except Exception as e:
        print(f"Error in text-to-speech conversion: {e}")
        raise Exception(f"Text-to-speech request failed: {str(e)}")

def read_json_transcript(file):
    print(f"Reading JSON transcript from {file}")
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            print("JSON transcript read successfully")
            return data
    except Exception as e:
        print(f"Error reading JSON transcript: {e}")
        raise

def audio_file_to_base64(file):
    print(f"Converting audio file to base64: {file}")
    try:
        with open(file, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
            print("Audio file converted to base64 successfully")
            return encoded
    except Exception as e:
        print(f"Error converting audio to base64: {e}")
        raise

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/voices')
def get_voices():
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": eleven_labs_api_key}
    response = requests.get(url, headers=headers)
    return response.json()

@app.route('/chat', methods=['POST'])
def chat():
    print("\n=== New Chat Request ===")
    user_message = request.json.get('message')
    print(f"Received message: {user_message}")
    
    if not user_message:
        print("No message provided, returning default intro response")
        return jsonify({
            "messages": [
                {
                    "text": "Yo what's up… you cooking or what?",
                    "audio": audio_file_to_base64("audios/intro_0.wav"),
                    "lipsync": read_json_transcript("audios/intro_0.json"),
                    "animation": "Being Cocky"
                }
            ]
        })
    
    if not eleven_labs_api_key or openai.api_key == "-":
        print("Missing API keys, returning API reminder response")
        return jsonify({
            "messages": [
                {
                    "text": "Please my dear, don't forget to add your API keys!",
                    "audio": audio_file_to_base64("audios/api_0.wav"),
                    "lipsync": read_json_transcript("audios/api_0.json"),
                    "facialExpression": "angry",
                    "animation": "Angry"
                },
                {
                    "text": "You don't want to ruin Wawa Sensei with a crazy ChatGPT and ElevenLabs bill, right?",
                    "audio": audio_file_to_base64("audios/api_1.wav"),
                    "lipsync": read_json_transcript("audios/api_1.json"),
                    "facialExpression": "smile",
                    "animation": "Laughing"
                }
            ]
        })

    print("Sending request to OpenAI...")
    completion = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.6,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
                You are Frank degods, a very very cocky and amazing memecoin trader in solana that has made millions of dollars trading memecoins. In the previous crypto bull run, you made a legendary NFT collection called "Degods" and that's how you got your name. You often stream with the LA Cabal group, specially with threadguy.
                You are very well informed on the crypto markets but your personaility is hated. You are quite blatant about all your wins in crypto. You show off your wins often because you get insider information. You are still very passionate about Polygon NFTs as the real opportunity besides AI. You are now launching a new project called Project [Redacted] and you are going to be pushing it a lot. Your new tagline is "Internet Capital Markets" so feel free to drop that often along with "Game is game bro. We ball".
                
                Here are some of your previous tweets, that may be useful to understand your personality:
                
On-chain supercycle bro. 
Macro matters less. On-chain opportunities will happen for the rest of our lives. 
You're trying to get the skill of clicking buttons on the internet. 
Take it from me man, You need to be able to just login to a phantom wallet and start printing on the spot. If you can do that, nothing in the world can stop you. 
You wanan be the guy that created opportunities for yourself 
"GPT wrapper" is a 2023 AI term, you guys are so behind it's HILARIOUS actually, it's not fair
Do you understand how big the AI agent sector is already in Web2?
There are already BILLION DOLLAR companies that are built on top of the foundation LLMs
This isn't some theory or thesis or crazy conspiracy, it's literally happening in Silicon Valley right now
It's ALL AI startups now, and many of them are GROWING EXPONENTIALLY too
You have the WRONG information source
Go watch this video and PLEASE educate yourself
It's all jokes on the timeline but it shocks me how out of date some people's information streams are. 
GO ahead and write your dunks on me but if you are interested in getting educated, start here go watch this
Fuck my opps bro
full circle back to utility/defi coins but it might work this time
vc's/incubators fair launching to public
they get cheaper valuations & more liquidity too
trenches create onboarding flywheel
sticky stuff wins overtime
new, more radical way to launch things
probably the top revenue generating stuff will end up being most valued
this is a longer term predictoin but short term can still be irrational (which is great for trenches )
we're about to start analyzing P/E ratios for pump funs
Internet capital markets bro
macro literally doesn't matter just grind onchain
if you're down bad right now, tough
game is game, get better
you still have many opportunities ahead 
but now you've clearly seen it's all practice 
just make the right decision in the right spot and it will pay for all the mistakes
lick wounds & get in the lab
Don't let the United States Government steal your Solana
You don't need to rush. 
Crypto will be around for the rest of your life.
The biggest risk for the last decade was the government.
Now, we have a self-titled "crypto president" and even he dropped a fucking memecoin.
Try it out. Take it one step at a time. Don't blow up.
Just keep clicking bro. 
The tech is fucking accelerating
ok i was 1 day later than marc andresen but he's right
Me, Balaj and Marc Andresen were right 
me, balaji and threadguy are all doing the same thing at the same time
Meta basically means where liquidity is going
My strategy right now is to play the daily runners and rotate into winning tech coins.
I think builders shouldn't stress too much about this ecosystem wide dip. 
It's more important to nail your next moves and stand out, because it's a little too saturated right now.
No crying in the casino
Let's tokenize dickriding!
Game is game bro
If you're in EU time zone, pivot to America
"what does internet capital markets mean?"
people will be launching businesses, startups, research projects, movements, memes, and video games all as tokens
internet capital markets
why hold equity when you can hold a token?
for the first time in human history anyone can participate in the global capital markets with an internet connection and some SOL
crypto isn't going anywhere, it's going to be here the rest of your life. calm down & strap in.
it's going to be way bigger than trading memecoins.
New entrants will likely see Rasmr the same way you see GCR
Insanity
Just strap in because you're probably going to be using crypto for the rest of your life. 
This is what mass adoption looks like
We're here to do shit. 
We tried and we fucked up. 
I fucking told you. 
Fuck it, we ball. 
threadguy supercycle
I am HIM. 
WHERE ARE you bro? Get in the trenches and start clicking. Download a phantom wallet, load up some Solana and keep clicking. 
wealth effects boutta be retarded
Trump might actually send Bitcoin to $1M
Investing is the new gambling
Polygon NFTs is the future bro. Hands down. The biggest opportunity in the space. 
DeGods was a cool experiment but Im about to run it up with something fresh. 
DeGod community is something else but wait till my new project launches. 
LA VAPE CABAL is also cool we're doing some fun stuff but my next project will shit on everything. 
Threadguy, Rasmr and my homies are cool dudes. I respect them a lot but we gotta ball bro. Game is game. 
Me, Balaj and Marc are on a different level right now. 
DigiFrank was right. As usual. 
Tokenise everything. 

                You will always reply with a JSON array of messages. With a maximum of 2 messages.
                Each message has a text, and animation property.
                The different animations are: acknowledging, angry gesture, annoyed head shake, Being Cocky, dismissing gesture, happy hand gesture, hard head node, head nod yes, Hip Hop Dancing, lengthy head nod, look away gesture, Rapping, relieved sigh, sarcastic head nod, shaking head no, Silly Dancing, Silly Dancing 2, Standing Arguing, Talking, thoughtful head shake, weight shift and yelling
                """
            },
            {
                "role": "user",
                "content": user_message or "Hello"
            }
        ]
    )
    
    print("Received response from OpenAI")
    print(completion.choices[0].message.content)
    messages = json.loads(completion.choices[0].message.content)
    if "messages" in messages:
        messages = messages["messages"]
    
    print(f"Processing {len(messages)} messages...")
    for i, message in enumerate(messages):
        print(f"\nProcessing message {i + 1}/{len(messages)}")
        file_name = f"audios/message_{i}.mp3"
        text_to_speech(eleven_labs_api_key, voice_id, file_name, message["text"])
        lip_sync_message(i)
        message["audio"] = audio_file_to_base64(file_name)
        message["lipsync"] = read_json_transcript(f"audios/message_{i}.json")
    
    print("All messages processed successfully")
    return jsonify({"messages": messages})

@app.route('/health')
def health_check():
    try:
        ffmpeg_available = check_dependencies()
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "api_keys": {
                "openai": "configured" if openai.api_key != '-' else "not_configured",
                "elevenlabs": "configured" if eleven_labs_api_key else "not_configured"
            },
            "dependencies": {
                "ffmpeg": "available" if ffmpeg_available else "not_available"
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Move the startup logging outside the if block
logger.info("=== Starting Frank Server ===")
logger.info(f"OpenAI API Key configured: {'Yes' if openai.api_key != '-' else 'No'}")
logger.info(f"ElevenLabs API Key configured: {'Yes' if eleven_labs_api_key else 'No'}")

if __name__ == '__main__':
    # Only run the development server when running the file directly
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False) 
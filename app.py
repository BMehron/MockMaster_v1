import streamlit as st
from timeit import default_timer as timer
from model import *
from audiorecorder import audiorecorder
from streamlit_extras.stylable_container import stylable_container
from model import get_answer
from keys import opai_key
import json
from openai import OpenAI

# Load the JSON data from the file
with open("data/problems.json", 'r') as file:
    data = json.load(file)

# initialize the problem id
if "problem_id" not in st.session_state.keys():
    st.session_state.problem_id = 0

# App title
st.set_page_config(page_title="Coding Interview")

# Define timer
if "start" not in st.session_state.keys():
    st.session_state.start = None
    
# Hugging Face Credentials
with st.sidebar:
    
    st.title('Coding Interview')
    # if ('EMAIL' in st.secrets) and ('PASS' in st.secrets):
    #     st.success('HuggingFace Login credentials already provided!', icon='✅')
    #     hf_email = st.secrets['EMAIL']
    #     hf_pass = st.secrets['PASS']
    # else:
    #     hf_email = st.text_input('Enter E-mail:', type='password')
    #     hf_pass = st.text_input('Enter password:', type='password')
    #     if not (hf_email and hf_pass):
    #         st.warning('Please enter your credentials!', icon='⚠️')
    #     else:
    #         st.success('Proceed to entering your prompt message!', icon='👉')
    # st.success('Proceed to entering your prompt message!', icon='👉')
    # st.markdown('📖 Learn how to build this app in this [blog](https://blog.streamlit.io/how-to-build-an-llm-powered-chatbot-with-streamlit/)!')
    

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    prompt="You are Mike a senior software engineer at Google. You will have to conduct a coding interview for a candidate who is applying for a summer internship at SWE. Write an introductory word in 3-4 sentences for a programming interview ask the candidate to for introduction."
    st.session_state.messages = [{"role": "assistant", "content": get_answer(prompt_text=prompt)}]
    st.session_state.start = timer()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

#st.title("Audio Recorder")
with stylable_container(
        key="bottom_content",
        css_styles="""
            {
                position: fixed;
                bottom: 120px;
                right: 50px;
            }
            """,
    ):
        audio = audiorecorder("🎙️ start", "🎙️ stop")
        
if prompt := st.chat_input(disabled=False):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
elif len(audio) > 0:
    # To play audio in frontend:
    #st.audio(audio.export().read())  
    audio.export("audio.mp3", format="mp3")
    # extract text from audio.
    client = OpenAI(api_key=opai_key)
    audio_file = open("audio.mp3", "rb")
    prompt = client.audio.transcriptions.create(
      model="whisper-1", 
      file=audio_file
    ).text
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Interview limit in minutes
stop_time = 5 # 60

# set finish flag
if "finish" not in st.session_state.keys():
    st.session_state.finish = False

# Create questions
create_question = True

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            problem = f"""Description: {data[st.session_state.problem_id]['description']}
Examples: {data[st.session_state.problem_id]['examples']}
Constraints: {data[st.session_state.problem_id]['constraints']}"""
            solution_approache = data[st.session_state.problem_id]['approaches']

            # ask the first question
            if len(st.session_state.messages) == 2:
                if create_question:
                    prompt_ = f"""Here is the introduction of the candidate. 
{st.session_state.messages[-1]['content']}
Now start the coding interview with the first question and ask for thoughts how they are going to implement it:
"""
                else:
                    prompt_ = f"""Here is the introduction of the candidate. 
{st.session_state.messages[-1]['content']}
Now start the coding interview with the first question as follows and ask for thoughts how they are going to implement it.
Problem:
{problem}
"""
                response = get_answer(prompt_text=prompt_)
            
            # execute the code if the user passes a function
            elif contains_python(text=st.session_state.messages[-1]['content']) == "YES":
                output = execute_code(input=st.session_state.messages[-1]['content'])
                if create_question:
                    prompt_ = f"""Here is the response of the candidate {st.session_state.messages[-1]['content']}. Here is an example of usage with executed output {output}
If the answer is True ask more difficult question.
If the answer is Wrong, ask to rethink about the solution. Don't explicitly give the right answer.
If candidate keeps giving wrong answer, ask an easier question.
"""
                else:
                    prompt_ = f"""Here is the response of the candidate {st.session_state.messages[-1]['content']}. Here is an example of usage with executed output {output}
If the answer is Wrong, ask to rethink about the solution. Don't explicitly give the right answer.
If the answer is True ask the following new question:
Problem:
{problem}
"""
                response = get_answer(prompt_text=prompt_)
                # stop if 1 hour has passed and the last question has been finalized
                if is_correct(text=response) == "YES":
                    st.session_state.problem_id += 1
                    if (timer() - st.session_state.start) / 60 > stop_time:
                        prompt_ = f"""Here is the response of the candidate {st.session_state.messages[-1]['content']}. Here is an example of usage with executed output {output}
Now finish the interview, and give a summary of the whole interview.
Give a feedback on the responses that the candidate have given to individual questions.
Tell how they could be improved.
Finally give an overall assessment rate out of 10, and give all kinds of feedbacks that you can possibly give. 
"""
                    response = get_answer(prompt_text=prompt_)
                    st.session_state.finish = True

            else:
                if create_question:
                    prompt_ = f"""Here are the insights of the user. 
{st.session_state.messages[-1]['content']}
If the implementation thoughts are correct, ask to implement in on python.
If the implementation thoughts are wrong, give some hints and ask to rethink about it.
"""
                else:
                    prompt_ = f"""Here are the approaches that the candidate has given. 
{st.session_state.messages[-1]['content']}

Here are the actual approaches of the true solution:
{solution_approache}

Compare the candidate approach to the original true approach.
If the candidate approch seems correct, ask to implement in on python.
If the candidate aproach is wrong, give some hints and ask to rethink about it.
"""
                response = get_answer(prompt_text=prompt_)
            st.write(response) 
    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)
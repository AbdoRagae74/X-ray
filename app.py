import streamlit as st
import groq
import base64

st.title("X-Ray Analyzer")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "image_data" not in st.session_state:
    st.session_state.image_data = None

# Sidebar
with st.sidebar:
    api_key = st.secrets["GROQ_API_KEY"]
    uploaded_file = st.file_uploader("Upload X-Ray", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded X-Ray", use_container_width=True)
        img_bytes = uploaded_file.read()
        if img_bytes:
            st.session_state.image_data = base64.b64encode(img_bytes).decode("utf-8")

    if st.session_state.messages:
        history_text = "\n\n".join(
            f"{'You' if m['role'] == 'user' else 'Assistant'}:\n{m['content']}"
            for m in st.session_state.messages
        )
        st.download_button("Download Chat", history_text, file_name="xray_report.txt", mime="text/plain")

    if st.button("New Session"):
        st.session_state.messages = []
        st.session_state.image_data = None
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

def call_groq(messages, max_tokens=1024):
    client = groq.Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=messages,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

# Auto-analyze on image upload — same exact call as app22.py
if st.session_state.image_data and not st.session_state.messages:
    with st.chat_message("user"):
        st.write("Please analyze this X-ray.")
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            reply = call_groq([{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{st.session_state.image_data}"}
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are a medical imaging assistant. Analyze this X-ray and provide:\n"
                            "1. Body part shown\n"
                            "2. Any visible abnormalities or findings\n"
                            "3. Overall impression\n\n"
                            "Be concise and clear.\n\n"
                            "Structure your response with: Exam Type, Technique, Findings, Impression, Recommendation.\n"
                            "End with:\nabuelfeda Radiologist - X-Ray Reader\n\n"
                            "Then ask if the user wants any area re-analyzed."
                        )
                    }
                ]
            }])
        st.write(reply)

    st.session_state.messages.append({"role": "user", "content": "Please analyze this X-ray."})
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Chat input
user_input = st.chat_input("Ask anything or request re-analysis...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build history + new message, re-attach image for re-analysis
            api_messages = []
            for m in st.session_state.messages:
                api_messages.append({"role": m["role"], "content": m["content"]})

            if st.session_state.image_data:
                api_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{st.session_state.image_data}"}
                        },
                        {"type": "text", "text": user_input}
                    ]
                })
            else:
                api_messages.append({"role": "user", "content": user_input})

            reply = call_groq(api_messages, max_tokens=2048)
        st.write(reply)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": reply})

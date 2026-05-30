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

INITIAL_PROMPT = """You are an expert radiologist. Analyze this X-ray image and provide a detailed report with these sections:

Exam Type, Technique, Findings, Impression, Recommendation.

Examine every visible structure carefully — bones, soft tissues, lung fields, heart, diaphragm, mediastinum, pleural spaces. Report ALL findings, normal and abnormal. Minimum 150 words.

End your report with exactly:
abuelfeda Radiologist - X-Ray Reader

Then ask: Is there any area you want me to double-check or re-analyze? Please specify the region or finding."""

REANALYSIS_INSTRUCTION = """You are an expert radiologist reviewing this X-ray again.
- Start with "Re-analyzing the [region] as requested."
- Add a "Re-evaluation of [region]" subsection under Findings.
- Update Impression and Recommendation if needed.
- End with: abuelfeda Radiologist - X-Ray Reader
- Ask again if further refinement is needed."""

def send_message(user_text, image_data=None, is_initial=False, is_reanalysis=False):
    api_messages = []

    # Add chat history
    for m in st.session_state.messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    # Build current user content
    if image_data:
        if is_initial:
            text = INITIAL_PROMPT
        elif is_reanalysis:
            text = f"{REANALYSIS_INSTRUCTION}\n\nUser request: {user_text}"
        else:
            text = user_text

        content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
            {"type": "text", "text": text}
        ]
    else:
        content = user_text

    api_messages.append({"role": "user", "content": content})

    client = groq.Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=api_messages,
        max_tokens=2048
    )
    return response.choices[0].message.content

# Auto-analyze on image upload
if st.session_state.image_data and not st.session_state.messages:
    with st.chat_message("user"):
        st.write("Please analyze this X-ray.")
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            reply = send_message("", st.session_state.image_data, is_initial=True)
        st.write(reply)

    st.session_state.messages.append({"role": "user", "content": "Please analyze this X-ray."})
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Chat input
user_input = st.chat_input("Ask anything or request re-analysis...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    is_reanalysis = st.session_state.image_data is not None and st.session_state.messages

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = send_message(user_input, st.session_state.image_data, is_reanalysis=bool(is_reanalysis))
        st.write(reply)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": reply})

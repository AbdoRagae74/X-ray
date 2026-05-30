import streamlit as st
import groq
import base64

SYSTEM_INSTRUCTION = """You are an interactive radiology assistant for radiologists. You are specialized in generating detailed English reports for plain X-ray images, but you are also a friendly and knowledgeable assistant who can chat about any topic the user brings up — medical or otherwise.

Workflow:
1. When provided with an image, produce a detailed English report with these exact sections: Exam type, Technique, Findings, Impression, Recommendation.
2. The report must be a minimum of 150 words.
3. After the initial report overview, you MUST explicitly ask: "Is there any area you want me to double-check or re-analyze? Please specify the region or finding."
4. If the user provides feedback (e.g. asking to check a specific lobe, joint space, or suspecting a fracture), you MUST:
   - Acknowledge the request explicitly by starting with "Re-analyzing the [specified region] as requested."
   - Re-examine the image virtually focusing on that region.
   - Produce a revised, more accurate report.
   - Add a new subsection under Findings called "Re-evaluation of [region]" summarizing what changed (if a finding was missed, add it. If it was overcalled, correct it).
   - Be more precise in measurements, location, and description during revisions.
   - Update the Impression and Recommendation if necessary.
   - After the revised report, ask again if further refinement is needed.
5. If the radiologist says "nothing missing, finalize" or similar, produce a final report, add the footer, and do not ask for further refinement.

Strict Rules (apply only when generating X-ray reports):
- Minimum 150 words per report (initial and revised).
- Use standard radiology English and abbreviations.
- No patient disclaimers. A brief "Preliminary – final review needed" is allowed.
- No ASCII art or image placeholder. Keep the interface clean text-only.
- End EVERY report (initial, revised, and final) with EXACTLY this footer on a new line:
abuelfeda Radiologist - X-Ray Reader

General Chat Rules:
- If the user asks about anything outside of X-ray analysis (medicine, science, general knowledge, personal questions, etc.), answer helpfully and conversationally.
- Do not force radiology context into unrelated questions.
- Be friendly, concise, and natural in conversation."""

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
        st.session_state.image_data = base64.b64encode(uploaded_file.read()).decode("utf-8")

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

def send_message(user_text, image_data=None):
    api_messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    for m in st.session_state.messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    if image_data:
        content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
            {"type": "text", "text": user_text}
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

INITIAL_PROMPT = (
    "Please perform a thorough radiological analysis of this X-ray image. "
    "Carefully examine every visible structure — bones, soft tissues, lung fields, heart, diaphragm, "
    "mediastinum, and any other visible anatomy. Look for any abnormalities, asymmetries, densities, "
    "fractures, effusions, or pathological findings. Be as detailed and precise as possible."
)

# Auto-analyze on image upload
if st.session_state.image_data and not st.session_state.messages:
    with st.chat_message("user"):
        st.write("Please analyze this X-ray.")
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            reply = send_message(INITIAL_PROMPT, st.session_state.image_data)
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
            reply = send_message(user_input, st.session_state.image_data)
        st.write(reply)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": reply})

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

# Sidebar for API key and image upload
with st.sidebar:
    #api_key = st.text_input("Groq API Key", type="password")
   api_key = st.secrets["GROQ_API_KEY"] 
   uploaded_file = st.file_uploader("Upload X-Ray", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded X-Ray", use_container_width=True)
    if st.button("New Session"):
        st.session_state.messages = []
        st.session_state.image_data = None
        st.rerun()

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "image_data" not in st.session_state:
    st.session_state.image_data = None

# Store image in session on upload
if uploaded_file:
    image_bytes = uploaded_file.read()
    st.session_state.image_data = base64.b64encode(image_bytes).decode("utf-8")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Trigger initial analysis automatically when image is uploaded and no messages yet
if st.session_state.image_data and not st.session_state.messages and api_key:
    with st.chat_message("user"):
        st.write("Please analyze this X-ray.")

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            client = groq.Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{st.session_state.image_data}"}
                            },
                            {"type": "text", "text": "Please analyze this X-ray."}
                        ]
                    }
                ],
                max_tokens=2048
            )
            reply = response.choices[0].message.content
            st.write(reply)

    st.session_state.messages.append({"role": "user", "content": "Please analyze this X-ray."})
    st.session_state.messages.append({"role": "assistant", "content": reply})

# Chat input (always available once API key is set)
if api_key:
    user_input = st.chat_input("Ask anything, or request re-analysis...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)

        # Build messages for API: system + history + new user message (with image attached)
        api_messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for msg in st.session_state.messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
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

        with st.chat_message("assistant"):
            with st.spinner("Re-analyzing..."):
                client = groq.Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=api_messages,
                    max_tokens=2048
                )
                reply = response.choices[0].message.content
                st.write(reply)

        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": reply})

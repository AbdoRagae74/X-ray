import streamlit as st
import groq
import base64

st.title("X-Ray Analyzer")

api_key = st.text_input("Groq API Key", type="password")
uploaded_file = st.file_uploader("Upload X-Ray", type=["jpg", "jpeg", "png"])

if uploaded_file and api_key:
    st.image(uploaded_file, caption="Uploaded X-Ray", use_container_width=True)

    if st.button("Analyze"):
        with st.spinner("Analyzing..."):
            image_data = base64.b64encode(uploaded_file.read()).decode("utf-8")

            client = groq.Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                        },
                        {
                            "type": "text",
                            "text": (
                                "You are a medical imaging assistant. Analyze this X-ray and provide:\n"
                                "1. Body part shown\n"
                                "2. Any visible abnormalities or findings\n"
                                "3. Overall impression\n\n"
                                "Be concise and clear."
                            )
                        }
                    ]
                }],
                max_tokens=1024
            )

        st.subheader("Result")
        st.write(response.choices[0].message.content)
        st.warning("This is AI-generated and NOT a clinical diagnosis. Consult a doctor.")

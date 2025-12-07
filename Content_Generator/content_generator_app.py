# content_generator_app.py
import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


st.set_page_config(page_title="Content Generator Bot", layout="wide")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o-mini"

TEMPLATES = {
    "Email": "Write a {tone} email (~{length} words) promoting {product} for {audience}. Add subject + CTA.",
    "Social Post": "Write a {tone} social media caption (~{length} words) for {product}. 1 hashtag only.",
    "Blog Outline": "Write a full blog outline for {product} targeting {audience}. H1 + H2 + bullets."
}

def generate(t, product, audience, tone, length):
    prompt = TEMPLATES[t].format(product=product, audience=audience, tone=tone, length=length)
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a marketing and copywriting expert."},
            {"role": "user", "content": prompt}
        ]
    )
    return r.choices[0].message.content

# UI
st.title("✍️ Content Generator Bot — Streamlit")

kind = st.selectbox("Content type", list(TEMPLATES.keys()))
product = st.text_input("Product / Service", "Acme CRM")
audience = st.text_input("Target Audience", "Sales Teams")
tone = st.selectbox("Tone", ["Professional","Friendly","Funny","Urgent","Inspirational"])
length = st.slider("Length (words)", 60, 600, 150)

if st.button("Generate Content"):
    if not OPENAI_API_KEY:
        st.error("Set OPENAI_API_KEY first.")
    else:
        with st.spinner("Generating..."):
            output = generate(kind, product, audience, tone, length)
            st.subheader("📄 Generated Content")
            st.write(output)

            st.download_button(
                "⬇ Download as TXT",
                output,
                file_name=f"{kind.replace(' ','_')}.txt"
            )
